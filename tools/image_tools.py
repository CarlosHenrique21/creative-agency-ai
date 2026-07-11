"""
ADK tool: generate a social media flyer.

Pipeline
--------
1. gpt-image-1 generates ONLY an on-brand background scene (UI chrome, glows,
   soft cards) — no readable marketing text, no numbers. When example brand
   images are present they are passed as visual references via images.edit so
   the output stays faithful to the real brand look.
2. Pillow composites the headline, body, metric chip, CTA and trust line on top
   (crisp text, exact palette, brand font) — see rag.text_compositor.
3. Pillow composites the brand logo — see rag.logo_compositor.
"""
from __future__ import annotations

import base64
import os
import uuid
from pathlib import Path

from google.adk.tools import ToolContext
from openai import OpenAI
from PIL import Image

from core.config import settings
from core.brand import PRODUCT_FACTS
from rag.logo_compositor import composite_logo, find_logo
from rag.text_compositor import composite_text

# Sync OpenAI client — ADK tools are called synchronously by the framework
_client = OpenAI(api_key=settings.openai_api_key)

_DIMENSIONS = {
    "instagram_feed": (1080, 1080),
    "instagram_story": (1080, 1920),
    "linkedin_post": (1200, 627),
    "linkedin_banner": (1584, 396),
}

_REFERENCE_DIR = Path("brand_assets/images")
_REFERENCE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
_MAX_REFERENCES = 3


def _size_from_ratio(ratio: float) -> str:
    if 0.9 <= ratio <= 1.1:
        return "1024x1024"
    return "1536x1024" if ratio > 1.1 else "1024x1536"


def _size_for(platform_key: str) -> tuple[int, int, str]:
    w, h = _DIMENSIONS.get(platform_key, (1080, 1080))
    return w, h, _size_from_ratio(w / h)


def _reference_images() -> list[Path]:
    if not settings.use_reference_images or not _REFERENCE_DIR.exists():
        return []
    files = sorted(
        f for f in _REFERENCE_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in _REFERENCE_EXT
    )
    return files[:_MAX_REFERENCES]


def _generate_background(prompt: str, size: str) -> str:
    """Return a b64 PNG background. Uses image references when available."""
    refs = _reference_images()
    if refs:
        handles = [open(p, "rb") for p in refs]
        try:
            resp = _client.images.edit(
                model=settings.image_model,
                image=handles,  # type: ignore[arg-type]
                prompt=prompt,
                n=1,
                size=size,  # type: ignore[arg-type]
            )
        finally:
            for h in handles:
                h.close()
    else:
        resp = _client.images.generate(
            model=settings.image_model,
            prompt=prompt,
            n=1,
            size=size,  # type: ignore[arg-type]
            quality=settings.image_quality,  # type: ignore[arg-type]
        )
    return resp.data[0].b64_json or ""


def generate_flyer_image(
    platform_key: str,
    image_prompt: str,
    headline: str,
    body_copy: str,
    badge: str,
    metric: str,
    call_to_action: str,
    trust_items: list[str],
    tool_context: ToolContext,
) -> dict:
    """
    Generate a flyer: AI background scene + Pillow-composited text + logo.

    Args:
        platform_key: e.g. "instagram_feed", "linkedin_post"
        image_prompt: English prompt for the BACKGROUND SCENE ONLY — describe
            the on-brand environment (UI chrome, glows, cards). Do NOT ask for
            the headline/CTA/trust text or any number: those are drawn by code.
        headline: headline text; wrap words in **double asterisks** to color
            them brand-green.
        body_copy: short supporting line (≤ 2 lines).
        badge: small pill text above the headline (e.g. "PLATAFORMA"); "" to skip.
        metric: the highlighted metric chip — MUST be a real product fact (e.g.
            "131 regras NCM"). Never a fabricated currency/revenue figure.
        call_to_action: CTA button label (an arrow is added automatically).
        trust_items: up to 3 short trust bullets for the bottom line.
        tool_context: ADK tool context (provides session state)

    Returns:
        dict with image_path (saved PNG file) and status message.
    """
    brand_id: str = tool_context.state.get("brand_id", "")
    w, h, size = _size_for(platform_key)

    # Guard against invented metrics: only keep a metric that maps to a real fact.
    metric = (metric or "").strip()
    if metric and not _is_real_fact(metric):
        metric = ""
        metric_note = "metric rejected (not a real product fact)"
    else:
        metric_note = "ok"

    full_prompt = (
        f"{image_prompt}\n\n"
        f"Render an empty, uncluttered BACKGROUND scene for a {w}x{h}px premium "
        f"dark-green SaaS/fintech social media flyer. "
        f"Do NOT render any headline, paragraph, button label, badge text, "
        f"checkmarks or numbers — all text is added later in post-processing. "
        f"Keep generous clean negative space in the center and bottom for text "
        f"overlay. High resolution, no watermark, no logo."
    )

    b64 = _generate_background(full_prompt, size)

    # Composite the marketing copy (crisp, on-brand text).
    copy = {
        "badge": badge,
        "headline": headline,
        "body_copy": body_copy,
        "metric": metric,
        "call_to_action": call_to_action,
        "trust_items": trust_items or [],
    }
    b64 = composite_text(b64, platform_key, copy)

    # Composite the brand logo.
    if brand_id:
        b64 = composite_logo(b64, brand_id, platform_key)
        logo_note = "logo composited" if find_logo(brand_id) else "no logo found"
    else:
        logo_note = "no brand_id — logo skipped"

    # Save to disk; keep only the path in state (base64 would flood the context).
    output_dir = os.path.abspath(settings.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{platform_key}_{uuid.uuid4().hex[:8]}.png"
    image_path = os.path.join(output_dir, filename)
    with open(image_path, "wb") as f:
        f.write(base64.b64decode(b64))

    flyers: dict = tool_context.state.get("flyers", {})
    if platform_key in flyers:
        flyers[platform_key]["image_path"] = image_path
        flyers[platform_key]["image_prompt"] = image_prompt
    tool_context.state["flyers"] = flyers

    return {
        "platform": platform_key,
        "image_path": image_path,
        "size": size,
        "used_references": bool(_reference_images()),
        "metric_status": metric_note,
        "logo_status": logo_note,
        "status": "success",
    }


def _is_real_fact(metric: str) -> bool:
    """Accept the metric only if it overlaps a known approved product fact."""
    m = metric.lower()
    return any(m in f.lower() or f.lower() in m for f in PRODUCT_FACTS)


def _luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (c / 255 for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def _palette_from_reference(path: Path) -> dict:
    """
    Sample the reference image and build a text palette that matches it, so the
    composited copy adopts the reference's colors instead of forcing Bússola green.

    Strategy: quantize to a few dominant colors; pick the most saturated/vivid one
    as the accent (CTA/highlight) and derive readable text/background tones from
    the overall brightness.
    """
    try:
        with Image.open(path) as im:
            small = im.convert("RGB").resize((80, 80))
        pal_img = small.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
        counts = pal_img.getcolors() or []
        palette_bytes = pal_img.getpalette() or []
        colors: list[tuple[int, tuple[int, int, int]]] = []
        for count, idx in counts:
            rgb = tuple(palette_bytes[idx * 3: idx * 3 + 3])  # type: ignore[assignment]
            if len(rgb) == 3:
                colors.append((count, rgb))  # type: ignore[arg-type]
        if not colors:
            return {}

        # Vividness = saturation-ish spread × how far from gray. Pick the punchiest
        # non-near-white / non-near-black color as the accent.
        def vividness(rgb: tuple[int, int, int]) -> float:
            mx, mn = max(rgb), min(rgb)
            sat = (mx - mn) / max(mx, 1)
            lum = _luminance(rgb)
            edge = 1.0 if 0.08 < lum < 0.92 else 0.2
            return sat * edge

        accent = max(colors, key=lambda c: vividness(c[1]))[1]
        # Dominant color (by pixel count) drives the background/chip tone.
        dominant = max(colors, key=lambda c: c[0])[1]
        dark = _luminance(dominant) < 0.5

        black = (10, 10, 12)
        white = (255, 255, 255)
        text = white if dark else (18, 18, 22)
        secondary = _mix(text, dominant, 0.55)

        # Ensure the highlight/accent reads against the background: if it's too
        # close in luminance to the dominant tone, push it toward the text color.
        if abs(_luminance(accent) - _luminance(dominant)) < 0.22:
            accent = _mix(accent, white if dark else black, 0.55)

        return {
            "cta_green": _hex(accent),
            "light_green": _hex(_mix(accent, white, 0.25)),
            "mid_green": _hex(_mix(accent, black, 0.25)),
            "secondary_bg": _hex(_mix(dominant, black if dark else white, 0.35)),
            "white": _hex(text),
            "light_gray": _hex(secondary),
            "near_black": _hex(black if _luminance(accent) > 0.55 else white),
        }
    except Exception:
        return {}


def generate_from_reference(
    reference_paths: list[str],
    platform_key: str,
    headline: str,
    body_copy: str = "",
    badge: str = "",
    metric: str = "",
    call_to_action: str = "",
    trust_items: list[str] | None = None,
    image_prompt: str = "",
    brand_id: str = "",
    apply_logo: bool = False,
    logo_path: str = "",
    match_reference_colors: bool = True,
) -> dict:
    """
    Generate a flyer from user-supplied REFERENCE image(s) + copy — the direct
    "GPT Image style" flow.

    The reference images are fed to gpt-image-1's edit endpoint to produce a
    BACKGROUND scene that faithfully mimics THEIR look (palette, lighting,
    composition) — NOT the Bússola brand. The copy (headline, body, metric chip,
    CTA, trust line) is then composited with colors sampled from the reference so
    the text matches it too. No RAG / no agents.

    Args:
        reference_paths: paths to the uploaded reference image(s) (PNG/JPG/WEBP).
        platform_key: e.g. "instagram_feed", "linkedin_post".
        headline, body_copy, badge, metric, call_to_action, trust_items: the copy
            to composite (typically produced by the content flow and edited by the user).
        image_prompt: optional extra direction for the background scene.
        brand_id: fallback logo lookup key (only used when apply_logo is True and
            no explicit logo_path is given).
        apply_logo: when True, composite a logo (off by default so the reference's
            identity is preserved).
        logo_path: explicit path to a logo file supplied by the user (e.g. an
            uploaded logo). Takes precedence over brand_id so the direct flow never
            picks up another brand's stored logo.
        match_reference_colors: when True (default), the composited text adopts
            colors sampled from the reference image.

    Returns:
        dict with image_path (saved PNG) and status.
    """
    refs = [Path(p) for p in reference_paths if p and Path(p).exists()]
    if not refs:
        return {"error": "no valid reference image provided", "status": "error"}

    w, h, size = _size_for(platform_key)

    # The direct flow follows the user's copy verbatim — no brand-specific
    # metric gating here (that lives in the Bússola pipeline only).
    metric = (metric or "").strip()
    metric_note = "ok"

    full_prompt = (
        f"{image_prompt}\n\n" if image_prompt else ""
    ) + (
        f"Recreate the visual style of the provided reference image(s) as an "
        f"empty, uncluttered BACKGROUND for a {w}x{h}px social media post. "
        f"Faithfully match THEIR exact color palette, lighting, mood, textures "
        f"and composition — do not shift the colors toward any other brand. "
        f"Do NOT render any headline, paragraph, button label, badge text, "
        f"checkmarks, logos or numbers — all text is added later in "
        f"post-processing. Keep generous clean negative space in the center and "
        f"bottom for text overlay. High resolution, no watermark."
    )

    handles = [open(p, "rb") for p in refs[:_MAX_REFERENCES]]
    try:
        resp = _client.images.edit(
            model=settings.image_model,
            image=handles,  # type: ignore[arg-type]
            prompt=full_prompt,
            n=1,
            size=size,  # type: ignore[arg-type]
        )
    finally:
        for hnd in handles:
            hnd.close()

    b64 = resp.data[0].b64_json or ""

    palette = _palette_from_reference(refs[0]) if match_reference_colors else None
    palette_note = "sampled from reference" if palette else "neutral default"

    copy = {
        "badge": badge,
        "headline": headline,
        "body_copy": body_copy,
        "metric": metric,
        "call_to_action": call_to_action,
        "trust_items": trust_items or [],
    }
    b64 = composite_text(b64, platform_key, copy, palette=palette)

    # Logo: prefer an explicitly uploaded logo; never fall back to a stored brand
    # logo unless the caller passed a brand_id AND opted in.
    resolved_logo = logo_path if (logo_path and Path(logo_path).exists()) else None
    if apply_logo and (resolved_logo or brand_id):
        b64 = composite_logo(b64, brand_id, platform_key, logo_path=resolved_logo)
        if resolved_logo:
            logo_note = "uploaded logo composited"
        else:
            logo_note = "brand logo composited" if find_logo(brand_id) else "no logo found"
    else:
        logo_note = "logo skipped"

    output_dir = os.path.abspath(settings.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{platform_key}_{uuid.uuid4().hex[:8]}.png"
    image_path = os.path.join(output_dir, filename)
    with open(image_path, "wb") as f:
        f.write(base64.b64decode(b64))

    return {
        "platform": platform_key,
        "image_path": image_path,
        "size": size,
        "used_references": len(refs),
        "metric_status": metric_note,
        "logo_status": logo_note,
        "palette_status": palette_note,
        "status": "success",
    }


_IMPROVE_PROMPT = (
    "Refine THIS exact image into a cleaner, more polished version of ITSELF. "
    "Preserve its own identity to the letter: keep the SAME color palette, the "
    "SAME background, the SAME layout and composition, and ALL existing text and "
    "numbers exactly as-is — do NOT add, remove, translate or restyle any text, "
    "do NOT introduce new people, objects, logos, colors or branding. Only "
    "improve technical quality: sharpen edges, refine lighting, depth, spacing "
    "and overall polish. No new logo, no watermark."
)


def improve_flyer(
    image_path: str,
    instructions: str = "",
    n_variations: int = 1,
) -> dict:
    """
    Improve an EXISTING image: feed ONLY that image to gpt-image-1's edit
    endpoint to produce refined variations that keep its own identity.

    It does not re-composite text and — importantly — does NOT inject any brand
    reference images, so the result stays faithful to the source instead of
    drifting toward another brand's look.

    Args:
        image_path: path to the image to improve (PNG/JPEG/WEBP).
        instructions: optional extra direction (e.g. "more contrast on the CTA").
        n_variations: how many refined variations to produce (1-4).

    Returns:
        dict with the list of saved variation paths and a status message.
    """
    src = Path(image_path)
    if not src.exists():
        return {"error": f"image not found: {image_path}", "status": "error"}

    with Image.open(src) as im:
        size = _size_from_ratio(im.width / im.height)

    prompt = _IMPROVE_PROMPT + (f"\n\nExtra direction: {instructions}" if instructions else "")
    n = max(1, min(int(n_variations), 4))

    # Only the source image — no brand reference images. Feeding the brand refs
    # was what dragged improved results toward the Bússola green identity.
    handles = [open(src, "rb")]
    try:
        resp = _client.images.edit(
            model=settings.image_model,
            image=handles,  # type: ignore[arg-type]
            prompt=prompt,
            n=n,
            size=size,  # type: ignore[arg-type]
        )
    finally:
        for h in handles:
            h.close()

    output_dir = os.path.abspath(settings.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    paths: list[str] = []
    for item in resp.data:
        b64 = item.b64_json or ""
        if not b64:
            continue
        out = os.path.join(output_dir, f"{src.stem}_improved_{uuid.uuid4().hex[:8]}.png")
        with open(out, "wb") as f:
            f.write(base64.b64decode(b64))
        paths.append(out)

    return {
        "source": str(src),
        "variations": paths,
        "count": len(paths),
        "used_references": False,
        "status": "success" if paths else "error",
    }
