# avatar_utils.py

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw
from models import Profile

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------

ASSETS_DIR = Path(__file__).parent / "assets"
DEFAULT_AVATAR_PATH = ASSETS_DIR / "default_avatar.png"

# Cached base avatar to avoid reloading from disk repeatedly
_BASE_AVATAR: Optional[Image.Image] = None


# ---------------------------------------------------------------------------
# Base avatar loading
# ---------------------------------------------------------------------------

def load_base_avatar() -> Image.Image:
    """
    Load the default avatar image as RGBA.

    If the default avatar file is missing, returns a simple placeholder image.
    This function is safe to call multiple times; it uses an in-memory cache.
    """
    global _BASE_AVATAR

    if _BASE_AVATAR is not None:
        return _BASE_AVATAR

    if not DEFAULT_AVATAR_PATH.exists():
        # Fallback: flat gray placeholder
        img = Image.new("RGBA", (256, 256), color=(200, 200, 200, 255))
        _BASE_AVATAR = img
        return img

    img = Image.open(DEFAULT_AVATAR_PATH).convert("RGBA")
    _BASE_AVATAR = img
    return img


# ---------------------------------------------------------------------------
# Hue-shift tinting
# ---------------------------------------------------------------------------

def tint_avatar(hue_shift: float, base_avatar: Optional[Image.Image] = None) -> Image.Image:
    """
    Apply an HSV hue shift in [0.0, 1.0] to the base avatar and return a new PIL Image.

    The alpha channel (if present) is preserved.
    """
    if base_avatar is None:
        base_avatar = load_base_avatar()

    # Separate out alpha (if any) so we don't mess with it during RGB HSV math.
    base_avatar = base_avatar.convert("RGBA")
    rgb_img = base_avatar.convert("RGB")
    alpha = base_avatar.split()[-1]  # last channel is alpha

    # Convert to float RGB array
    arr = np.array(rgb_img).astype("float32") / 255.0
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]

    cmax = np.max(arr, axis=-1)
    cmin = np.min(arr, axis=-1)
    delta = cmax - cmin + 1e-8

    # Hue
    h = np.zeros_like(cmax)
    mask = delta != 0
    r_eq = (cmax == r) & mask
    g_eq = (cmax == g) & mask
    b_eq = (cmax == b) & mask

    h[r_eq] = ((g[r_eq] - b[r_eq]) / delta[r_eq]) % 6
    h[g_eq] = ((b[g_eq] - r[g_eq]) / delta[g_eq]) + 2
    h[b_eq] = ((r[b_eq] - g[b_eq]) / delta[b_eq]) + 4
    h = h / 6.0  # to [0,1]

    # Saturation and Value
    s = delta / (cmax + 1e-8)
    v = cmax

    # Apply hue shift
    h = (h + hue_shift) % 1.0

    # Convert HSV back to RGB
    h6 = h * 6.0
    i = np.floor(h6).astype(int)
    f = h6 - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)

    r2 = np.zeros_like(v)
    g2 = np.zeros_like(v)
    b2 = np.zeros_like(v)

    i_mod = i % 6
    mask0 = i_mod == 0
    mask1 = i_mod == 1
    mask2 = i_mod == 2
    mask3 = i_mod == 3
    mask4 = i_mod == 4
    mask5 = i_mod == 5

    r2[mask0], g2[mask0], b2[mask0] = v[mask0], t[mask0], p[mask0]
    r2[mask1], g2[mask1], b2[mask1] = q[mask1], v[mask1], p[mask1]
    r2[mask2], g2[mask2], b2[mask2] = p[mask2], v[mask2], t[mask2]
    r2[mask3], g2[mask3], b2[mask3] = p[mask3], q[mask3], v[mask3]
    r2[mask4], g2[mask4], b2[mask4] = t[mask4], p[mask4], v[mask4]
    r2[mask5], g2[mask5], b2[mask5] = v[mask5], p[mask5], q[mask5]

    out = np.stack([r2, g2, b2], axis=-1)
    out = (np.clip(out, 0.0, 1.0) * 255).astype("uint8")

    rgb_out = Image.fromarray(out, mode="RGB")
    # Reattach alpha
    rgba_out = Image.merge("RGBA", (*rgb_out.split(), alpha))
    return rgba_out


# ---------------------------------------------------------------------------
# Profile-aware helpers
# ---------------------------------------------------------------------------

def get_tinted_avatar_for_profile(profile: Profile) -> Image.Image:
    """
    Return a tinted avatar image for the given profile, using its avatar_hue_shift
    if present, or 0.0 as a default.
    """
    hue_shift = getattr(profile, "avatar_hue_shift", 0.0) or 0.0
    base = load_base_avatar()
    return tint_avatar(hue_shift=hue_shift, base_avatar=base)


def make_circular(image: Image.Image, size: int = 64) -> Image.Image:
    """
    Resize an image to a square of the given size and apply a circular alpha mask,
    returning a circular RGBA avatar.
    """
    image = image.convert("RGBA")
    # Center-crop to square then resize
    w, h = image.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    image = image.crop((left, top, left + side, top + side))
    image = image.resize((size, size), Image.LANCZOS)

    # Circular mask
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)

    circular = Image.new("RGBA", (size, size))
    circular.paste(image, (0, 0), mask)
    return circular


def get_circular_avatar_for_profile(profile: Profile, size: int = 40) -> Image.Image:
    """
    Return a small, circular avatar image for use in the UI (e.g., in the feed).

    Usage in Streamlit:
        avatar_img = get_circular_avatar_for_profile(profile, size=40)
        st.image(avatar_img, width=40)
    """
    tinted = get_tinted_avatar_for_profile(profile)
    return make_circular(tinted, size=size)
