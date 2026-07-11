"""
Text compositor: draws the marketing copy (badge, headline, body, metric chip,
CTA button and trust line) onto the AI-generated background with Pillow.

Why this exists
---------------
gpt-image-1 renders text unreliably — wrong kerning, dropped accents, the
occasional invented number. The example brand images have pixel-perfect text.
So the AI now produces only an on-brand *background scene* (UI chrome, glows,
soft cards) with NO readable marketing text, and every word the viewer reads is
composited here at exact sizes, the exact brand palette and the brand font.

Highlight a word green by wrapping it in **double asterisks** in the headline.
"""
from __future__ import annotations

import base64
import io
import re
from typing import Literal

from PIL import Image, ImageDraw
import structlog

from core.brand import PALETTE, resolve_font

logger = structlog.get_logger().bind(component="TextCompositor")

Align = Literal["left", "center"]


# --------------------------------------------------------------------------- #
# Per-platform layout. All values are fractions of width/height so the same
# rules scale to any output size.
# --------------------------------------------------------------------------- #
_LAYOUTS: dict[str, dict] = {
    "instagram_feed":  {"align": "center", "col": (0.09, 0.91), "top": 0.10, "scale": 1.00},
    "instagram_story": {"align": "center", "col": (0.10, 0.90), "top": 0.16, "scale": 1.05},
    "linkedin_post":   {"align": "left",   "col": (0.06, 0.60), "top": 0.12, "scale": 0.78},
    "linkedin_banner": {"align": "left",   "col": (0.04, 0.66), "top": 0.16, "scale": 0.62},
}


def composite_text(base_b64: str, platform_key: str, copy: dict,
                   palette: dict | None = None) -> str:
    """
    Draw the campaign copy onto the base flyer.

    copy keys (all optional strings, except trust_items which is a list):
      badge, headline, body_copy, metric, call_to_action, trust_items

    palette: optional overrides for the drawing colors. Any of the keys in
      core.brand.PALETTE (e.g. "cta_green", "white", "light_gray", ...) may be
      supplied to recolor the text/pills/CTA. When None (the default used by the
      Bússola pipeline), the official brand palette is used unchanged. The direct
      image flow passes colors sampled from the user's reference image so the
      composited text matches it instead of forcing Bússola green.
    """
    pal = {**PALETTE, **(palette or {})}
    img = Image.open(io.BytesIO(base64.b64decode(base_b64))).convert("RGBA")
    W, H = img.size
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    layout = _LAYOUTS.get(platform_key, _LAYOUTS["instagram_feed"])
    align: Align = layout["align"]
    x0, x1 = int(W * layout["col"][0]), int(W * layout["col"][1])
    col_w = x1 - x0
    scale = layout["scale"]
    base = min(W, H)  # reference dimension for font sizing

    # Gentle top+bottom scrim so any AI background keeps text legible.
    _apply_scrim(img, top_strength=70, bottom_strength=130)

    y = int(H * layout["top"])
    cx = (x0 + x1) // 2

    def anchor_x() -> int:
        return cx if align == "center" else x0

    # --- Badge pill -------------------------------------------------------- #
    badge = (copy.get("badge") or "").strip()
    if badge:
        bf = resolve_font("body", int(base * 0.026 * scale))
        y = _draw_pill(
            draw, badge, bf, anchor_x(), y, align,
            text_color=pal["light_green"], bg=None,
            border=pal["light_green"], pad_x=int(base * 0.022),
            pad_y=int(base * 0.012),
        ) + int(base * 0.035)

    # --- Headline ---------------------------------------------------------- #
    headline = (copy.get("headline") or "").strip()
    if headline:
        hf = resolve_font("headline", int(base * 0.072 * scale))
        y = _draw_rich_paragraph(
            draw, headline, hf, x0, y, col_w, align,
            color=pal["white"], highlight=pal["cta_green"],
            line_spacing=1.08,
        ) + int(base * 0.028)

    # --- Body copy --------------------------------------------------------- #
    body = (copy.get("body_copy") or copy.get("subheadline") or "").strip()
    if body:
        bf = resolve_font("body", int(base * 0.030 * scale))
        y = _draw_rich_paragraph(
            draw, body, bf, x0, y, col_w, align,
            color=pal["light_gray"], highlight=pal["light_green"],
            line_spacing=1.2,
        ) + int(base * 0.030)

    # --- Metric chip (real product fact only) ------------------------------ #
    metric = (copy.get("metric") or "").strip()
    if metric:
        mf = resolve_font("mono", int(base * 0.030 * scale))
        y = _draw_pill(
            draw, metric, mf, anchor_x(), y, align,
            text_color=pal["cta_green"], bg=pal["secondary_bg"],
            border=pal["mid_green"], pad_x=int(base * 0.028),
            pad_y=int(base * 0.018),
        ) + int(base * 0.035)

    # --- CTA button -------------------------------------------------------- #
    cta = (copy.get("call_to_action") or "").strip()
    if cta:
        cf = resolve_font("headline", int(base * 0.034 * scale))
        y = _draw_cta(
            draw, f"{cta}  →", cf, anchor_x(), y, align,
            pad_x=int(base * 0.040), pad_y=int(base * 0.024), pal=pal,
        ) + int(base * 0.030)

    # --- Trust line (pinned near the bottom, above the logo zone) ---------- #
    trust = copy.get("trust_items") or []
    if trust:
        tf = resolve_font("body", int(base * 0.022 * scale))
        ty = int(H * (0.93 if platform_key == "instagram_story" else 0.90))
        _draw_trust_line(draw, list(trust), tf, x0, x1, ty, align, pal=pal)

    out = Image.alpha_composite(img, overlay).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    logger.info("text_composited", platform=platform_key, size=f"{W}x{H}")
    return base64.b64encode(buf.getvalue()).decode()


# --------------------------------------------------------------------------- #
# Drawing helpers
# --------------------------------------------------------------------------- #
def _apply_scrim(img: Image.Image, top_strength: int, bottom_strength: int) -> None:
    """Darken the top and bottom edges with a vertical gradient (in place)."""
    W, H = img.size
    grad = Image.new("L", (1, H), 0)
    for yy in range(H):
        t = yy / max(H - 1, 1)
        top = int(top_strength * max(0.0, 1 - t * 3))      # fades by ~1/3 height
        bot = int(bottom_strength * max(0.0, (t - 0.6) / 0.4))  # last 40%
        grad.putpixel((0, yy), min(255, top + bot))
    alpha = grad.resize((W, H))
    black = Image.new("RGBA", (W, H), (5, 20, 12, 0))
    black.putalpha(alpha)
    img.alpha_composite(black)


def _wrap(draw: ImageDraw.ImageDraw, words: list[tuple[str, bool]], font, max_w: int):
    """Greedy word-wrap. Each token is (text, is_highlight). Yields lines."""
    line: list[tuple[str, bool]] = []
    for tok in words:
        trial = line + [tok]
        text = " ".join(t for t, _ in trial)
        if draw.textlength(text, font=font) > max_w and line:
            yield line
            line = [tok]
        else:
            line = trial
    if line:
        yield line


def _parse_highlights(text: str) -> list[tuple[str, bool]]:
    """Split text into (word, highlighted) tokens using **markers**."""
    tokens: list[tuple[str, bool]] = []
    for chunk in re.split(r"(\*\*[^*]+\*\*)", text):
        if not chunk:
            continue
        hl = chunk.startswith("**") and chunk.endswith("**")
        words = (chunk[2:-2] if hl else chunk).split()
        tokens.extend((w, hl) for w in words)
    return tokens


def _draw_rich_paragraph(draw, text, font, x0, y, col_w, align, color, highlight,
                         line_spacing) -> int:
    """Word-wrap text and draw it, honoring **highlight** markers. Returns new y."""
    tokens = _parse_highlights(text)
    ascent, descent = font.getmetrics()
    line_h = int((ascent + descent) * line_spacing)
    space_w = draw.textlength(" ", font=font)

    for line in _wrap(draw, tokens, font, col_w):
        line_w = sum(draw.textlength(t, font=font) for t, _ in line) + space_w * (len(line) - 1)
        cx = x0 + (col_w - line_w) // 2 if align == "center" else x0
        for word, hl in line:
            draw.text((cx, y), word, font=font, fill=highlight if hl else color)
            cx += draw.textlength(word, font=font) + space_w
        y += line_h
    return y


def _text_size(draw, text, font) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def _rounded(draw, xy, radius, fill=None, outline=None, width=1) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _draw_pill(draw, text, font, anchor, y, align, text_color, bg, border,
               pad_x, pad_y) -> int:
    """Draw a pill (badge/metric chip). anchor is center-x or left-x. Returns bottom y."""
    tw, th = _text_size(draw, text, font)
    w, h = tw + pad_x * 2, th + pad_y * 2
    left = anchor - w // 2 if align == "center" else anchor
    box = (left, y, left + w, y + h)
    radius = h // 2
    fill = _rgba(bg, 235) if bg else None
    _rounded(draw, box, radius, fill=fill, outline=_rgb(border), width=max(2, h // 20))
    draw.text((left + pad_x, y + pad_y - 2), text, font=font, fill=_rgb(text_color))
    return y + h


def _draw_cta(draw, text, font, anchor, y, align, pad_x, pad_y, pal=PALETTE) -> int:
    """Solid CTA button with dark bold label. Returns bottom y."""
    tw, th = _text_size(draw, text, font)
    w, h = tw + pad_x * 2, th + pad_y * 2
    left = anchor - w // 2 if align == "center" else anchor
    box = (left, y, left + w, y + h)
    _rounded(draw, box, radius=h // 2, fill=_rgb(pal["cta_green"]))
    draw.text((left + pad_x, y + pad_y - 2), text, font=font, fill=_rgb(pal["near_black"]))
    return y + h


def _draw_trust_line(draw, items, font, x0, x1, y, align, pal=PALETTE) -> None:
    """Draw '✓ item   ✓ item   ✓ item' with a vector checkmark (font-agnostic)."""
    ascent, descent = font.getmetrics()
    line_h = ascent + descent
    check_w = int(line_h * 0.9)          # space reserved for each checkmark
    gap = int(line_h * 1.1)              # gap between items
    text_w = [draw.textlength(it, font=font) for it in items]
    total = sum(check_w + w for w in text_w) + gap * (len(items) - 1)
    cx = (x0 + x1 - total) // 2 if align == "center" else x0
    for it, w in zip(items, text_w):
        _draw_check(draw, cx, y, line_h, _rgb(pal["cta_green"]))
        draw.text((cx + check_w, y), it, font=font, fill=_rgb(pal["light_gray"]))
        cx += check_w + w + gap


def _draw_check(draw, x: int, y: int, size: int, color) -> None:
    """Draw a small checkmark glyph as two strokes within a size×size box."""
    w = max(2, size // 9)
    x1, y1 = x + size * 0.12, y + size * 0.52
    x2, y2 = x + size * 0.34, y + size * 0.74
    x3, y3 = x + size * 0.78, y + size * 0.26
    draw.line([(x1, y1), (x2, y2), (x3, y3)], fill=color, width=w, joint="curve")


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _rgba(hex_color: str, alpha: int) -> tuple[int, int, int, int]:
    return (*_rgb(hex_color), alpha)
