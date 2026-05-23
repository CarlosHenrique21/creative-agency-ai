"""
ADK tool: initialize campaign state from the user message.
Used by brand_strategist to ensure brand_id and platforms are set
even when the pipeline is triggered via ADK Web UI (no API pre-state).
"""
from __future__ import annotations

from google.adk.tools import ToolContext

# Map of known brand names → brand_ids (matches ChromaDB ingest)
_BRAND_ID_MAP = {
    "bussola fiscal": "bussola_fiscal",
    "bussola_fiscal": "bussola_fiscal",
    "bussola-fiscal": "bussola_fiscal",
    "bussolafiscal": "bussola_fiscal",
}

_VALID_PLATFORMS = {
    "instagram_feed", "instagram_story", "linkedin_post", "linkedin_banner"
}


def set_selected_theme(
    theme_name: str,
    creative_angle: str,
    tool_context: ToolContext,
) -> dict:
    """
    Salva o tema escolhido pelo usuário no session state.

    Args:
        theme_name: nome ou número do tema escolhido
        creative_angle: descrição do ângulo criativo a seguir
        tool_context: ADK tool context

    Returns:
        Confirmação do tema salvo
    """
    tool_context.state["selected_theme"] = theme_name
    tool_context.state["creative_angle"] = creative_angle
    tool_context.state["pending_theme_selection"] = False
    return {
        "theme": theme_name,
        "creative_angle": creative_angle,
        "status": "theme_selected",
    }


def apply_copy_changes(
    platform_key: str,
    headline: str,
    subheadline: str,
    body_copy: str,
    call_to_action: str,
    tool_context: ToolContext,
) -> dict:
    """
    Aplica alterações nos textos do flyer solicitadas pelo usuário.

    Args:
        platform_key: "instagram_feed" ou "linkedin_post"
        headline: novo headline
        subheadline: novo subheadline
        body_copy: novo body copy
        call_to_action: novo CTA
        tool_context: ADK tool context

    Returns:
        Confirmação das alterações aplicadas
    """
    flyers: dict = tool_context.state.get("flyers", {})
    if platform_key in flyers:
        flyers[platform_key]["headline"] = headline
        flyers[platform_key]["subheadline"] = subheadline
        flyers[platform_key]["body_copy"] = body_copy
        flyers[platform_key]["call_to_action"] = call_to_action
    tool_context.state["flyers"] = flyers
    tool_context.state["pending_copy_approval"] = False
    tool_context.state["copy_approved"] = True
    return {
        "platform": platform_key,
        "updated": True,
        "status": "copy_updated",
    }


def initialize_campaign(
    brand_name: str,
    platforms: list[str],
    brief: str,
    tool_context: ToolContext,
) -> dict:
    """
    Set brand_id, platforms, brief and initial flyer slots in session state.
    Call this first before any RAG queries.

    Args:
        brand_name: brand name as mentioned in the user message (e.g. "BussolaFiscal")
        platforms: list of platform keys (e.g. ["instagram_feed", "linkedin_post"])
        brief: campaign brief text
        tool_context: ADK tool context

    Returns:
        dict confirming what was set
    """
    # Resolve brand_id
    brand_id = _BRAND_ID_MAP.get(brand_name.lower().strip(), brand_name.lower().replace(" ", "_"))
    tool_context.state["brand_id"] = brand_id

    # Normalize and validate platforms
    valid = [p for p in platforms if p in _VALID_PLATFORMS]
    if not valid:
        valid = ["instagram_feed"]
    tool_context.state["platforms"] = valid

    # Set brief if not already set
    if not tool_context.state.get("brief"):
        tool_context.state["brief"] = brief

    # Initialize flyer slots for each platform
    flyers: dict = tool_context.state.get("flyers", {})
    for platform in valid:
        if platform not in flyers:
            flyers[platform] = {
                "platform": platform,
                "headline": "",
                "subheadline": "",
                "body_copy": "",
                "call_to_action": "",
                "image_prompt": "",
                "image_path": "",
                "revision_notes": "",
            }
    tool_context.state["flyers"] = flyers

    return {
        "brand_id": brand_id,
        "platforms": valid,
        "brief_set": bool(brief),
        "status": "initialized",
    }
