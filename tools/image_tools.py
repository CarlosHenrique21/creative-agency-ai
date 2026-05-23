"""
ADK tool: generate a social media flyer image with gpt-image-1,
then composite the brand logo on top via Pillow.
"""
from __future__ import annotations

import base64
import os
import uuid
from google.adk.tools import ToolContext
from openai import OpenAI

from core.config import settings
from rag.logo_compositor import composite_logo, find_logo

# Sync OpenAI client — ADK tools are called synchronously by the framework
_client = OpenAI(api_key=settings.openai_api_key)

_SIZE_MAP = {
    "square": "1024x1024",
    "landscape": "1536x1024",
    "portrait": "1024x1536",
}


def generate_flyer_image(
    platform_key: str,
    image_prompt: str,
    headline: str,
    call_to_action: str,
    tool_context: ToolContext,
) -> dict:
    """
    Generate a flyer image for the given platform using gpt-image-1
    and composite the brand logo on top.

    Args:
        platform_key: e.g. "instagram_feed", "linkedin_post"
        image_prompt: detailed visual prompt in English
        headline: headline text (used to reserve space in prompt)
        call_to_action: CTA text (used to reserve space in prompt)
        tool_context: ADK tool context (provides session state)

    Returns:
        dict with image_path (saved PNG file) and status message
    """
    brand_id: str = tool_context.state.get("brand_id", "")

    # Determine output size from platform
    dimensions = {
        "instagram_feed": (1080, 1080),
        "instagram_story": (1080, 1920),
        "linkedin_post": (1200, 627),
        "linkedin_banner": (1584, 396),
    }
    w, h = dimensions.get(platform_key, (1080, 1080))
    ratio = w / h
    if 0.9 <= ratio <= 1.1:
        size = "1024x1024"
    elif ratio > 1.1:
        size = "1536x1024"
    else:
        size = "1024x1536"

    # Add technical requirements to prompt
    full_prompt = (
        f"{image_prompt}\n\n"
        f"Technical requirements: {w}x{h}px, high resolution, "
        f"professional social media flyer, no watermarks, clean composition, "
        f"text overlay space reserved for: headline '{headline}', CTA '{call_to_action}'."
    )

    # Add logo space instruction when a logo exists
    if brand_id and find_logo(brand_id):
        logo_areas = {
            "instagram_feed": "bottom-right corner",
            "instagram_story": "top-center area",
            "linkedin_post": "bottom-right corner",
            "linkedin_banner": "left-center area",
        }
        area = logo_areas.get(platform_key, "bottom-right corner")
        full_prompt += (
            f" Leave a clean uncluttered {area} for the brand logo overlay. "
            "Do NOT generate a logo or watermark — it will be added in post-processing."
        )

    response = _client.images.generate(
        model=settings.image_model,
        prompt=full_prompt,
        n=1,
        size=size,  # type: ignore[arg-type]
        quality=settings.image_quality,  # type: ignore[arg-type]
    )

    b64 = response.data[0].b64_json or ""

    # Composite logo using Pillow
    if brand_id:
        b64 = composite_logo(b64, brand_id, platform_key)
        logo_note = "logo composited" if find_logo(brand_id) else "no logo found"
    else:
        logo_note = "no brand_id — logo skipped"

    # Save image to disk — keep only the file path in session state to avoid
    # flooding the LLM context window with raw base64 (~3M tokens per image).
    output_dir = os.path.abspath(settings.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{platform_key}_{uuid.uuid4().hex[:8]}.png"
    image_path = os.path.join(output_dir, filename)
    with open(image_path, "wb") as f:
        f.write(base64.b64decode(b64))

    # Persist only metadata (no base64) into session state
    flyers: dict = tool_context.state.get("flyers", {})
    if platform_key in flyers:
        flyers[platform_key]["image_path"] = image_path
        flyers[platform_key]["image_prompt"] = image_prompt
    tool_context.state["flyers"] = flyers

    return {
        "platform": platform_key,
        "image_path": image_path,
        "size": size,
        "logo_status": logo_note,
        "status": "success",
    }
