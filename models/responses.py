from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel
from core.state import QualityScore, AgentMessage


class FlyerResult(BaseModel):
    platform: str
    headline: str
    subheadline: str
    body_copy: str
    call_to_action: str
    image_path: str = ""
    image_url: str = ""
    image_b64: str = ""
    image_prompt: str = ""
    quality: QualityScore | None = None


class ContentResponse(BaseModel):
    """Structured copy produced by the content flow (editable by the user)."""
    platform: str
    headline: str = ""
    subheadline: str = ""
    body_copy: str = ""
    badge: str = ""
    metric: str = ""
    call_to_action: str = ""
    trust_items: list[str] = []


class GenerateImageResponse(BaseModel):
    """A single flyer produced by the direct image flow."""
    status: str
    platform: str
    image_path: str
    image_url: str
    size: str
    used_references: int
    metric_status: str
    logo_status: str
    palette_status: str = ""


class FlyerVariation(BaseModel):
    path: str   # absolute path on the server
    url: str    # URL served via the /files static mount


class ImproveFlyerResponse(BaseModel):
    status: str
    source: str
    count: int
    used_references: bool
    variations: list[FlyerVariation]


class GenerateFlyersResponse(BaseModel):
    campaign_id: str
    status: str
    revision_cycles: int
    flyers: list[FlyerResult]
    agent_log: list[AgentMessage]

    @classmethod
    def from_state(cls, state: dict) -> "GenerateFlyersResponse":
        # ADK session state stores flyers and scores as plain dicts
        flyers_raw: dict[str, dict] = state.get("flyers", {})
        scores_raw: dict[str, dict] = state.get("quality_scores", {})
        messages_raw: list[dict] = state.get("messages", [])

        def _url(spec: dict) -> str:
            path = spec.get("image_path", "")
            if path:
                return f"/files/{Path(path).name}"
            return spec.get("image_url", "")

        flyers = [
            FlyerResult(
                platform=key,
                headline=spec.get("headline", ""),
                subheadline=spec.get("subheadline", ""),
                body_copy=spec.get("body_copy", ""),
                call_to_action=spec.get("call_to_action", ""),
                image_path=spec.get("image_path", ""),
                image_url=_url(spec),
                image_b64=spec.get("image_b64", ""),
                image_prompt=spec.get("image_prompt", ""),
                quality=QualityScore(**scores_raw[key]) if key in scores_raw else None,
            )
            for key, spec in flyers_raw.items()
        ]

        agent_log = [
            AgentMessage(
                agent=m.get("agent", "unknown"),
                content=m.get("content", ""),
            )
            for m in messages_raw
        ]

        return cls(
            campaign_id=state.get("campaign_id", ""),
            status=state.get("status", "unknown"),
            revision_cycles=state.get("revision_cycle", 0),
            flyers=flyers,
            agent_log=agent_log,
        )
