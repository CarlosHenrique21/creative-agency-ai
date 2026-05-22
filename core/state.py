from __future__ import annotations
from typing import Annotated, Literal
from pydantic import BaseModel, Field
from enum import Enum
import operator


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


class CampaignState(BaseModel):
    # Input
    campaign_id: str
    brief: str
    brand: BrandProfile
    platforms: list[Platform]
    # Optional: link to a pre-ingested brand in the RAG stores
    brand_id: str = ""

    # Agent outputs accumulated via append
    messages: Annotated[list[AgentMessage], operator.add] = Field(default_factory=list)

    # RAG context injected before agents run
    brand_rag_context: str = ""
    visual_rag_context: str = ""

    # Working data
    creative_direction: str = ""
    flyers: dict[str, FlyerSpec] = Field(default_factory=dict)
    quality_scores: dict[str, QualityScore] = Field(default_factory=dict)
    revision_cycle: int = 0
    status: str = "pending"
    error: str = ""
