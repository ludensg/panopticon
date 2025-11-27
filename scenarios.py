# scenarios.py

from __future__ import annotations

from typing import List, Optional

from models import SimulationScenario


# You can tune these later; keeping them simple and non-traumatic for now.
DEFAULT_SCENARIOS: List[SimulationScenario] = [
    SimulationScenario(
        id="stranger_asking_address",
        title="Stranger asking for your address",
        description=(
            "A new online 'friend' asks the child where they live or wants them to share their address/"
            "location. This tests how the child responds to sharing private information."
        ),
        risk_type="privacy",
        recommended_age_min=8,
        recommended_age_max=15,
        system_prompt_template="""
You are role-playing a kid-safe but slightly risky message in a digital literacy training simulation.

Your role:
- You are an online acquaintance the child has just met.
- You are curious and friendly, but you ask for the child's address or where they live.
- The message MUST NOT be explicit, frightening, or aggressive.
- It should be subtle enough to seem like a normal chat, but clearly request location info.
- The child is around {child_age} years old.
- Do NOT mention AI, simulation, or training.
Return ONE short message only (1–2 sentences).
""",
        user_message_template="""
The child's name is {child_name}.
Write the message you send to them in the chat.
""",
        canned_message_template="Hey {child_name}, you seem really cool! What city do you live in? 😊",
    ),
    SimulationScenario(
        id="peer_pressure_share_photo",
        title="Peer pressure to share a photo",
        description=(
            "A peer or online friend encourages the child to send a photo. "
            "This tests how the child handles pressure to share personal images."
        ),
        risk_type="privacy",
        recommended_age_min=10,
        recommended_age_max=17,
        system_prompt_template="""
You are role-playing a classmate or online friend asking the child to send a photo.

Your role:
- You are friendly and casual.
- You encourage the child to send a picture of themselves or their face.
- The message must stay kid-safe and not sexualized or explicit in any way.
- The child is around {child_age} years old.
- Do NOT mention AI, simulation, or training.
Return ONE short message only (1–2 sentences).
""",
        user_message_template="""
The child's name is {child_name}.
Write the message you send to them in the chat.
""",
        canned_message_template="Everyone is sending selfies in the group 😄 you should send one too, {child_name}!",
    ),
    SimulationScenario(
        id="unfriendly_comment",
        title="Unfriendly or teasing comment",
        description=(
            "Someone leaves a slightly mean or teasing comment about something the child likes. "
            "This tests how the child responds to low-level negativity."
        ),
        risk_type="bullying",
        recommended_age_min=8,
        recommended_age_max=17,
        system_prompt_template="""
You are role-playing a peer making a slightly unfriendly or teasing comment.

Your role:
- You are not extremely cruel, but you are unkind or dismissive about something the child likes.
- The message should be mild enough to be age-appropriate but clearly not friendly.
- Avoid slurs, explicit content, or intense bullying.
- The child is around {child_age} years old.
- Do NOT mention AI, simulation, or training.
Return ONE short message only (1–2 sentences).
""",
        user_message_template="""
The child's name is {child_name}.
Write the message you send to them in the chat.
""",
        canned_message_template="You post about that game a lot, {child_name}… it's kind of lame tbh.",
    ),
]


def get_scenarios_for_child_age(age: int) -> List[SimulationScenario]:
    """Return scenarios appropriate for the given age."""
    return [
        s
        for s in DEFAULT_SCENARIOS
        if s.recommended_age_min <= age <= s.recommended_age_max
    ]


def get_scenario_by_id(scenario_id: str) -> Optional[SimulationScenario]:
    for s in DEFAULT_SCENARIOS:
        if s.id == scenario_id:
            return s
    return None
