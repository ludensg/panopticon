# models.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Literal, Dict
import uuid


def make_id(prefix: str) -> str:
    """Generate a short unique ID with a prefix, for easier debugging."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ---------- Core config models ----------

@dataclass
class Interest:
    topic: str
    weight: float


ModeLiteral = Literal["realistic", "gamified"]


@dataclass
class ChildConfig:
    name: str
    age: int
    interests: List[Interest]
    mode: Literal["realistic", "gamified"]
    max_posts: int  # baseline max posts
    # Max posts allowed during quiet hours (e.g., school time / late night).
    # If None, defaults to max_posts.
    max_posts_quiet: Optional[int] = None
    # Fraction of posts (0.0–1.0) that should be in "kid-friendly news" style.
    news_ratio: float = 0.3
    # Fraction of posts (0.0–1.0) that should include a web image.
    image_ratio: float = 0.4


ProfileRole = Literal["child", "parent", "friend", "synthetic", "system"]
AvatarStyle = Literal["cartoony", "realistic", "system"]


@dataclass
class ChildSkillProfile:
    """
    Lightweight skill model per child.
    Values are in [0.0, 1.0] and get nudged by simulation evaluations.
    """
    boundary_setting: float = 0.5
    info_sharing_safety: float = 0.5
    emotional_clarity: float = 0.5
    peer_pressure_resistance: float = 0.5
    curiosity: float = 0.5


# ---------- Profile / Post / DM models ----------

@dataclass
class Profile:
    id: str
    role: ProfileRole
    display_name: str
    avatar_style: AvatarStyle
    personality_tags: List[str]
    topics: List[str]
    is_parent_controlled: bool = False
    avatar_hue_shift: float = 0.0  # 0.0–1.0

@dataclass
class Comment:
    id: str
    child_id: str            # which child wrote this comment
    post_id: str             # the post this comment belongs to
    author_profile_id: str   # profile of the author (child’s profile id)
    text: str
    created_at: datetime

@dataclass
class Post:
    id: str
    child_id: str
    author_profile_id: str
    author_name: str
    text: str
    topic: str
    mode: Literal["realistic", "gamified"]
    image_url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    # NEW: interaction from the child(ren)
    likes: List[str] = field(default_factory=list)        # list of child_ids who liked this
    comments: List[Comment] = field(default_factory=list) # comments on this post


@dataclass
class DMMessage:
    id: str
    child_id: str
    conversation_id: str
    sender_profile_id: str
    receiver_profile_id: str
    text: str
    created_at: datetime
    is_simulation: bool = False
    simulation_tag: Optional[str] = None

    def to_dict(self) -> Dict:
        """Helper for JSON serialization if needed later."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data

@dataclass
class SimulationEvent:
    """
    Represents a full simulation session for a given child + scenario + partner.
    It has:
    - An initial injected message from the partner (incoming_message_id),
    - The child's first reply (child_reply_message_id),
    - An eventual evaluation (outcome_label + evaluation_summary).
    """
    id: str
    child_id: str
    scenario_id: str
    partner_profile_id: str
    created_at: datetime
    incoming_message_id: str  # DMMessage.id of the first injected risky message
    child_reply_message_id: Optional[str] = None  # DMMessage.id of first reply
    outcome_label: Optional[str] = None  # "SAFE", "UNSAFE", "NEEDS_REVIEW"
    backend_used: Optional[str] = None
    model_used: Optional[str] = None
    is_active: bool = True
    evaluation_summary: Optional[str] = None  # short explanation for the parent




@dataclass
class SimulationScenario:
    """
    Static description of a simulation scenario type (library item).
    """
    id: str
    title: str
    description: str
    risk_type: str  # e.g. "privacy", "pressure", "bullying"
    recommended_age_min: int
    recommended_age_max: int
    # For future LLM use:
    system_prompt_template: str
    user_message_template: str
    # For now, a canned message we can inject without LLM:
    canned_message_template: str


# Forward declaration for type hints
@dataclass
class ChildState:
    id: str
    config: ChildConfig
    profile_id: str  # Profile used when sending messages as this child
    posts: List[Post] = field(default_factory=list)
    dm_messages: List[DMMessage] = field(default_factory=list)
    simulation_events: List[SimulationEvent] = field(default_factory=list)
    skill_profile: ChildSkillProfile = field(default_factory=ChildSkillProfile)

    # Convenience methods (kept minimal; garden knows about profiles)
    def summary(self) -> Dict:
        return {
            "name": self.config.name,
            "age": self.config.age,
            "mode": self.config.mode,
            "posts_count": len(self.posts),
            "dm_count": len(self.dm_messages),
            "simulation_events_count": len(self.simulation_events),
        }



@dataclass
class GardenState:
    id: str
    name: str
    children: Dict[str, ChildState] = field(default_factory=dict)
    profiles: List[Profile] = field(default_factory=list)

    # ---- Profile helpers ----

    def get_profile_by_id(self, profile_id: str) -> Optional[Profile]:
        return next((p for p in self.profiles if p.id == profile_id), None)

    def ensure_child_profile(self, child: ChildState) -> Profile:
        """
        Get or create the Profile corresponding to this child.
        Keeps all profiles in garden.profiles.
        """
        # If we already have a valid profile_id, return it
        if child.profile_id:
            existing = self.get_profile_by_id(child.profile_id)
            if existing is not None:
                return existing

        # Otherwise create a new profile for the child
        cfg = child.config
        profile = Profile(
            id=make_id("profile"),
            role="child",
            display_name=cfg.name,
            avatar_style="cartoony",
            personality_tags=["curious"],
            topics=[i.topic for i in cfg.interests],
            is_parent_controlled=True,
            avatar_hue_shift=0.0,
        )
        self.profiles.append(profile)
        child.profile_id = profile.id
        return profile

    # ---- Child helpers ----

    def get_child(self, child_id: str) -> Optional[ChildState]:
        return self.children.get(child_id)

    def add_child(self, config: ChildConfig) -> ChildState:
        """
        Create a new ChildState with its own Profile, add it to the garden, and return it.
        """
        child_id = make_id("child")
        # Temporary profile id; ensure_child_profile will fix if needed
        child = ChildState(
            id=child_id,
            config=config,
            profile_id="",  # will be created on demand
        )
        self.children[child_id] = child
        # Immediately ensure profile for convenience
        self.ensure_child_profile(child)
        return child

    def list_children(self) -> List[ChildState]:
        return list(self.children.values())
