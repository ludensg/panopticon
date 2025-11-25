# avatar_utils.py

from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image


ASSETS_DIR = Path(__file__).parent / "assets"
DEFAULT_AVATAR_PATH = ASSETS_DIR / "default_avatar.png"


def load_base_avatar() -> Image.Image:
    if not DEFAULT_AVATAR_PATH.exists():
        # As a fallback, create a simple placeholder image.
        img = Image.new("RGB", (256, 256), color=(200, 200, 200))
        return img
    return Image.open(DEFAULT_AVATAR_PATH).convert("RGB")


def tint_avatar(hue_shift: float, base_avatar: Optional[Image.Image] = None) -> Image.Image:
    """
    Apply an HSV hue shift in [0.0, 1.0] to the base avatar.
    Returns a new PIL Image.
    """
    if base_avatar is None:
        base_avatar = load_base_avatar()

    img = base_avatar.convert("RGB")
    arr = np.array(img).astype("float32") / 255.0

    # Convert RGB to HSV
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

    return Image.fromarray(out)
