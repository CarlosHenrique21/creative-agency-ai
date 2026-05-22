import pytest
from core.state import CampaignInput, BrandProfile, Platform, FlyerSpec, QualityScore


def make_input() -> CampaignInput:
    return CampaignInput(
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
    score = QualityScore(brand_consistency=8, visual_appeal=8, copy_clarity=8, platform_fit=8)
    score.calculate_overall()
    assert score.approved is True
    assert score.overall == 8.0


def test_quality_score_rejection() -> None:
    score = QualityScore(brand_consistency=6, visual_appeal=7, copy_clarity=6, platform_fit=7)
    score.calculate_overall()
    assert score.approved is False


def test_campaign_input_to_session_state() -> None:
    inp = make_input()
    state = inp.to_session_state()

    assert state["campaign_id"] == "test-001"
    assert state["brief"] == "Teste de campanha"
    assert state["brand"]["name"] == "TestBrand"
    assert "instagram_feed" in state["platforms"]
    assert state["flyers"] == {}
    assert state["revision_cycle"] == 0
    assert state["status"] == "running"


def test_session_state_has_rag_fields() -> None:
    inp = make_input()
    state = inp.to_session_state()
    assert "brand_rag_context" in state
    assert "visual_rag_context" in state
    assert state["brand_rag_context"] == ""
