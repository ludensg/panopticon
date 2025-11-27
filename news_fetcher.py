# news_fetcher.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import os
import random

import requests


NEWS_API_KEY = os.environ.get("NEWS_API_KEY")


@dataclass
class NewsItem:
    title: str
    description: str
    url: str
    source_name: str


# Very simple word-based content filter.
# This is only a coarse safety layer; the LLM still rewrites everything
# in a kid-friendly way on top.
BANNED_TOKENS = {
    "shooting",
    "killed",
    "murder",
    "war",
    "attack",
    "abuse",
    "assault",
    "bomb",
    "terror",
    "rape",
    "suicide",
    "hostage",
}


def _looks_unsuitable(text: str) -> bool:
    low = (text or "").lower()
    return any(tok in low for tok in BANNED_TOKENS)


def _pick_category_for_topic(topic: str) -> Optional[str]:
    """
    Roughly map our topic label to a NewsAPI 'category' for fallback.
    Categories allowed by NewsAPI include:
      - business, entertainment, general, health, science, sports, technology
    """
    t = (topic or "").lower()
    if any(k in t for k in ["space", "planet", "nasa", "astronomy"]):
        return "science"
    if any(k in t for k in ["game", "gaming", "console", "playstation", "xbox", "nintendo"]):
        return "technology"
    if any(k in t for k in ["robot", "ai", "coding", "computer"]):
        return "technology"
    if any(k in t for k in ["animal", "nature", "environment", "climate"]):
        return "science"
    if any(k in t for k in ["health", "medicine", "fitness"]):
        return "health"
    # Fallback: general science-ish stuff
    return "science"


def get_child_news_for_topic(topic: str, max_items: int = 10) -> Optional[NewsItem]:
    """
    Fetch a single news article that could be interesting for children,
    roughly related to `topic`.

    Uses NewsAPI.org's /v2/everything for topic-based search, and falls back
    to /v2/top-headlines for a generic science/technology/etc headline.

    You must set NEWS_API_KEY in your environment.
      export NEWS_API_KEY="your_key_here"

    Returns:
        NewsItem or None if no suitable article is found.
    """
    if not NEWS_API_KEY:
        return None

    # 1) Try /v2/everything for topic-specific search
    base_query = (topic or "").strip()
    if not base_query:
        base_query = "science OR space OR animals OR environment OR education"

    try:
        everything_resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": base_query,
                "language": "en",
                "pageSize": max_items,
                "sortBy": "publishedAt",
                "apiKey": NEWS_API_KEY,
            },
            timeout=5,
        )
    except Exception:
        everything_resp = None

    candidate_articles = []
    if everything_resp is not None and everything_resp.status_code == 200:
        data = everything_resp.json()
        articles = data.get("articles") or []
        for art in articles:
            title = (art.get("title") or "").strip()
            description = (art.get("description") or "").strip()
            combined = f"{title} {description}"
            if not title:
                continue
            if _looks_unsuitable(combined):
                continue
            candidate_articles.append(art)

    # 2) If we have suitable topic-specific articles, pick one and return
    if candidate_articles:
        art = random.choice(candidate_articles)
        title = art.get("title") or ""
        description = art.get("description") or ""
        url = art.get("url") or ""
        source = (art.get("source") or {}).get("name") or ""
        return NewsItem(
            title=title.strip(),
            description=description.strip(),
            url=url.strip(),
            source_name=source.strip(),
        )

    # 3) Fallback: /v2/top-headlines with a reasonable category
    category = _pick_category_for_topic(topic)
    try:
        top_resp = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={
                "country": "us",
                "category": category,
                "pageSize": max_items,
                "apiKey": NEWS_API_KEY,
            },
            timeout=5,
        )
    except Exception:
        return None

    if top_resp.status_code != 200:
        return None

    data = top_resp.json()
    articles = data.get("articles") or []
    if not articles:
        return None

    # Filter again for obviously unsuitable content
    safe_articles = []
    for art in articles:
        title = (art.get("title") or "").strip()
        description = (art.get("description") or "").strip()
        combined = f"{title} {description}"
        if not title:
            continue
        if _looks_unsuitable(combined):
            continue
        safe_articles.append(art)

    if not safe_articles:
        return None

    art = random.choice(safe_articles)
    title = art.get("title") or ""
    description = art.get("description") or ""
    url = art.get("url") or ""
    source = (art.get("source") or {}).get("name") or ""
    return NewsItem(
        title=title.strip(),
        description=description.strip(),
        url=url.strip(),
        source_name=source.strip(),
    )
