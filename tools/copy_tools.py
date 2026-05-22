"""
ADK tool: write platform-specific copy and persist FlyerSpec into session state.
"""
from __future__ import annotations

import json
import re

from google.adk.tools import ToolContext

from core.state import FlyerSpec, Platform, BrandProfile


def write_platform_copy(
    platform_key: str,
    headline: str,
    subheadline: str,
    body_copy: str,
    call_to_action: str,
    tool_context: ToolContext,
) -> dict:
    """
    Persist the copywriter's output for a single platform into session state.
    Creates or updates the FlyerSpec for this platform.

    Args:
        platform_key: e.g. "instagram_feed"
        headline: main headline text
        subheadline: supporting headline
        body_copy: body text
        call_to_action: CTA button/link text
        tool_context: ADK tool context (provides session state)

    Returns:
        Confirmation dict with the stored copy fields.
    """
    platform = Platform(platform_key)
    spec = FlyerSpec(platform=platform)
    spec.set_dimensions()

    # Preserve existing image data if the spec already exists (revision cycle)
    flyers: dict = tool_context.state.get("flyers", {})
    if platform_key in flyers:
        existing = flyers[platform_key]
        spec.image_b64 = existing.get("image_b64", "")
        spec.image_url = existing.get("image_url", "")
        spec.image_prompt = existing.get("image_prompt", "")

    spec.headline = headline
    spec.subheadline = subheadline
    spec.body_copy = body_copy
    spec.call_to_action = call_to_action

    flyers[platform_key] = spec.model_dump()
    tool_context.state["flyers"] = flyers

    return {
        "platform": platform_key,
        "headline": headline,
        "subheadline": subheadline,
        "body_copy": body_copy,
        "call_to_action": call_to_action,
        "dimensions": f"{spec.width}x{spec.height}px",
        "status": "saved",
    }
