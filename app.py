# app.py

import streamlit as st
from typing import Dict

from models import (
    GardenState,
    ChildConfig,
    Interest,
    ChildState,
    make_id,
)
from avatar_utils import load_base_avatar, tint_avatar
from feed_generator import generate_feed_for_child  # we'll define this function
from datetime import datetime


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
            # Decide which model string to pass based on backend
            backend = st.session_state.get("llm_backend", "openai")
            if backend == "openai":
                model_name = st.session_state.get("openai_model", "gpt-4.1-mini")
            else:
                model_name = st.session_state.get("ollama_model", "llama3")

            generate_feed_for_child(garden, active_child, backend=backend, model_name=model_name)
            st.sidebar.success(f"Feed generated using {backend} ({model_name}).")
            st.rerun()


    # ---- AI backend selection ----
    st.sidebar.subheader("AI Backend")

    backend = st.sidebar.radio(
        "Backend",
        options=["openai", "ollama"],
        index=0,
        key="llm_backend",
        help="Choose whether to use OpenAI's API or a local Ollama model.",
    )

    openai_model = st.sidebar.text_input(
        "OpenAI model",
        value=st.session_state.get("openai_model", "gpt-4.1-mini"),
        key="openai_model",
    )

    ollama_model = st.sidebar.text_input(
        "Ollama model",
        value=st.session_state.get("ollama_model", "llama3"),
        key="ollama_model",
        help="Make sure you've pulled this model with `ollama pull <model>`.",
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


def feed_tab(garden: GardenState, child: ChildState):
    st.subheader("Feed")

    if not child.posts:
        st.info("No posts yet. Click 'Generate feed for this child' in the sidebar.")
        return

    base_avatar = load_base_avatar()
    for post in child.posts:
        author = garden.get_profile_by_id(post.author_profile_id)
        if not author:
            continue

        with st.container():
            cols = st.columns([1, 5])
            with cols[0]:
                tinted = tint_avatar(author.avatar_hue_shift, base_avatar)
                st.image(tinted, use_container_width=True)
            with cols[1]:
                st.markdown(f"**{author.display_name}** · _Topic: {post.topic}_")
                st.write(post.text)
        st.markdown("---")


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

        conv_id = f"conv_{child.id}_{other_profile_id}"
        history = [m for m in child.dm_messages if m.conversation_id == conv_id]
        history = sorted(history, key=lambda m: m.created_at)

        if history:
            for msg in history:
                sender = garden.get_profile_by_id(msg.sender_profile_id)
                sender_name = sender.display_name if sender else "Unknown"
                prefix = "🧒" if msg.sender_profile_id == child.profile_id else "👤"
                st.markdown(f"{prefix} **{sender_name}:** {msg.text}")
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

                # If the other profile is another child, mirror the message into their DM list too
                other_profile = garden.get_profile_by_id(other_profile_id)
                if other_profile and other_profile.role == "child":
                    # Find the ChildState that owns this profile
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

                st.success("Message sent.")
                st.rerun()
            else:
                st.warning("Please type a message before sending.")




def analytics_tab(garden: GardenState, child: ChildState):
    st.subheader("Analytics (basic)")
    st.write("This will show topic distributions, simulation outcomes, etc.")
    st.write("For now, just showing some raw counts:")

    from collections import Counter

    topics = [p.topic for p in child.posts]
    topic_counts = Counter(topics)
    st.markdown("**Topics in feed:**")
    if topic_counts:
        for topic, count in topic_counts.items():
            st.write(f"- {topic}: {count} posts")
    else:
        st.write("- (no posts yet)")

    st.markdown("**DMs by conversation partner:**")
    partner_counts = Counter()
    for msg in child.dm_messages:
        if msg.sender_profile_id == child.profile_id:
            other_id = msg.receiver_profile_id
        else:
            other_id = msg.sender_profile_id
        partner_counts[other_id] += 1

    if partner_counts:
        for pid, count in partner_counts.items():
            prof = garden.get_profile_by_id(pid)
            name = prof.display_name if prof else pid
            st.write(f"- {name}: {count} messages")
    else:
        st.write("- (no DMs yet)")

    sim_counts = Counter(m.simulation_tag for m in child.dm_messages if m.is_simulation)
    st.markdown("**Simulation events (by tag):**")
    if sim_counts:
        for tag, count in sim_counts.items():
            st.write(f"- {tag or '(untagged)'}: {count}")
    else:
        st.write("- (no simulation events yet)")


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
