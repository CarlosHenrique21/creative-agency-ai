import pytest
from core.state import CampaignState, BrandProfile, Platform, FlyerSpec, QualityScore


def make_state() -> CampaignState:
    return CampaignState(
        campaign_id="test-001",
        brief="Teste de campanha",
        brand=BrandProfile(name="TestBrand"),
        platforms=[Platform.INSTAGRAM_FEED, Platform.LINKEDIN_POST],
    )


def test_flyer_spec_sets_dimensions() -> None:
    spec = FlyerSpec(platform=Platform.INSTAGRAM_FEED)
    spec.set_dimensions()
    assert spec.width == 1080
    assert spec.height == 1080


def test_flyer_spec_story_dimensions() -> None:
    spec = FlyerSpec(platform=Platform.INSTAGRAM_STORY)
    spec.set_dimensions()
    assert spec.width == 1080
    assert spec.height == 1920


def test_quality_score_approval() -> None:
    score = QualityScore(
        brand_consistency=8,
        visual_appeal=8,
        copy_clarity=8,
        platform_fit=8,
    )
    score.calculate_overall()
    assert score.approved is True
    assert score.overall == 8.0


def test_quality_score_rejection() -> None:
    score = QualityScore(
        brand_consistency=6,
        visual_appeal=7,
        copy_clarity=6,
        platform_fit=7,
    )
    score.calculate_overall()
    assert score.approved is False


def test_campaign_state_messages_accumulate() -> None:
    from core.state import AgentMessage

    state = make_state()
    state.messages.append(AgentMessage(agent="brand_strategist", content="Analysis done"))
    state.messages.append(AgentMessage(agent="creative_director", content="Direction set"))
    assert len(state.messages) == 2
