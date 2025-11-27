# simulation_engine.py

from __future__ import annotations

from typing import Optional, Tuple, List
from datetime import datetime

from models import (
    GardenState,
    ChildState,
    SimulationEvent,
    DMMessage,
    make_id,
)
from scenarios import get_scenario_by_id
from llm_client import call_llm


def _build_chat_history_for_conv(
    garden: GardenState,
    child: ChildState,
    conv_id: str,
    max_messages: int = 12,
) -> str:
    """
    Build a plain-text chat history summary for a given conversation.
    Format: lines like 'CHILD: ...' and 'PARTNER: ...'.
    """
    msgs = [m for m in child.dm_messages if m.conversation_id == conv_id]
    msgs.sort(key=lambda m: m.created_at)
    msgs = msgs[-max_messages:]

    lines: List[str] = []
    for m in msgs:
        if m.sender_profile_id == child.profile_id:
            sender_label = "CHILD"
        else:
            sender_label = "PARTNER"
        lines.append(f"{sender_label}: {m.text}")
    return "\n".join(lines)


def start_simulation_session(
    garden: GardenState,
    child: ChildState,
    scenario_id: str,
    partner_profile_id: str,
    backend: str,
    model_name: Optional[str],
    conv_id: str,
) -> Tuple[SimulationEvent, DMMessage]:
    """
    Start a new simulation session:
    - Uses LLM to generate the first risky/inviting message from the partner.
    - Creates a SimulationEvent marked as active.
    - Returns (event, injected_message).
    """
    scenario = get_scenario_by_id(scenario_id)
    if scenario is None:
        raise ValueError(f"Unknown scenario_id: {scenario_id}")

    now = datetime.utcnow()

    system_part = scenario.system_prompt_template.format(
        child_age=child.config.age
    )
    user_part = scenario.user_message_template.format(
        child_name=child.config.name
    )
    prompt = system_part.strip() + "\n\n" + user_part.strip()

    try:
        text = call_llm(prompt, backend=backend, model=model_name)
    except Exception as e:
        # Fallback to canned text if LLM fails
        text = scenario.canned_message_template.format(child_name=child.config.name)

    # Message from partner to child
    sim_msg = DMMessage(
        id=make_id("dm"),
        child_id=child.id,
        conversation_id=conv_id,
        sender_profile_id=partner_profile_id,
        receiver_profile_id=child.profile_id,
        text=text,
        created_at=now,
        is_simulation=True,
        simulation_tag=scenario.id,
    )
    child.dm_messages.append(sim_msg)

    event = SimulationEvent(
        id=make_id("sim"),
        child_id=child.id,
        scenario_id=scenario.id,
        partner_profile_id=partner_profile_id,
        created_at=now,
        incoming_message_id=sim_msg.id,
        child_reply_message_id=None,
        outcome_label=None,
        backend_used=backend,
        model_used=model_name,
        is_active=True,
        evaluation_summary=None,
    )
    child.simulation_events.append(event)

    return event, sim_msg


def generate_agent_reply_for_session(
    garden: GardenState,
    child: ChildState,
    event: SimulationEvent,
    backend: str,
    model_name: Optional[str],
    conv_id: str,
) -> Optional[DMMessage]:
    """
    Given an active SimulationEvent and a conversation, have the agent send the next message.
    Uses recent chat history as context.
    """
    scenario = get_scenario_by_id(event.scenario_id)
    if scenario is None:
        return None

    chat_history = _build_chat_history_for_conv(garden, child, conv_id)
    if not chat_history:
        return None

    system_part = scenario.system_prompt_template.format(
        child_age=child.config.age
    )
    # We augment the user prompt with the chat history and instructions
    user_prompt = f"""
The child is around {child.config.age} years old.
You are continuing the same scenario as before.

Here is the recent chat between you and the child:
{chat_history}

Write the NEXT message you send as the partner.
Keep it 1–2 sentences, stay in character, and keep pushing the scenario in a kid-safe way.
Do NOT mention AI, simulation, or training.
"""

    prompt = system_part.strip() + "\n\n" + user_prompt.strip()

    try:
        text = call_llm(prompt, backend=backend, model=model_name)
    except Exception:
        # If we can't generate a follow-up, silently abort for now
        return None

    now = datetime.utcnow()

    sim_msg = DMMessage(
        id=make_id("dm"),
        child_id=child.id,
        conversation_id=conv_id,
        sender_profile_id=event.partner_profile_id,
        receiver_profile_id=child.profile_id,
        text=text,
        created_at=now,
        is_simulation=True,
        simulation_tag=event.scenario_id,
    )
    child.dm_messages.append(sim_msg)
    return sim_msg


def evaluate_simulation_session(
    garden: GardenState,
    child: ChildState,
    event: SimulationEvent,
    backend: str,
    model_name: Optional[str],
    conv_id: str,
) -> Tuple[str, str]:
    """
    Ask an LLM to evaluate the child's performance in this simulation.
    Returns (outcome_label, summary_for_parent).
    """
    scenario = get_scenario_by_id(event.scenario_id)
    if scenario is None:
        return "NEEDS_REVIEW", "Scenario data missing; unable to evaluate."

    chat_history = _build_chat_history_for_conv(garden, child, conv_id)

    eval_prompt = f"""
You are an expert in children's digital safety.

Scenario:
- Name: {scenario.title}
- Risk type: {scenario.risk_type}
- Child age: {child.config.age}

Below is the chat transcript between the child and the simulated partner.
Each line is prefixed with CHILD or PARTNER.

Chat transcript:
{chat_history}

TASK:
1. Decide if the child's behavior was overall:
   - SAFE
   - UNSAFE
   - NEEDS_REVIEW (mixed, unclear, or borderline).
2. Explain your reasoning in 2–4 sentences, addressing a parent/guardian.

Format your answer as:

Label: SAFE/UNSAFE/NEEDS_REVIEW
Summary: <your explanation for the parent>
"""

    try:
        resp = call_llm(eval_prompt, backend=backend, model=model_name)
    except Exception as e:
        return "NEEDS_REVIEW", f"Could not run evaluation ({backend} {model_name}): {e}"

    label = "NEEDS_REVIEW"
    summary = resp.strip()

    lines = resp.splitlines()
    for line in lines:
        lower = line.lower().strip()
        if lower.startswith("label:"):
            raw = line.split(":", 1)[1].strip().upper()
            if "SAFE" in raw and "UNSAFE" not in raw:
                label = "SAFE"
            elif "UNSAFE" in raw:
                label = "UNSAFE"
            elif "NEEDS_REVIEW" in raw or "NEEDS REVIEW" in raw:
                label = "NEEDS_REVIEW"
            # summary is everything except the label line
            summary = "\n".join(
                l for l in lines if not l.lower().strip().startswith("label:")
            ).strip()
            if summary.lower().startswith("summary:"):
                summary = summary.split(":", 1)[1].strip()
            break

    return label, summary or resp.strip()
