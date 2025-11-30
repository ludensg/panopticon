# username_utils.py

from __future__ import annotations

import random
from typing import Iterable, Optional


# Basic vocab for usernames – all kid-safe and neutral
ADJECTIVES = [
    "Bright", "Curious", "Calm", "Brave", "Kind",
    "Quiet", "Lucky", "Happy", "Swift", "Gentle",
    "Cozy", "Sunny", "Foggy", "Mellow", "Steady",
]

NEUTRAL_NOUNS = [
    "Sky", "River", "Forest", "Comet", "Star", "Planet", "Moon", "Cloud",
    "Pixel", "Echo", "Signal", "Circuit", "Trail", "Bridge", "Garden",
    "Story", "Quest", "Snow", "Breeze", "Spark",
]

GAMIFIED_NOUNS = [
    "Wizard", "Knight", "Ninja", "Dragon", "Robot",
    "Ranger", "Pilot", "Mage", "Explorer", "Captain",
    "Fox", "Panda", "Otter", "Wolf", "Phoenix",
]

# Topic stems – used when we know the main topic
TOPIC_STEMS = {
    "space": ["Galaxy", "Nova", "Orbit", "Astro", "Comet", "Starship"],
    "animals": ["Paws", "Feather", "Whisker", "Roamer", "Tracker"],
    "drawing": ["Sketch", "Doodle", "Canvas", "Ink", "Palette"],
    "science": ["Neuron", "Photon", "Atom", "PixelLab", "Vector"],
    "history": ["Chronicle", "Archive", "Scroll", "Relic"],
    "music": ["Melody", "Rhythm", "Chord", "EchoBeat"],
    "sports": ["Striker", "Runner", "Keeper", "Sprinter"],
}


def _topic_stem_for(topics: Iterable[str]) -> Optional[str]:
    """
    Pick a word stem based on one of the given topics, if any match our map.
    """
    topics = list(topics)
    random.shuffle(topics)

    for t in topics:
        key = t.lower()
        if key in TOPIC_STEMS:
            return random.choice(TOPIC_STEMS[key])
    return None


def _numeric_suffix() -> str:
    """
    Generate a realistic-ish numeric suffix: 2–4 digits.
    """
    # Bias toward 2–3 digits; occasionally 4
    roll = random.random()
    if roll < 0.6:
        return str(random.randint(10, 99))
    elif roll < 0.95:
        return str(random.randint(100, 999))
    else:
        return str(random.randint(1000, 9999))


def generate_username(
    *,
    mode: str = "realistic",
    topics: Optional[Iterable[str]] = None,
    existing_names: Optional[Iterable[str]] = None,
    max_tries: int = 20,
) -> str:
    """
    Generate a kid-friendly, semi-realistic username.

    - `mode` can be "realistic" or "gamified".
    - `topics` is a list of topic strings (e.g. interests or profile topics).
    - `existing_names`, if provided, will be used to avoid duplicates.

    Returns a display name like "CuriousComet42" or "GalaxyRanger_19".
    """
    topics = list(topics or [])
    existing = set(n.lower() for n in (existing_names or []))

    topic_stem = _topic_stem_for(topics)

    for _ in range(max_tries):
        base_parts = []

        # 1) Use topic stem if available, otherwise generic nouns
        if topic_stem:
            stem = topic_stem
        else:
            stem = random.choice(NEUTRAL_NOUNS)

        # 2) Adjective or second noun
        if random.random() < 0.6:
            adj = random.choice(ADJECTIVES)
            base_parts.append(adj)
            base_parts.append(stem)
        else:
            # Noun + noun combo
            noun2_pool = GAMIFIED_NOUNS if mode == "gamified" else NEUTRAL_NOUNS
            noun2 = random.choice(noun2_pool)
            base_parts.append(stem)
            base_parts.append(noun2)

        base = "".join(base_parts)

        # 3) Maybe add separator + numeric suffix
        username = base
        if random.random() < 0.85:
            sep = "" if random.random() < 0.7 else random.choice(["_", "."])
            username = f"{base}{sep}{_numeric_suffix()}"

        if username.lower() not in existing:
            return username

    # Fallback if we somehow exhausted attempts
    return f"{stem}{_numeric_suffix()}"
