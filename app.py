# app.py

import streamlit as st
from typing import List
from datetime import datetime
import uuid

from models import Interest, ChildConfig, DMMessage, Profile
from feed_generator import generate_feed
from avatar_utils import get_avatar_for_profile




def init_session_state():
    """
    Ensure we have the basic session_state containers
    to hold generated posts, profiles, and DMs.
    """
    if "posts" not in st.session_state:
        st.session_state["posts"] = []
    if "profiles" not in st.session_state:
        st.session_state["profiles"] = []
    if "dm_messages" not in st.session_state:
        st.session_state["dm_messages"] = []  # List[DMMessage]


def main():
    st.set_page_config(page_title="Panopticon – Micro-MVP", layout="wide")
    init_session_state()

    st.title("Panopticon – Micro-MVP Demo")

    # Sidebar: Parent config
    st.sidebar.header("Parent Configuration")

    child_name = st.sidebar.text_input("Child name", value="Alex")
    child_age = st.sidebar.number_input("Child age", min_value=5, max_value=16, value=9)

    st.sidebar.markdown("### Interests")
    possible_interests = ["space", "dinosaurs", "drawing", "music", "animals"]
    selected = st.sidebar.multiselect("Select interests", possible_interests, default=["space", "animals"])

    interests: List[Interest] = []
    for topic in selected:
        w = st.sidebar.slider(f"Interest in {topic}", 0.1, 1.0, 0.7)
        interests.append(Interest(topic=topic, weight=w))

    mode = st.sidebar.radio("Mode", options=["realistic", "gamified"], index=1)
    max_posts = st.sidebar.slider("Number of posts", 3, 15, 8)

    generate_button = st.sidebar.button("Generate Feed")

    # Create tabs: Feed + DMs (for future simulations)
    feed_tab, dm_tab = st.tabs(["Feed", "Direct Messages (DMs)"])

    # ----- FEED TAB -----
    with feed_tab:
        st.subheader("Child View – Feed")

        if generate_button:
            child_cfg = ChildConfig(
                name=child_name,
                age=int(child_age),
                interests=interests,
                mode=mode,
                max_posts=int(max_posts),
            )
            with st.spinner("Generating feed..."):
                posts, profiles = generate_feed(child_cfg)

            # Store in session_state so DM tab can access profiles
            st.session_state["posts"] = posts
            st.session_state["profiles"] = profiles

        posts = st.session_state.get("posts", [])
        profiles: List[Profile] = st.session_state.get("profiles", [])

        if not posts:
            st.info("Configure the child and click 'Generate Feed' in the sidebar.")
        else:
            profiles_by_id = {p.id: p for p in profiles}

            for post in posts:
                prof = profiles_by_id.get(post.author_profile_id)

                with st.container():
                    cols = st.columns([1, 8])

                    with cols[0]:
                        if prof is not None:
                            try:
                                avatar_img = get_avatar_for_profile(prof)
                                st.image(avatar_img, width=56)
                            except Exception as e:
                                st.caption("No avatar")
                        else:
                            st.caption("")

                    with cols[1]:
                        st.markdown(f"**{post.author_name}** · *{post.topic}*")
                        st.write(post.text)

                    st.markdown("---")


    # ----- DM TAB -----
    with dm_tab:
        st.subheader("Direct Messages – Prototype for Simulations")

        profiles: List[Profile] = st.session_state.get("profiles", [])

        if not profiles:
            st.info("No profiles available yet. Generate a feed first to create synthetic profiles.")
        else:
            # Select which profile to DM with (from child's perspective)
            profile_options = {p.display_name: p for p in profiles}
            selected_name = st.selectbox(
                "Select a profile to open a DM conversation with:",
                list(profile_options.keys()),
            )
            active_profile = profile_options[selected_name]

            header_cols = st.columns([1, 5])
            with header_cols[0]:
                try:
                    avatar_img = get_avatar_for_profile(active_profile)
                    st.image(avatar_img, width=56)
                except Exception:
                    st.caption("No avatar")

            with header_cols[1]:
                st.markdown(
                    f"**Conversation with:** `{active_profile.display_name}`  \n"
                    f"*role: {active_profile.role}, avatar: {active_profile.avatar_style}*"
                )

            st.markdown("---")


            # Filter DM messages for this conversation (child <-> profile)
            all_msgs: List[DMMessage] = st.session_state.get("dm_messages", [])
            conversation_id = f"conv_child_{active_profile.id}"

            conv_msgs = [
                m for m in all_msgs
                if m.conversation_id == conversation_id
            ]

            # Show message history
            if not conv_msgs:
                st.caption("No messages yet. Start the conversation below.")
            else:
                for msg in conv_msgs:
                    sender = "Child" if msg.sender_profile_id == "child_profile" else active_profile.display_name
                    align = "➡️" if sender == "Child" else "⬅️"
                    st.markdown(f"**{sender} {align}**  \n{msg.text}")

            st.markdown("---")

            # Simple input for child message (from child's perspective)
            new_msg = st.text_area("Type a new message as the child:", height=80)

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button("Send (child → profile)"):
                    if new_msg.strip():
                        msg = DMMessage(
                            id=f"dm_{uuid.uuid4().hex[:8]}",
                            conversation_id=conversation_id,
                            sender_profile_id="child_profile",  # placeholder child ID
                            receiver_profile_id=active_profile.id,
                            text=new_msg.strip(),
                            created_at=datetime.utcnow(),
                            is_simulation=False,  # later: True for injected events
                            simulation_tag=None,
                        )
                        st.session_state["dm_messages"].append(msg)
                        st.experimental_rerun()
                    else:
                        st.warning("Message is empty.")

            with col2:
                st.caption("Future: 'Trigger Simulation' button will inject scenario messages here.")

            st.info(
                "This DM view is the backbone for future simulations: "
                "we'll later inject scripted 'bad actor' or 'teachable' messages "
                "from special simulation profiles and log the child's responses."
            )


if __name__ == "__main__":
    main()
