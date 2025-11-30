# app.py

import streamlit as st
from typing import Dict, List, Tuple
import requests
import os
import random

from models import (
    GardenState,
    ChildConfig,
    Interest,
    ChildState,
    make_id,
    Profile
)
from avatar_utils import get_circular_avatar_for_profile
from feed_generator import generate_feed_for_child  # we'll define this function
from datetime import datetime
from scenarios import get_scenarios_for_child_age, get_scenario_by_id
from models import SimulationEvent

from simulation_engine import (
    start_simulation_session,
    generate_agent_reply_for_session,
    evaluate_simulation_session,
)

from username_utils import generate_username


from llm_client import call_llm  # for simulation LLM injection


# ---------- Available LLM detection ----------

def get_available_ollama_models() -> List[str]:
    """
    Query the Ollama HTTP API for available models.

    Expects OLLAMA_HOST to be something like:
      - http://localhost:11434
      - http://host.docker.internal:11434

    Returns a list of model names, e.g. ["llama3", "tinyllama"].

    If anything fails, returns an empty list (and the UI will fall back).
    """
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    url = f"{host}/api/tags"

    try:
        resp = requests.get(url, timeout=2)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    # Per Ollama docs, this is typically: {"models": [{"name": "llama3", ...}, ...]}
    models = data.get("models") or []
    names = []
    for m in models:
        name = m.get("name")
        if name:
            # Some tags include ":latest" or variants; strip them for UI friendliness
            names.append(name.split(":")[0])
    # Deduplicate while preserving order
    seen = set()
    result = []
    for n in names:
        if n not in seen:
            seen.add(n)
            result.append(n)
    return result


def openai_available() -> bool:
    """
    True if OPENAI_API_KEY is present and non-empty.
    """
    return bool(os.environ.get("OPENAI_API_KEY"))


def build_llm_backend_options() -> List[str]:
    """
    Decide which backends to show in the dropdown, based on environment.
    """
    options: List[str] = []
    if openai_available():
        options.append("openai")
    if get_available_ollama_models():
        options.append("ollama")
    return options

def llm_selection_ui(
    label_prefix: str,
    backend_state_key: str,
    model_state_key: str,
) -> Tuple[str, str]:
    """
    Render a pair of dropdowns in the sidebar:

    - Backend (openai / ollama), based on what's actually available.
    - Model (choices appropriate for the selected backend).

    Stores selections in st.session_state[backend_state_key/model_state_key]
    and returns (backend, model).
    """
    backend_options = build_llm_backend_options()

    if not backend_options:
        st.sidebar.error(
            "No LLM backend detected. "
            "Set OPENAI_API_KEY for OpenAI or configure OLLAMA_HOST and ensure Ollama is running."
        )
        # Safe fallbacks so the rest of the app doesn't explode
        return ("openai", "gpt-4.1-mini")

    has_openai = openai_available()
    ollama_models = get_available_ollama_models()
    has_ollama = bool(ollama_models)

    # ----- Decide default backend -----
    if backend_state_key not in st.session_state:
        if has_openai:
            default_backend = "openai"
        elif has_ollama:
            default_backend = "ollama"
        else:
            default_backend = backend_options[0]
        st.session_state[backend_state_key] = default_backend

    # Clamp to currently available backends
    if st.session_state[backend_state_key] not in backend_options:
        st.session_state[backend_state_key] = backend_options[0]

    backend = st.sidebar.selectbox(
        f"{label_prefix} backend",
        options=backend_options,
        index=backend_options.index(st.session_state[backend_state_key]),
        key=backend_state_key,
    )

    # ----- Model options per backend -----
    if backend == "openai":
        # You can extend this list if you want more OpenAI models
        model_options = ["gpt-4.1-mini", "gpt-4o-mini"]
    else:
        # Ollama: use detected models; fall back to a simple list if none detected
        model_options = ollama_models or ["llama3", "tinyllama"]

    if (
        model_state_key not in st.session_state
        or st.session_state[model_state_key] not in model_options
    ):
        st.session_state[model_state_key] = model_options[0]

    model = st.sidebar.selectbox(
        f"{label_prefix} model",
        options=model_options,
        index=model_options.index(st.session_state[model_state_key]),
        key=model_state_key,
    )

    return backend, model



# ---------- Session state setup ----------

def create_default_garden(name: str = "Default Garden") -> GardenState:
    """Create a garden with a single default child."""
    garden = GardenState(id=make_id("garden"), name=name)

    default_config = ChildConfig(
        name="Alex",
        age=10,
        interests=[Interest("space", 0.5), Interest("animals", 0.3), Interest("drawing", 0.2)],
        mode="realistic",
        max_posts=8,
    )
    garden.add_child(default_config)
    return garden

def get_feed_llm_config() -> Tuple[str, str]:
    """
    Returns (backend, model_name) for the feed generator,
    based on the sidebar dropdowns.
    """
    backend = st.session_state.get("feed_backend", "openai")
    if backend == "openai":
        model_name = st.session_state.get("feed_model", "gpt-4.1-mini")
    else:
        model_name = st.session_state.get("feed_model", "llama3")
    return backend, model_name


def get_sim_llm_config():
    """
    Returns (backend, model_name) for simulations.
    If simulation mode is 'same_as_feed', reuse feed config.
    """
    mode = st.session_state.get("sim_llm_mode", "same_as_feed")
    feed_backend, feed_model = get_feed_llm_config()

    if mode == "same_as_feed":
        return feed_backend, feed_model

    if mode == "openai":
        backend = "openai"
        model_name = st.session_state.get("sim_openai_model", "gpt-4.1-mini")
        return backend, model_name

    if mode == "ollama":
        backend = "ollama"
        model_name = st.session_state.get("sim_ollama_model", "llama3")
        return backend, model_name

    # Fallback
    return feed_backend, feed_model


def create_simulation_profile_for_child(garden: GardenState, child: ChildState, scenario_id: str) -> Profile:
    """
    Create a new synthetic profile to act as the simulation agent for this child.
    Profile is themed loosely around the scenario and child's mode.
    """
    scen = get_scenario_by_id(scenario_id)

    # Derive rough topic(s) from the scenario, if available
    scenario_topics = []
    if scen is not None:
        # You can extend this mapping per scenario fields if you have them
        scenario_topics.append(scen.risk_type)

    # Collect existing names to avoid duplicate display names in this garden
    existing_names = [p.display_name for p in garden.profiles]

    display_name = generate_username(
        mode=child.config.mode,
        topics=scenario_topics,
        existing_names=existing_names,
    )

    personality_pool = [
        "curious",
        "outgoing",
        "chatty",
        "confident",
        "playful",
        "casual",
    ]
    personality_tags = random.sample(personality_pool, k=2)

    topics = scenario_topics or ["chat"]

    avatar_style = "cartoony" if child.config.mode == "gamified" else "realistic"
    hue_shift = random.random()

    profile = Profile(
        id=make_id("profile"),
        role="synthetic",
        display_name=display_name,
        avatar_style=avatar_style,
        personality_tags=personality_tags,
        topics=topics,
        is_parent_controlled=False,
        avatar_hue_shift=hue_shift,
    )
    garden.profiles.append(profile)
    return profile



def init_session_state():
    if "gardens" not in st.session_state:
        st.session_state.gardens: Dict[str, GardenState] = {}
        default_garden = create_default_garden()
        st.session_state.gardens[default_garden.id] = default_garden
        st.session_state.active_garden_id = default_garden.id
        # set active_child_id to the only child in this garden
        only_child = next(iter(default_garden.children.values()))
        st.session_state.active_child_id = only_child.id

    # safety: ensure active IDs are valid
    gardens: Dict[str, GardenState] = st.session_state.gardens
    if "active_garden_id" not in st.session_state or st.session_state.active_garden_id not in gardens:
        # pick any existing garden
        if gardens:
            st.session_state.active_garden_id = next(iter(gardens.keys()))
        else:
            g = create_default_garden()
            gardens[g.id] = g
            st.session_state.active_garden_id = g.id

    garden = gardens[st.session_state.active_garden_id]
    if "active_child_id" not in st.session_state or st.session_state.active_child_id not in garden.children:
        # pick any child in this garden, or create one if none exist
        if not garden.children:
            default_config = ChildConfig(
                name="Alex",
                age=10,
                interests=[Interest("space", 0.5)],
                mode="realistic",
                max_posts=5,
            )
            new_child = garden.add_child(default_config)
            st.session_state.active_child_id = new_child.id
        else:
            st.session_state.active_child_id = next(iter(garden.children.keys()))
    


def get_active_garden() -> GardenState:
    gardens: Dict[str, GardenState] = st.session_state.gardens
    return gardens[st.session_state.active_garden_id]


def get_active_child(garden: GardenState) -> ChildState:
    return garden.children[st.session_state.active_child_id]


# ---------- Sidebar UI ----------

def sidebar_garden_and_child_management():
    st.sidebar.header("Environment")

    gardens: Dict[str, GardenState] = st.session_state.gardens

    # ---- Garden selection ----
    st.sidebar.subheader("Garden")
    garden_name_to_id = {g.name: g.id for g in gardens.values()}
    current_garden_id = st.session_state.active_garden_id
    current_garden_name = next(
        (name for name, gid in garden_name_to_id.items() if gid == current_garden_id),
        None,
    )

    chosen_garden_name = st.sidebar.selectbox(
        "Active garden",
        options=list(garden_name_to_id.keys()),
        index=list(garden_name_to_id.keys()).index(current_garden_name) if current_garden_name else 0,
    )
    st.session_state.active_garden_id = garden_name_to_id[chosen_garden_name]
    garden = get_active_garden()

    with st.sidebar.expander("Create new garden"):
        new_name = st.text_input("New garden name", value="", key="new_garden_name")
        if st.button("Create garden"):
            name = new_name.strip() or "New Garden"
            new_garden = create_default_garden(name)
            gardens[new_garden.id] = new_garden
            st.session_state.active_garden_id = new_garden.id
            # set active child to the default child's id
            default_child = next(iter(new_garden.children.values()))
            st.session_state.active_child_id = default_child.id
            st.success(f"Created garden '{name}'")
            st.rerun()  # ensure dropdowns and views update immediately

    # ---- Child selection & management ----
    st.sidebar.subheader("Children in this garden")

    children = garden.list_children()
    if not children:
        st.sidebar.info("No children in this garden yet. Add one below.")
        active_child = None
    else:
        label_by_id = {c.id: f"{c.config.name} ({c.config.age})" for c in children}
        # ensure active child is in this garden
        if st.session_state.active_child_id not in label_by_id:
            st.session_state.active_child_id = children[0].id

        # selectbox by label
        current_label = label_by_id[st.session_state.active_child_id]
        chosen_label = st.sidebar.selectbox(
            "Active child",
            options=list(label_by_id.values()),
            index=list(label_by_id.values()).index(current_label),
        )
        # update active_child_id
        for cid, label in label_by_id.items():
            if label == chosen_label:
                st.session_state.active_child_id = cid
                break
        active_child = get_active_child(garden)

    # ---- Add child ----
    with st.sidebar.expander("Add child"):
        new_child_name = st.text_input("Name", value="", key="new_child_name")
        new_child_age = st.number_input("Age", min_value=5, max_value=17, value=10, step=1, key="new_child_age")
        new_child_mode = st.radio("Mode", options=["realistic", "gamified"], index=0, key="new_child_mode")

        st.markdown("Interests (simple version)")
        topic1 = st.text_input("Topic 1", value="space", key="new_child_topic_1")
        topic2 = st.text_input("Topic 2", value="animals", key="new_child_topic_2")
        interests = []
        if topic1.strip():
            interests.append(Interest(topic1.strip(), 0.6))
        if topic2.strip():
            interests.append(Interest(topic2.strip(), 0.4))
        if not interests:
            interests = [Interest("general", 1.0)]

        if st.button("Create child"):
            cfg = ChildConfig(
                name=new_child_name.strip() or "New Child",
                age=int(new_child_age),
                interests=interests,
                mode=new_child_mode,  # type: ignore
                max_posts=8,
            )
            new_child = garden.add_child(cfg)
            st.session_state.active_child_id = new_child.id
            st.success(f"Created child '{cfg.name}'")
            st.rerun()  # refresh child dropdown and header

    # ---- Edit active child ----
    if active_child is not None:
        st.sidebar.subheader("Active child settings")

        cfg = active_child.config
        edited_name = st.sidebar.text_input("Name", value=cfg.name, key="edit_child_name")
        edited_age = st.sidebar.number_input("Age", min_value=5, max_value=17, value=cfg.age, step=1, key="edit_child_age")
        edited_mode = st.sidebar.radio(
            "Mode",
            options=["realistic", "gamified"],
            index=0 if cfg.mode == "realistic" else 1,
            key="edit_child_mode",
        )
        edited_max_posts = st.sidebar.slider("Max posts", min_value=3, max_value=30, value=cfg.max_posts, key="edit_child_max_posts")

        if st.sidebar.button("Save child settings"):
            # For now we keep interests unchanged here; interest editing UI can come later
            active_child.config = ChildConfig(
                name=edited_name.strip() or cfg.name,
                age=int(edited_age),
                interests=cfg.interests,
                mode=edited_mode,  # type: ignore
                max_posts=int(edited_max_posts),
            )
            # update child profile display name if needed
            garden.ensure_child_profile(active_child)
            st.sidebar.success("Child settings updated.")
            st.rerun()  # update labels, header, and any dependent views

        if st.sidebar.button("Generate feed for this child"):
            backend, model_name = get_feed_llm_config()
            generate_feed_for_child(garden, active_child, backend=backend, model_name=model_name)
            st.sidebar.success(f"Feed generated using {backend} ({model_name}).")
            st.rerun()


    # ---- LLM backend selection ----
    st.sidebar.subheader("LLM backends")

    st.sidebar.markdown("**Feed generation**")
    feed_backend, feed_model = llm_selection_ui(
        label_prefix="Feed",
        backend_state_key="feed_backend",
        model_state_key="feed_model",
    )

    st.sidebar.markdown("**Simulations**")
    sim_backend, sim_model = llm_selection_ui(
        label_prefix="Simulation",
        backend_state_key="sim_backend",
        model_state_key="sim_model",
    )






# ---------- Main tabs ----------

def overview_tab(garden: GardenState, child: ChildState):
    st.subheader("Overview")
    st.write(f"**Garden:** {garden.name}")
    st.write(f"**Child:** {child.config.name} ({child.config.age} y/o, mode: {child.config.mode})")

    summary = child.summary()
    col1, col2, col3 = st.columns(3)
    col1.metric("Posts", summary["posts_count"])
    col2.metric("DM messages", summary["dm_count"])
    col3.metric("Max posts setting", child.config.max_posts)

    if child.posts:
        st.markdown("### Recent posts")
        for post in child.posts[:3]:
            st.markdown(f"- **{post.topic}**: {post.text}")
    else:
        st.info("No posts yet. Generate a feed from the sidebar.")

    if child.dm_messages:
        st.markdown("### Recent DMs")
        # Show the last 3 messages
        last_msgs = sorted(child.dm_messages, key=lambda m: m.created_at, reverse=True)[:3]
        for msg in last_msgs:
            sender = garden.get_profile_by_id(msg.sender_profile_id)
            sender_name = sender.display_name if sender else "Unknown"
            st.markdown(f"- **{sender_name}**: {msg.text}")
    else:
        st.info("No DMs yet for this child.")


def feed_tab(garden: GardenState, child: ChildState) -> None:
    st.header(f"Feed for {child.config.name}")

    feed_view, settings_view = st.tabs(["Feed", "Feed settings"])

    with feed_view:
        if st.button("Generate feed for this child"):
            backend, model_name = get_feed_llm_config()
            generate_feed_for_child(garden, child, backend=backend, model_name=model_name)
            st.success("Feed generated.")
            st.rerun()

        if not child.posts:
            st.info("No posts yet. Generate a feed to get started.")
        else:
            # Sort posts by timestamp, newest first
            posts_sorted = sorted(child.posts, key=lambda p: p.created_at, reverse=True)

            for post in posts_sorted:
                author_profile = garden.get_profile_by_id(post.author_profile_id)

                with st.container():
                    col_avatar, col_text, col_image = st.columns([1, 7, 3])

                    with col_avatar:
                        if author_profile is not None:
                            try:
                                avatar_img = get_circular_avatar_for_profile(author_profile, size=40)
                                st.image(avatar_img, width=40)
                            except Exception:
                                st.markdown("🧑")
                        else:
                            st.markdown("🧑")

                    with col_text:
                        # Format timestamp
                        ts = post.created_at.strftime("%Y-%m-%d %H:%M")
                        st.markdown(
                            f"**{post.author_name}**  \n"
                            f"*Topic: {post.topic}* · `{ts}`"
                        )
                        st.write(post.text)

                    with col_image:
                        if post.image_url:
                            try:
                                st.image(post.image_url, width=120)
                            except Exception:
                                st.caption("Image unavailable")

                    st.markdown("---")




    with settings_view:
        st.subheader("Feed settings")

        # Interests and weights (simple UI – adjust to your existing pattern)
        st.markdown("**Topics & interests**")
        current_topics = [i.topic for i in child.config.interests]
        default_suggestions = ["space", "animals", "drawing", "science", "history", "music", "sports"]

        # Multi-select suggestions + existing topics
        topic_choices = sorted(set(default_suggestions + current_topics))
        selected_topics = st.multiselect(
            "Select topics",
            options=topic_choices,
            default=current_topics,
            key=f"topics_select_{child.id}",
        )

        # Simple: give all selected topics equal weight.
        # (You can keep your existing per-topic sliders if you like; this is the minimal version.)
        new_interests = []
        if selected_topics:
            equal_weight = 1.0 / len(selected_topics)
            for t in selected_topics:
                new_interests.append(Interest(topic=t, weight=equal_weight))

        # Post volume settings
        st.markdown("**Post volume**")
        max_posts = st.slider(
            "Max posts (normal hours)",
            min_value=1,
            max_value=30,
            value=child.config.max_posts,
            key=f"max_posts_{child.id}",
        )
        max_posts_quiet = st.slider(
            "Max posts during quiet hours (school/late)",
            min_value=0,
            max_value=30,
            value=child.config.max_posts_quiet or child.config.max_posts,
            key=f"max_posts_quiet_{child.id}",
        )

        st.markdown("**Content style**")
        news_ratio = st.slider(
            "Fraction of posts that are kid-friendly news",
            min_value=0.0,
            max_value=1.0,
            value=child.config.news_ratio,
            step=0.05,
            key=f"news_ratio_{child.id}",
        )

        image_ratio = st.slider(
            "Fraction of posts that include an image",
            min_value=0.0,
            max_value=1.0,
            value=child.config.image_ratio,
            step=0.05,
            key=f"image_ratio_{child.id}",
        )

        if st.button("Save feed settings", key=f"save_feed_settings_{child.id}"):
            if new_interests:
                child.config.interests = new_interests
            child.config.max_posts = max_posts
            child.config.max_posts_quiet = max_posts_quiet
            child.config.news_ratio = news_ratio
            child.config.image_ratio = image_ratio
            st.success("Feed settings updated.")
            st.rerun()



def dm_tab(garden: GardenState, child: ChildState):
    st.subheader("Direct Messages")

    # Identify conversation partners for this child
    partners = {}
    for msg in child.dm_messages:
        # Determine "other" profile in this message
        if msg.sender_profile_id == child.profile_id:
            other_id = msg.receiver_profile_id
        else:
            other_id = msg.sender_profile_id
        if other_id not in partners:
            prof = garden.get_profile_by_id(other_id)
            partners[other_id] = prof.display_name if prof else other_id

    # Also allow starting new conversations with any profile in this garden
    all_profiles = [p for p in garden.profiles if p.id != child.profile_id]
    new_conv_options = {p.display_name: p.id for p in all_profiles}

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("#### Conversations")
        if partners:
            # maintain selected conversation in session
            conv_key = f"active_conv_{child.id}"
            # default: pick first if none selected
            if conv_key not in st.session_state or st.session_state[conv_key] not in partners:
                st.session_state[conv_key] = next(iter(partners.keys()))

            # radio by label
            labels = {pid: name for pid, name in partners.items()}
            current_pid = st.session_state[conv_key]
            current_label = labels[current_pid]
            chosen_label = st.radio(
                "Select a conversation",
                options=list(labels.values()),
                index=list(labels.values()).index(current_label),
            )
            for pid, label in labels.items():
                if label == chosen_label:
                    st.session_state[conv_key] = pid
                    break
        else:
            st.info("No conversations yet.")

        st.markdown("#### Start new conversation")
        if new_conv_options:
            chosen_name = st.selectbox("Profile", list(new_conv_options.keys()), key=f"new_conv_profile_{child.id}")
            if st.button("Start conversation"):
                other_id = new_conv_options[chosen_name]
                conv_id = f"conv_{child.id}_{other_id}"
                # No need to create any messages yet; selecting this will show empty chat
                st.session_state[f"active_conv_{child.id}"] = other_id
        else:
            st.info("No other profiles available in this garden yet.")

    with col_right:
        st.markdown("#### Messages")
        conv_key = f"active_conv_{child.id}"
        if conv_key not in st.session_state:
            st.info("Select or start a conversation on the left.")
            return

        other_profile_id = st.session_state[conv_key]
        other_profile = garden.get_profile_by_id(other_profile_id)
        other_name = other_profile.display_name if other_profile else "Unknown profile"

        st.markdown(f"**Chat between {child.config.name} and {other_name}**")

        # --- Simulation controls (session-based) ---
        st.markdown("##### Simulation tools")

        # Simulations only make sense with non-child partners
        if other_profile is None or other_profile.role == "child":
            st.info("Simulation agents can only be attached to non-child profiles.")
        else:
            scenarios = get_scenarios_for_child_age(child.config.age)

            # Check if there's an active session for this child + partner
            active_events = [
                e
                for e in child.simulation_events
                if e.partner_profile_id == other_profile_id and e.is_active
            ]
            active_event = None
            if active_events:
                active_events.sort(key=lambda e: e.created_at, reverse=True)
                active_event = active_events[0]

            if active_event is None:
                # No active session: allow starting one
                if scenarios:
                    scenario_labels = {f"{s.title} ({s.risk_type})": s.id for s in scenarios}
                    default_label = list(scenario_labels.keys())[0]
                    chosen_label = st.selectbox(
                        "Start a simulation scenario in this conversation",
                        options=list(scenario_labels.keys()),
                        index=list(scenario_labels.keys()).index(default_label),
                        key=f"scenario_select_{child.id}",
                    )
                    chosen_scenario_id = scenario_labels[chosen_label]

                    if st.button("Start simulation session", key=f"start_sim_{child.id}"):
                        backend, model_name = get_sim_llm_config()
                        conv_id = f"conv_{child.id}_{other_profile_id}"
                        try:
                            event, _sim_msg = start_simulation_session(
                                garden=garden,
                                child=child,
                                scenario_id=chosen_scenario_id,
                                partner_profile_id=other_profile_id,
                                backend=backend,
                                model_name=model_name,
                                conv_id=conv_id,
                            )
                            st.success(
                                f"Started simulation '{chosen_label}' using {backend} ({model_name})."
                            )
                            st.rerun()
                        except Exception as e:
                            st.warning(f"Could not start simulation: {e}")
                else:
                    st.info("No scenarios available for this age yet.")
            else:
                # There is an active session
                from scenarios import get_scenario_by_id

                scen = get_scenario_by_id(active_event.scenario_id)
                scen_title = scen.title if scen else active_event.scenario_id
                st.markdown(
                    f"**Active simulation:** {scen_title}  \n"
                    f"Backend: {active_event.backend_used or 'n/a'}  "
                    f"Model: {active_event.model_used or 'n/a'}"
                )
                if st.button("End simulation & evaluate", key=f"end_eval_sim_{child.id}"):
                    backend, model_name = get_sim_llm_config()
                    conv_id = f"conv_{child.id}_{other_profile_id}"
                    label, summary = evaluate_simulation_session(
                        garden=garden,
                        child=child,
                        event=active_event,
                        backend=backend,
                        model_name=model_name,
                        conv_id=conv_id,
                    )
                    active_event.outcome_label = label
                    active_event.evaluation_summary = summary
                    active_event.is_active = False
                    st.success(f"Simulation evaluated: {label}")
                    st.info(summary)
                    st.rerun()

        st.markdown("---")

        # --- Existing message history ---
        conv_id = f"conv_{child.id}_{other_profile_id}"
        history = [m for m in child.dm_messages if m.conversation_id == conv_id]
        history = sorted(history, key=lambda m: m.created_at)

        if history:
            for msg in history:
                sender = garden.get_profile_by_id(msg.sender_profile_id)
                sender_name = sender.display_name if sender else "Unknown"
                prefix = "🧒" if msg.sender_profile_id == child.profile_id else "👤"
                # Mark simulation messages
                tag = ""
                if msg.is_simulation:
                    tag = " _(simulation)_"
                st.markdown(f"{prefix} **{sender_name}:** {msg.text}{tag}")
        else:
            st.info("No messages yet in this conversation.")

        st.markdown("---")
        st.markdown("Send a message as the child")

        new_text = st.text_area("Message", height=80, key=f"dm_input_{child.id}")
        if st.button("Send", key=f"dm_send_{child.id}"):
            if new_text.strip():
                from models import DMMessage  # import here to avoid circular import in some setups
                from datetime import datetime as _dt

                garden.ensure_child_profile(child)
                text = new_text.strip()
                now = _dt.utcnow()

                # Message from this child's perspective
                msg = DMMessage(
                    id=make_id("dm"),
                    child_id=child.id,
                    conversation_id=conv_id,
                    sender_profile_id=child.profile_id,
                    receiver_profile_id=other_profile_id,
                    text=text,
                    created_at=now,
                )
                child.dm_messages.append(msg)

                # Attach this as the first reply to the latest simulation event (if any)
                pending_events = [
                    e
                    for e in child.simulation_events
                    if e.partner_profile_id == other_profile_id and e.child_reply_message_id is None
                ]
                if pending_events:
                    pending_events.sort(key=lambda e: e.created_at, reverse=True)
                    latest_event = pending_events[0]
                    latest_event.child_reply_message_id = msg.id

                # If the other profile is another child, mirror the message into their DM list too
                other_profile = garden.get_profile_by_id(other_profile_id)
                if other_profile and other_profile.role == "child":
                    other_child = None
                    for c in garden.list_children():
                        if c.profile_id == other_profile_id:
                            other_child = c
                            break
                    if other_child is not None:
                        other_conv_id = f"conv_{other_child.id}_{child.profile_id}"
                        mirrored_msg = DMMessage(
                            id=make_id("dm"),
                            child_id=other_child.id,
                            conversation_id=other_conv_id,
                            sender_profile_id=child.profile_id,
                            receiver_profile_id=other_profile_id,
                            text=text,
                            created_at=now,
                        )
                        other_child.dm_messages.append(mirrored_msg)

                # If there's an active simulation session with this partner, generate agent reply
                active_events = [
                    e
                    for e in child.simulation_events
                    if e.partner_profile_id == other_profile_id and e.is_active
                ]
                if active_events and (other_profile is None or other_profile.role != "child"):
                    active_events.sort(key=lambda e: e.created_at, reverse=True)
                    active_event = active_events[0]
                    backend, model_name = get_sim_llm_config()
                    agent_msg = generate_agent_reply_for_session(
                        garden=garden,
                        child=child,
                        event=active_event,
                        backend=backend,
                        model_name=model_name,
                        conv_id=conv_id,
                    )
                    # agent_msg is already added to child.dm_messages inside the function

                st.success("Message sent.")
                st.rerun()
            else:
                st.warning("Please type a message before sending.")


def analytics_tab(garden: GardenState, child: ChildState) -> None:
    st.header(f"Analytics for {child.config.name}")

    # --- Basic stats ---
    st.subheader("Overview")

    st.write(
        f"- Age: **{child.config.age}**  \n"
        f"- Mode: **{child.config.mode}**  \n"
        f"- Posts generated: **{len(child.posts)}**  \n"
        f"- DM messages: **{len(child.dm_messages)}**  \n"
        f"- Simulation sessions: **{len(child.simulation_events)}**"
    )

    st.markdown("---")

    # --- Quick auto simulation (one-click) ---
    st.subheader("Quick auto simulation")

    scenarios = get_scenarios_for_child_age(child.config.age)
    if not scenarios:
        st.info("No scenarios available for this child's age yet.")
    else:
        # Build choices
        scenario_labels = {f"{s.title} ({s.risk_type})": s.id for s in scenarios}
        default_label = list(scenario_labels.keys())[0]

        chosen_label = st.selectbox(
            "Choose a scenario to auto-run",
            options=list(scenario_labels.keys()),
            index=list(scenario_labels.keys()).index(default_label),
            key=f"auto_sim_scenario_{child.id}",
        )
        chosen_scenario_id = scenario_labels[chosen_label]

        if st.button("Run auto simulation now", key=f"auto_sim_run_{child.id}"):
            backend, model_name = get_sim_llm_config()
            # 1) Create a new synthetic profile as the agent
            profile = create_simulation_profile_for_child(
                garden=garden,
                child=child,
                scenario_id=chosen_scenario_id,
            )
            # 2) Conversation id between this child and the new agent profile
            conv_id = f"conv_{child.id}_{profile.id}"

            try:
                # 3) Start the simulation session (inject first message)
                event, _sim_msg = start_simulation_session(
                    garden=garden,
                    child=child,
                    scenario_id=chosen_scenario_id,
                    partner_profile_id=profile.id,
                    backend=backend,
                    model_name=model_name,
                    conv_id=conv_id,
                )
                # No pending agent reply yet; first move was just created above.

                st.success(
                    f"Started auto simulation '{chosen_label}' with profile **{profile.display_name}** "
                    f"using {backend} ({model_name}). "
                    "The child will see a new chat with this profile."
                )
                st.rerun()
            except Exception as e:
                st.warning(f"Could not start auto simulation: {e}")

    st.markdown("---")
    st.subheader("Simulation sessions")

    events = sorted(child.simulation_events, key=lambda e: e.created_at, reverse=True)

    if not events:
        st.info("No simulation sessions have been run for this child yet.")
        return

    # ---- Helper: status + badges ----
    def get_status(e) -> str:
        return (e.outcome_label or "UNEVALUATED").upper()

    def status_badge(status: str) -> str:
        status = status.upper()
        if status == "SAFE":
            return "🟢 SAFE"
        if status == "UNSAFE":
            return "🔴 UNSAFE"
        if status in ("NEEDS_REVIEW", "NEEDS REVIEW"):
            return "🟡 NEEDS REVIEW"
        return "⚪ UNEVALUATED"

    # ---- Filter by outcome ----
    status_options = ["All statuses", "SAFE", "UNSAFE", "NEEDS_REVIEW", "UNEVALUATED"]
    status_choice = st.selectbox(
        "Filter sessions by outcome",
        options=status_options,
        index=0,
        key=f"sim_status_filter_{child.id}",
    )

    if status_choice == "All statuses":
        filtered_events = events
    else:
        filtered_events = [
            e for e in events
            if get_status(e) == status_choice
        ]

    if not filtered_events:
        st.info(f"No simulation sessions matching filter: **{status_choice}**.")
        return

    # ---- "Carousel" of runs with short titles ----
    label_to_event = {}
    option_labels = []

    for e in filtered_events:
        scen = get_scenario_by_id(e.scenario_id)
        scen_title = scen.title if scen else e.scenario_id
        status = get_status(e)
        badge = status_badge(status)
        ts_str = e.created_at.strftime("%Y-%m-%d %H:%M")

        # Global run number (stable across filters)
        global_index = events.index(e)  # 0 = newest
        run_no = len(events) - global_index  # oldest = 1, newest = len(events)

        label = f"Run #{run_no} – {scen_title} • {badge} • {ts_str}"
        option_labels.append(label)
        label_to_event[label] = e

    selected_label = st.selectbox(
        "Select a simulation session",
        options=option_labels,
        key=f"sim_session_select_{child.id}",
    )
    event = label_to_event[selected_label]

    scen = get_scenario_by_id(event.scenario_id)
    scen_title = scen.title if scen else event.scenario_id
    status = get_status(event)
    badge = status_badge(status)

    st.markdown(f"### {scen_title}")
    st.write(f"- **Run ID:** `{event.id}`")
    st.write(f"- **Outcome:** {badge}")
    st.write(f"- Partner profile ID: `{event.partner_profile_id}`")
    st.write(f"- Started at: `{event.created_at.isoformat(timespec='seconds')}`")
    st.write(f"- Backend: **{event.backend_used or 'n/a'}**, model: **{event.model_used or 'n/a'}**")
    st.write(f"- Active: **{event.is_active}**")

    # Outcome summary
    st.markdown("#### Outcome summary")

    if event.evaluation_summary:
        st.markdown("**Summary for parent:**")
        st.write(event.evaluation_summary)
    else:
        st.info("This simulation has not been evaluated yet. Use 'End simulation & evaluate' in the DMs tab.")

    # Conversation transcript
    st.markdown("#### Conversation transcript")

    with st.expander("View chat log", expanded=False):
        conv_id = f"conv_{child.id}_{event.partner_profile_id}"
        messages = [
            m for m in child.dm_messages if m.conversation_id == conv_id
        ]
        messages.sort(key=lambda m: m.created_at)

        if not messages:
            st.info("No messages found for this simulation conversation.")
        else:
            for m in messages:
                sender = garden.get_profile_by_id(m.sender_profile_id)
                sender_name = sender.display_name if sender else "Unknown"
                is_child = m.sender_profile_id == child.profile_id

                prefix = "🧒 CHILD" if is_child else "👤 PARTNER"
                sim_tag = " _(simulation)_" if m.is_simulation else ""
                timestamp = m.created_at.strftime("%Y-%m-%d %H:%M:%S")

                st.markdown(
                    f"{prefix}{sim_tag}  \n"
                    f"**{sender_name}** at `{timestamp}`  \n"
                    f"{m.text}"
                )




# ---------- Main ----------

def main():
    st.set_page_config(page_title="Panopticon – Social Media Simulator", layout="wide")
    init_session_state()

    sidebar_garden_and_child_management()
    garden = get_active_garden()
    child = get_active_child(garden)

    st.title("Panopticon")
    st.caption("Parent-curated, AI-assisted social media simulator for children (prototype).")
    st.markdown(f"**Garden:** {garden.name} · **Child:** {child.config.name} ({child.config.age}, mode: {child.config.mode})")

    tabs = st.tabs(["Overview", "Feed", "DMs", "Analytics"])
    with tabs[0]:
        overview_tab(garden, child)
    with tabs[1]:
        feed_tab(garden, child)
    with tabs[2]:
        dm_tab(garden, child)
    with tabs[3]:
        analytics_tab(garden, child)


if __name__ == "__main__":
    main()
