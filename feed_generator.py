# feed_generator.py

from __future__ import annotations

import random
from typing import List

from datetime import datetime
from urllib.parse import quote_plus

from image_search import search_image_for_topic

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

    max_posts = get_effective_max_posts(child)
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

def get_effective_max_posts(child: ChildState) -> int:
    """
    Decide how many posts to show based on time of day and child's config.
    Simple version:
    - Quiet hours: use max_posts_quiet if set, else max_posts.
    - Normal hours: use max_posts.
    Quiet hours are 08:00–15:00 and 21:00–07:00 (tweak as needed).
    """
    base = child.config.max_posts
    quiet = child.config.max_posts_quiet or base

    hour = datetime.now().hour  # server local time
    # Example quiet windows: school-ish & late night
    in_quiet = (8 <= hour < 15) or (21 <= hour or hour < 7)
    return quiet if in_quiet else base


def get_image_url_for_topic(topic: str) -> str:
    """
    Very simple web image strategy:
    Use Unsplash's source endpoint to get a random featured image by topic.
    This avoids needing an API key and is fine for a prototype.
    """
    q = quote_plus(topic)
    return f"https://source.unsplash.com/featured/?{q}"



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

        # Decide whether this post should be "news-like" or "personal update"
        if random.random() < child.config.news_ratio:
            post_flavor = "kid-friendly news"
        else:
            post_flavor = "personal update"

        base_prompt = REALISTIC_PROMPT if child.config.mode == "realistic" else GAMIFIED_PROMPT
        prompt = base_prompt.format(
            child_age=child.config.age,
            topic=topic,
            personality_tags=", ".join(author_profile.personality_tags),
            author_name=author_profile.display_name,
            child_interests=child_interests_str,
            post_flavor=post_flavor,
        )

        try:
            raw = call_llm(prompt, backend=backend, model=model_name)
        except Exception as e:
            raw = f"(LLM error: {e}) This is a placeholder post about {topic}."

        text = sanitize_post_text(raw)

        # Decide if this post should include an image
        image_url = None
        if random.random() < child.config.image_ratio:
            # Try to fetch a kid-safe image URL from Pixabay
            image_url = search_image_for_topic(topic)

        post = Post(
            id=make_id("post"),
            child_id=child.id,
            author_profile_id=author_profile.id,
            author_name=author_profile.display_name,
            text=text,
            topic=topic,
            mode=child.config.mode,
            image_url=image_url,
        )

        posts.append(post)

    child.posts = posts
    return posts

