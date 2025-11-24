# feed_generator.py

import random
from typing import List
import uuid

from models import ChildConfig, Profile, Post
from prompts import GAMIFIED_PROMPT, REALISTIC_PROMPT
from llm_client import call_llm

# Some simple personality options for auto-generated synthetic profiles.
PERSONALITY_POOL = [
    ["curious", "kind", "excitable"],
    ["creative", "thoughtful", "funny"],
    ["adventurous", "friendly", "imaginative"],
]

# Topic-based name prefixes for synthetic personas.
NAME_PREFIXES = {
    "space": ["Astro", "Nova", "Stellar", "Orbit"],
    "dinosaurs": ["Dino", "Rex", "Fossil"],
    "drawing": ["Sketch", "Doodle", "Canvas"],
    "music": ["Melody", "Rhythm", "Beat"],
    "animals": ["Paws", "Fluffy", "Wild"],
}


def generate_synthetic_profile(topic: str, mode: str) -> Profile:
    """
    Generate a synthetic profile tailored to a given topic and mode.
    These will be used both in feed posts and later in simulations/DMs.
    """
    personality = random.choice(PERSONALITY_POOL)
    style = "cartoony" if mode == "gamified" else "realistic"
    base = random.choice(NAME_PREFIXES.get(topic, ["Buddy", "Sunny", "Bright"]))

    profile_id = f"profile_{uuid.uuid4().hex[:8]}"

    return Profile(
        id=profile_id,
        role="synthetic",
        display_name=f"{base}{random.randint(1, 99)}",
        avatar_style=style,
        personality_tags=personality,
        topics=[topic],
        is_parent_controlled=False,
    )


def generate_feed(child: ChildConfig) -> (List[Post], List[Profile]):
    """
    Generate a list of posts and the synthetic profiles that authored them.

    Returns:
        posts: List[Post]
        profiles: List[Profile] used in this feed (to later support DMs/simulations).
    """
    if not child.interests:
        return [], []

    # 1. Sample topics based on interest weights.
    topics: List[str] = []
    weights = [i.weight for i in child.interests]
    names = [i.topic for i in child.interests]

    for _ in range(child.max_posts):
        topics.append(random.choices(names, weights=weights, k=1)[0])

    posts: List[Post] = []
    profiles: List[Profile] = []

    # To avoid duplicating profiles per post, we keep a memo:
    topic_to_profile: dict[str, Profile] = {}

    for topic in topics:
        if topic in topic_to_profile:
            profile = topic_to_profile[topic]
        else:
            profile = generate_synthetic_profile(topic, child.mode)
            topic_to_profile[topic] = profile
            profiles.append(profile)

        if child.mode == "gamified":
            prompt = GAMIFIED_PROMPT.format(
                child_age=child.age,
                topic=topic,
                profile_name=profile.display_name,
                personality_tags=", ".join(profile.personality_tags),
            )
        else:
            prompt = REALISTIC_PROMPT.format(
                child_age=child.age,
                topic=topic,
                profile_name=profile.display_name,
                personality_tags=", ".join(profile.personality_tags),
            )

        text = call_llm(prompt)

        post = Post(
            id=f"post_{uuid.uuid4().hex[:8]}",
            author_profile_id=profile.id,
            author_name=profile.display_name,
            text=text,
            topic=topic,
            mode=child.mode,
        )
        posts.append(post)

    return posts, profiles
