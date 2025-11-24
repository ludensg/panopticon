# avatar_utils.py

import os
from functools import lru_cache

import numpy as np
from PIL import Image
import colorsys

from models import Profile

BASE_AVATAR_PATH = "assets/default_avatar.png"


@lru_cache(maxsize=1)
def load_base_avatar() -> Image.Image:
    """
    Load the base avatar image once and cache it.
    """
    if not os.path.exists(BASE_AVATAR_PATH):
        raise FileNotFoundError(
            f"Base avatar image not found at {BASE_AVATAR_PATH}. "
            f"Make sure assets/default_avatar.png exists."
        )
    img = Image.open(BASE_AVATAR_PATH).convert("RGBA")
    return img


def tint_avatar(base: Image.Image, hue_shift: float) -> Image.Image:
    """
    Apply a hue shift to the base avatar.
    hue_shift is in [0.0, 1.0) representing a full 0–360° rotation.
    """
    # Convert to numpy array
    arr = np.array(base).astype("float32")

    # Separate channels
    r, g, b, a = np.rollaxis(arr, axis=-1)
    r /= 255.0
    g /= 255.0
    b /= 255.0

    # Convert each pixel from RGB to HSV, shift hue, convert back
    h, s, v = np.vectorize(colorsys.rgb_to_hsv)(r, g, b)
    h = (h + hue_shift) % 1.0
    r2, g2, b2 = np.vectorize(colorsys.hsv_to_rgb)(h, s, v)

    r2 = (r2 * 255).astype("uint8")
    g2 = (g2 * 255).astype("uint8")
    b2 = (b2 * 255).astype("uint8")

    rgba = np.stack([r2, g2, b2, a.astype("uint8")], axis=-1)

    tinted = Image.fromarray(rgba, mode="RGBA")
    return tinted


def get_avatar_for_profile(profile: Profile) -> Image.Image:
    """
    Returns a tinted avatar image for a given profile.
    For now, all synthetic profiles share the same base avatar,
    but with different hue shifts.
    """
    base = load_base_avatar()

    # If in the future you want different logic per role:
    # if profile.role == "parent": return base (no tint), etc.
    hue = profile.avatar_hue_shift or 0.0
    return tint_avatar(base, hue)
