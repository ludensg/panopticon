# feed_generator.py

from __future__ import annotations

import random
from typing import List

from models import (
    ChildState,
    GardenState,
    Post,
    make_id,
)
from prompts import REALISTIC_PROMPT, GAMIFIED_PROMPT
from llm_client import call_llm


def sanitize_post_text(text: str, max_len: int = 280) -> str:
    """Simple cleanup for LLM outputs."""
    if not text:
        return ""
    t = text.strip()
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()
    t = " ".join(line.strip() for line in t.splitlines() if line.strip())
    if len(t) > max_len:
        t = t[: max_len - 1].rstrip() + "…"
    return t


def _sample_topics(child: ChildState) -> List[str]:
    interests = [i for i in child.config.interests if i.weight > 0]
    if not interests:
        return ["general"] * child.config.max_posts

    max_posts = child.config.max_posts
    topics = [i.topic for i in interests]
    weights = [i.weight for i in interests]
    total = sum(weights) or 1.0
    probs = [w / total for w in weights]

    sampled: List[str] = []
    if max_posts >= len(interests):
        base_topics = [i.topic for i in interests]
        sampled.extend(base_topics)
        remaining = max_posts - len(base_topics)
        if remaining > 0:
            extra = random.choices(topics, weights=probs, k=remaining)
            sampled.extend(extra)
    else:
        sampled = random.choices(topics, weights=probs, k=max_posts)

    random.shuffle(sampled)
    return sampled


def _find_or_create_profile_for_topic(
    garden: GardenState,
    topic: str,
    mode: str,
) -> "Profile":
    from models import Profile  # local import to avoid circular issues

    for p in garden.profiles:
        if p.role == "synthetic" and topic in p.topics:
            return p

    display_name = random.choice(
        ["SkyKid", "StarGazer", "PixelPal", "DinoBuddy", "ArtHero", "CloudRider"]
    ) + str(random.randint(1, 999))

    personality_pool = [
        "curious",
        "shy",
        "outgoing",
        "creative",
        "thoughtful",
        "funny",
        "adventurous",
    ]
    personality_tags = random.sample(personality_pool, k=2)

    hue_shift = random.random()
    avatar_style = "cartoony" if mode == "gamified" else "realistic"

    profile = Profile(
        id=make_id("profile"),
        role="synthetic",
        display_name=display_name,
        avatar_style=avatar_style,
        personality_tags=personality_tags,
        topics=[topic],
        is_parent_controlled=False,
        avatar_hue_shift=hue_shift,
    )
    garden.profiles.append(profile)
    return profile


def generate_feed_for_child(
    garden: GardenState,
    child: ChildState,
    backend: str = "openai",
    model_name: str | None = None,
) -> List[Post]:
    """
    Generate a feed for a specific child within a garden, using the chosen backend + model.
    Updates child.posts and returns the new posts.
    """
    topics = _sample_topics(child)
    posts: List[Post] = []

    child_interests_str = ", ".join(i.topic for i in child.config.interests)

    for topic in topics:
        author_profile = _find_or_create_profile_for_topic(garden, topic, child.config.mode)

        base_prompt = REALISTIC_PROMPT if child.config.mode == "realistic" else GAMIFIED_PROMPT
        prompt = base_prompt.format(
            child_age=child.config.age,
            topic=topic,
            personality_tags=", ".join(author_profile.personality_tags),
            author_name=author_profile.display_name,
            child_interests=child_interests_str,
        )

        try:
            raw = call_llm(prompt, backend=backend, model=model_name)
        except Exception as e:
            raw = f"(LLM error: {e}) This is a placeholder post about {topic}."

        text = sanitize_post_text(raw)

        post = Post(
            id=make_id("post"),
            child_id=child.id,
            author_profile_id=author_profile.id,
            author_name=author_profile.display_name,
            text=text,
            topic=topic,
            mode=child.config.mode,
        )
        posts.append(post)

    child.posts = posts
    return posts
