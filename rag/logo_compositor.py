"""
Logo compositor: finds the brand logo file and composites it onto a generated flyer.

Approach
--------
gpt-image-1 generates the base flyer (returned as b64 PNG).
Pillow then loads the logo from brand_assets/logo/<brand_id>.*  (or the
fallback default logo), resizes it to fit the configured area, and pastes
it with full alpha-channel support.

Logo placement per platform:
  - Instagram Feed / LinkedIn Post  → bottom-right corner
  - Instagram Story                 → top-center
  - LinkedIn Banner                 → left-center (brand anchor position)

The logo file must be PNG or SVG (SVG requires cairosvg; PNG is preferred).
"""
from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Literal

from PIL import Image
import structlog

logger = structlog.get_logger().bind(component="LogoCompositor")

_LOGO_DIR = Path("brand_assets/logo")
_LOGO_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")

# Logo occupies this fraction of the shorter flyer dimension
_LOGO_SCALE = 0.32
# Padding from edges in pixels (at 1080px reference)
_PADDING_REF = 40
_REF_SIZE = 1080

Placement = Literal["bottom_right", "bottom_left", "top_center", "left_center", "bottom_center"]

_PLATFORM_PLACEMENT: dict[str, Placement] = {
    "instagram_feed": "bottom_center",
    "instagram_story": "top_center",
    "linkedin_post": "bottom_center",
    "linkedin_banner": "left_center",
}


def find_logo(brand_id: str) -> Path | None:
    """
    Look for a logo file in priority order:
      1. brand_assets/logo/<brand_id>.<ext>
      2. brand_assets/logo/default.<ext>
      3. Any image file in brand_assets/logo/ (first match)
    Returns None if nothing is found.
    """
    for stem in (brand_id, "default"):
        for ext in _LOGO_EXTENSIONS:
            candidate = _LOGO_DIR / f"{stem}{ext}"
            if candidate.exists():
                return candidate
    # Fallback: pick any logo file present in the directory
    if _LOGO_DIR.exists():
        for ext in _LOGO_EXTENSIONS:
            matches = sorted(_LOGO_DIR.glob(f"*{ext}"))
            if matches:
                return matches[0]
    return None


def composite_logo(
    flyer_b64: str,
    brand_id: str,
    platform_key: str,
    logo_scale: float = _LOGO_SCALE,
) -> str:
    """
    Paste the brand logo onto the flyer image.

    Parameters
    ----------
    flyer_b64   : base64-encoded PNG/JPEG of the generated flyer
    brand_id    : used to locate the correct logo file
    platform_key: e.g. "instagram_feed" — determines logo placement
    logo_scale  : logo width as a fraction of the shorter flyer dimension

    Returns
    -------
    base64-encoded PNG with logo composited in.
    If no logo file is found the original flyer_b64 is returned unchanged.
    """
    logo_path = find_logo(brand_id)
    if logo_path is None:
        logger.warning("logo_not_found", brand_id=brand_id)
        return flyer_b64

    # --- Load flyer ---
    flyer_bytes = base64.b64decode(flyer_b64)
    flyer = Image.open(io.BytesIO(flyer_bytes)).convert("RGBA")
    fw, fh = flyer.size

    # --- Load & prepare logo ---
    logo = Image.open(logo_path).convert("RGBA")
    logo = _resize_logo(logo, fw, fh, logo_scale)
    lw, lh = logo.size

    # --- Compute position ---
    padding = _scale_padding(min(fw, fh))
    placement: Placement = _PLATFORM_PLACEMENT.get(platform_key, "bottom_right")
    x, y = _compute_position(fw, fh, lw, lh, padding, placement)

    # --- Composite ---
    canvas = flyer.copy()
    canvas.paste(logo, (x, y), mask=logo)

    # --- Encode back to b64 PNG ---
    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="PNG", optimize=True)
    result_b64 = base64.b64encode(buf.getvalue()).decode()

    logger.info(
        "logo_composited",
        brand_id=brand_id,
        platform=platform_key,
        placement=placement,
        logo_size=f"{lw}x{lh}",
        position=f"({x},{y})",
    )
    return result_b64


def _resize_logo(logo: Image.Image, fw: int, fh: int, scale: float) -> Image.Image:
    """Resize logo so its width equals scale × shorter flyer dimension."""
    target_w = int(min(fw, fh) * scale)
    ratio = target_w / logo.width
    target_h = int(logo.height * ratio)
    return logo.resize((target_w, target_h), Image.LANCZOS)


def _scale_padding(shorter_side: int) -> int:
    return int(_PADDING_REF * shorter_side / _REF_SIZE)


def _compute_position(
    fw: int, fh: int, lw: int, lh: int, padding: int, placement: Placement
) -> tuple[int, int]:
    positions: dict[Placement, tuple[int, int]] = {
        "bottom_right": (fw - lw - padding, fh - lh - padding),
        "bottom_left":  (padding, fh - lh - padding),
        "bottom_center": ((fw - lw) // 2, fh - lh - padding),
        "top_center":   ((fw - lw) // 2, padding),
        "left_center":  (padding, (fh - lh) // 2),
    }
    return positions[placement]
