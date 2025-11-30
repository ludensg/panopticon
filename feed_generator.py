# feed_generator.py

from __future__ import annotations

import random
from typing import List

from datetime import datetime
from urllib.parse import quote_plus

from image_search import search_image_for_topic
from news_fetcher import get_child_news_for_topic, NewsItem
from username_utils import generate_username


from models import (
    ChildState,
    GardenState,
    Post,
    make_id,
)
from prompts import REALISTIC_PROMPT, GAMIFIED_PROMPT
from llm_client import call_llm

import re


def choose_sub_flavor(post_flavor: str) -> str:
    """
    Pick a more granular sub-flavor for the post.

    This is used by the prompt templates as {sub_flavor} and can be things like:
    - personal_story
    - how_to_tip
    - cool_fact
    - mini_report
    """
    if "news" in post_flavor.lower():
        # News-like posts
        return random.choice(["cool_fact", "mini_report", "today_i_learned"])
    else:
        # Personal-style posts
        return random.choice(["personal_story", "how_to_tip", "reflection"])


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



def _find_or_create_profile_for_topic(garden: GardenState, topic: str, mode: str) -> Profile:
    # Try to reuse an existing synthetic profile that already lists this topic
    for p in garden.profiles:
        if p.role == "synthetic" and topic in p.topics:
            return p

    # Else create a new one
    from models import Profile, make_id

    # Collect existing display names to avoid duplicates
    existing_names = [p.display_name for p in garden.profiles]

    display_name = generate_username(
        mode=mode,
        topics=[topic],
        existing_names=existing_names,
    )

    profile = Profile(
        id=make_id("profile"),
        role="synthetic",
        display_name=display_name,
        avatar_style="cartoony" if mode == "gamified" else "realistic",
        personality_tags=["curious", "friendly"],
        topics=[topic],
        is_parent_controlled=False,
        avatar_hue_shift=random.random(),
    )
    garden.profiles.append(profile)
    return profile

STOPWORDS = {
    "the", "a", "an", "and", "or", "but",
    "to", "for", "in", "on", "at", "of",
    "is", "are", "was", "were", "be", "been", "being",
    "i", "you", "he", "she", "they", "we", "it",
    "this", "that", "these", "those",
    "my", "your", "his", "her", "their", "our",
    "with", "about", "from", "as", "by",
}


def build_image_query(topic: str, text: str, max_terms: int = 4) -> str:
    """
    Build a more specific image search query from the topic + post text.

    - Extracts non-stopword tokens from the text.
    - Prefers longer tokens (length >= 4).
    - Combines up to `max_terms` of them with the topic.
    """
    # Extract word-like tokens from text (keep numbers too)
    tokens = re.findall(r"[A-Za-z0-9]+", text or "")
    # Filter & normalize
    candidates = []
    for t in tokens:
        low = t.lower()
        if low in STOPWORDS:
            continue
        if len(low) < 4:
            continue
        candidates.append(low)

    # De-duplicate preserving order
    seen = set()
    filtered = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            filtered.append(c)

    key_terms = filtered[:max_terms]
    if key_terms:
        return f"{topic} " + " ".join(key_terms)
    else:
        return topic


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
    adaptive_context = build_adaptive_context(child)


    child_interests_str = ", ".join(i.topic for i in child.config.interests)

    for topic in topics:
        author_profile = _find_or_create_profile_for_topic(garden, topic, child.config.mode)

        # Decide whether this post should be "news-like" or "personal update"
        if random.random() < child.config.news_ratio:
            post_flavor = "kid-friendly news"
        else:
            post_flavor = "personal update"

        sub_flavor = choose_sub_flavor(post_flavor)

        # --- NEW: world news integration for "kid-friendly news" ---
        news_item: NewsItem | None = None
        if "news" in post_flavor.lower():
            news_item = get_child_news_for_topic(topic)

        if news_item:
            news_context = (
                f"This post should be loosely based on the following real-world article, "
                f"rewritten in a child-friendly, positive way:\n\n"
                f"- Title: {news_item.title}\n"
                f"- Description: {news_item.description}\n"
                f"- Source: {news_item.source_name}\n"
            )
        else:
            # Fallback: let the model invent a plausible, positive recent development.
            news_context = (
                "No specific article is available. Invent a plausible, positive, "
                "recent development related to the topic that would be interesting "
                "for a child, avoiding scary or graphic details."
            )

        base_prompt = REALISTIC_PROMPT if child.config.mode == "realistic" else GAMIFIED_PROMPT
        prompt = base_prompt.format(
            adaptive_context=adaptive_context,
            child_age=child.config.age,
            topic=topic,
            personality_tags=", ".join(author_profile.personality_tags),
            author_name=author_profile.display_name,
            child_interests=child_interests_str,
            post_flavor=post_flavor,
            sub_flavor=sub_flavor,
            news_context=news_context,
        )

        try:
            raw = call_llm(prompt, backend=backend, model=model_name)
        except Exception as e:
            raw = f"(LLM error: {e}) This is a placeholder post about {topic}."

        text = sanitize_post_text(raw)

        # --- Smarter image query ---
        image_url = None
        if random.random() < child.config.image_ratio:
            # If we have a news article, use its text as the basis;
            # otherwise, use the generated post text.
            if news_item:
                image_text = f"{news_item.title} {news_item.description or ''}"
            else:
                image_text = text

            query = build_image_query(topic, image_text)
            image_url = search_image_for_topic(query)

        now = datetime.utcnow()
        post = Post(
            id=make_id("post"),
            child_id=child.id,
            author_profile_id=author_profile.id,
            author_name=author_profile.display_name,
            text=text,
            topic=topic,
            mode=child.config.mode,
            image_url=image_url,
            created_at=now,
        )

        posts.append(post)

    # Prepend new posts, newest first
    if child.posts:
        child.posts = posts + child.posts
    else:
        child.posts = posts

    return child.posts


def build_adaptive_context(child: ChildState) -> str:
        sp = child.skill_profile
        return f"""
    Child skill model (0.0 = weaker, 1.0 = stronger):

    - Boundary-setting: {sp.boundary_setting:.2f}
    - Information safety: {sp.info_sharing_safety:.2f}
    - Peer pressure resistance: {sp.peer_pressure_resistance:.2f}
    - Emotional clarity: {sp.emotional_clarity:.2f}
    - Curiosity: {sp.curiosity:.2f}

    Content goals:
    - Subtly model behavior that strengthens areas where the child's score is lower.
    - Show characters who set healthy boundaries and avoid oversharing.
    - Encourage curiosity and critical thinking without fear or shame.
    - Keep everything age-appropriate and emotionally supportive.
    """.strip()
