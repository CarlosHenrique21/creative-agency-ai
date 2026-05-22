"""
Campaign state models.

The ADK passes state between agents via ToolContext.state (a plain dict).
These Pydantic models are used at the API boundary for validation and
serialisation, and as typed helpers when reading/writing the ADK session.

ADK session keys (all strings):
  campaign_id, brief, brand, brand_id,
  platforms, brand_rag_context, visual_rag_context,
  creative_direction, flyers, quality_scores,
  revision_cycle, status, messages
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field
from enum import Enum


class Platform(str, Enum):
    INSTAGRAM_FEED = "instagram_feed"
    INSTAGRAM_STORY = "instagram_story"
    LINKEDIN_POST = "linkedin_post"
    LINKEDIN_BANNER = "linkedin_banner"


PLATFORM_DIMENSIONS: dict[Platform, tuple[int, int]] = {
    Platform.INSTAGRAM_FEED: (1080, 1080),
    Platform.INSTAGRAM_STORY: (1080, 1920),
    Platform.LINKEDIN_POST: (1200, 627),
    Platform.LINKEDIN_BANNER: (1584, 396),
}


class BrandProfile(BaseModel):
    name: str
    primary_color: str = "#000000"
    secondary_color: str = "#FFFFFF"
    accent_color: str = "#FF6B00"
    font_style: str = "modern sans-serif"
    tone: str = "professional"
    logo_description: str = ""


class FlyerSpec(BaseModel):
    platform: Platform
    headline: str = ""
    subheadline: str = ""
    body_copy: str = ""
    call_to_action: str = ""
    image_prompt: str = ""
    image_url: str = ""
    image_b64: str = ""
    width: int = 0
    height: int = 0
    revision_notes: str = ""

    def set_dimensions(self) -> None:
        self.width, self.height = PLATFORM_DIMENSIONS[self.platform]


class AgentMessage(BaseModel):
    agent: str
    content: str
    role: Literal["assistant", "system"] = "assistant"


class QualityScore(BaseModel):
    brand_consistency: int = Field(ge=0, le=10)
    visual_appeal: int = Field(ge=0, le=10)
    copy_clarity: int = Field(ge=0, le=10)
    platform_fit: int = Field(ge=0, le=10)
    overall: float = 0.0
    approved: bool = False
    feedback: str = ""

    def calculate_overall(self) -> None:
        self.overall = (
            self.brand_consistency
            + self.visual_appeal
            + self.copy_clarity
            + self.platform_fit
        ) / 4
        self.approved = self.overall >= 7.5


class CampaignInput(BaseModel):
    """Validated input received from the API — converted to ADK session state."""
    campaign_id: str
    brief: str
    brand: BrandProfile
    platforms: list[Platform]
    brand_id: str = ""

    def to_session_state(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "brief": self.brief,
            "brand": self.brand.model_dump(),
            "brand_id": self.brand_id,
            "platforms": [p.value for p in self.platforms],
            "brand_rag_context": "",
            "visual_rag_context": "",
            "creative_direction": "",
            "flyers": {},
            "quality_scores": {},
            "revision_cycle": 0,
            "status": "running",
            "messages": [],
        }
