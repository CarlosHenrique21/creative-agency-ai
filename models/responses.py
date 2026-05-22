from pydantic import BaseModel
from core.state import FlyerSpec, QualityScore, AgentMessage


class FlyerResult(BaseModel):
    platform: str
    headline: str
    subheadline: str
    body_copy: str
    call_to_action: str
    image_url: str
    image_b64: str
    image_prompt: str
    quality: QualityScore | None = None


class GenerateFlyersResponse(BaseModel):
    campaign_id: str
    status: str
    revision_cycles: int
    flyers: list[FlyerResult]
    agent_log: list[AgentMessage]

    @classmethod
    def from_state(cls, state: dict) -> "GenerateFlyersResponse":
        flyers_raw: dict[str, FlyerSpec] = state.get("flyers", {})
        scores: dict[str, QualityScore] = state.get("quality_scores", {})

        flyers = [
            FlyerResult(
                platform=key,
                headline=spec.headline,
                subheadline=spec.subheadline,
                body_copy=spec.body_copy,
                call_to_action=spec.call_to_action,
                image_url=spec.image_url,
                image_b64=spec.image_b64,
                image_prompt=spec.image_prompt,
                quality=scores.get(key),
            )
            for key, spec in flyers_raw.items()
        ]

        return cls(
            campaign_id=state["campaign_id"],
            status=state.get("status", "unknown"),
            revision_cycles=state.get("revision_cycle", 0),
            flyers=flyers,
            agent_log=state.get("messages", []),
        )
