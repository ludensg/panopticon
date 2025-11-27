# image_search.py
"""
Lightweight, kid-safe image search for feed posts.

Uses the Pixabay API:
- https://pixabay.com/api/docs/
- Requires an API key in the PIXABAY_API_KEY environment variable.
- Uses safesearch=true to filter content to all-ages.
"""

from __future__ import annotations

import os
from typing import Optional

import requests


PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")


def search_image_for_topic(topic: str) -> Optional[str]:
    """
    Return a URL for a kid-safe image related to `topic`, or None on any error.

    We call Pixabay with:
    - safesearch=true  -> only images suitable for all ages
    - image_type=photo -> avoid vectors/illustrations for now
    - per_page=3       -> small, but gives a little variety
    - order=popular    -> higher quality content
    """
    if not PIXABAY_API_KEY:
        # No key configured; fail gracefully.
        return None

    try:
        resp = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": PIXABAY_API_KEY,
                "q": topic,
                "image_type": "photo",
                "safesearch": "true",
                "per_page": 3,
                "order": "popular",
            },
            timeout=5,
        )
    except Exception:
        return None

    if resp.status_code != 200:
        return None

    try:
        data = resp.json()
    except Exception:
        return None

    hits = data.get("hits") or []
    if not hits:
        return None

    # Take the first hit; you could randomize here if you want.
    hit = hits[0]

    # Prefer a reasonably-sized web image.
    url = (
        hit.get("webformatURL")
        or hit.get("largeImageURL")
        or hit.get("previewURL")
    )
    return url
