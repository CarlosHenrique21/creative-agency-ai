"""
ADK tool: persist quality scores and set revision flags in session state.
"""
from __future__ import annotations

from google.adk.tools import ToolContext

from core.state import QualityScore


def score_flyer_quality(
    platform_key: str,
    brand_consistency: int,
    visual_appeal: int,
    copy_clarity: int,
    platform_fit: int,
    feedback: str,
    revision_notes: str,
    tool_context: ToolContext,
) -> dict:
    """
    Record the quality score for a single flyer and update session state.
    If the score is below threshold, the revision_notes are written back
    into the FlyerSpec so the Copywriter can act on them.

    Args:
        platform_key: e.g. "instagram_feed"
        brand_consistency: score 0-10
        visual_appeal: score 0-10
        copy_clarity: score 0-10
        platform_fit: score 0-10
        feedback: overall feedback string
        revision_notes: specific actionable notes if revision is needed
        tool_context: ADK tool context (provides session state)

    Returns:
        Score summary dict including overall and approved flag.
    """
    score = QualityScore(
        brand_consistency=brand_consistency,
        visual_appeal=visual_appeal,
        copy_clarity=copy_clarity,
        platform_fit=platform_fit,
        feedback=feedback,
    )
    score.calculate_overall()

    # Persist score
    quality_scores: dict = tool_context.state.get("quality_scores", {})
    quality_scores[platform_key] = score.model_dump()
    tool_context.state["quality_scores"] = quality_scores

    # Write revision notes back into flyer spec if not approved
    if not score.approved and revision_notes:
        flyers: dict = tool_context.state.get("flyers", {})
        if platform_key in flyers:
            flyers[platform_key]["revision_notes"] = revision_notes
            tool_context.state["flyers"] = flyers

    # Update global status based on all scores so far
    all_scores = list(quality_scores.values())
    all_approved = all(s.get("approved", False) for s in all_scores)

    platforms: list = tool_context.state.get("platforms", [])
    all_platforms_scored = len(all_scores) >= len(platforms)

    if all_platforms_scored:
        if all_approved:
            tool_context.state["status"] = "completed"
        else:
            cycle = tool_context.state.get("revision_cycle", 0)
            tool_context.state["revision_cycle"] = cycle + 1
            tool_context.state["status"] = "needs_revision"

    return {
        "platform": platform_key,
        "overall": score.overall,
        "approved": score.approved,
        "brand_consistency": brand_consistency,
        "visual_appeal": visual_appeal,
        "copy_clarity": copy_clarity,
        "platform_fit": platform_fit,
        "feedback": feedback,
    }
