# models.py

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class Interest:
    """
    Represents a topic the child is interested in, with a weight indicating
    how frequently it should appear in the feed.
    """
    topic: str
    weight: float


@dataclass
class ChildConfig:
    """
    Configuration describing the child and the current session settings.
    """
    name: str
    age: int
    interests: List[Interest]
    mode: str  # "realistic" or "gamified"
    max_posts: int = 8


@dataclass
class Profile:
    """
    A unified representation of any profile in the system: child, parent,
    real friend, or synthetic persona.

    For now we mostly use synthetic profiles in the feed, but this structure
    will also support:
      - Parent profile
      - Child profile
      - Real-life friend profiles
    and simulation actors later.
    """
    id: str
    role: str  # "child" | "parent" | "friend" | "synthetic"
    display_name: str
    avatar_style: str  # "cartoony" | "realistic" | "system"
    personality_tags: List[str]
    topics: List[str]
    is_parent_controlled: bool = False  # True for parent-designed personas
    avatar_hue_shift: float = 0.0  # value in [0.0, 1.0), used to tint the base avatar


@dataclass
class Post:
    """
    A single post visible in the child's feed.
    """
    id: str
    author_profile_id: str
    author_name: str
    text: str
    topic: str
    mode: str  # "realistic" or "gamified"


@dataclass
class DMMessage:
    """
    A single direct message between the child and a profile.
    This will be used for both:
      - normal DM-style interactions
      - simulation events (when is_simulation = True).
    """
    id: str
    conversation_id: str
    sender_profile_id: str
    receiver_profile_id: str
    text: str
    created_at: datetime
    is_simulation: bool = False
    simulation_tag: Optional[str] = None  # e.g., "stranger_asks_address"
