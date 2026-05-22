"""
ADK orchestration for the Social Media Agency pipeline.

Pipeline (SequentialAgent):
  brand_strategist → creative_director → revision_loop

revision_loop (LoopAgent, max N iterations):
  copywriter → designer → social_media_manager → quality_reviewer

The LoopAgent exits when quality_reviewer sets session state status = "completed"
or when max_iterations is reached.
"""
from __future__ import annotations

from google.adk.agents import SequentialAgent, LoopAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from agents import (
    brand_strategist_agent,
    creative_director_agent,
    copywriter_agent,
    designer_agent,
    social_media_manager_agent,
    quality_reviewer_agent,
)
from core.config import settings
from core.state import CampaignInput
import structlog

logger = structlog.get_logger()

APP_NAME = "social_media_agency"

# Inner loop: copy → design → review (runs up to max_revision_cycles times)
revision_loop = LoopAgent(
    name="revision_loop",
    max_iterations=settings.max_revision_cycles,
    sub_agents=[
        copywriter_agent,
        designer_agent,
        social_media_manager_agent,
        quality_reviewer_agent,
    ],
)

# Full pipeline
agency_pipeline = SequentialAgent(
    name="agency_pipeline",
    description="Full social media flyer generation pipeline",
    sub_agents=[
        brand_strategist_agent,
        creative_director_agent,
        revision_loop,
    ],
)

# Session service (in-memory; swap for DatabaseSessionService in production)
_session_service = InMemorySessionService()

# Runner wires the pipeline to the session service
_runner = Runner(
    agent=agency_pipeline,
    app_name=APP_NAME,
    session_service=_session_service,
)


async def run_campaign(campaign_input: CampaignInput) -> dict:
    """
    Create an ADK session, run the full agency pipeline and return
    the final session state as a plain dict.
    """
    session_id = campaign_input.campaign_id
    initial_state = campaign_input.to_session_state()

    session = await _session_service.create_session(
        app_name=APP_NAME,
        user_id="api",
        session_id=session_id,
        state=initial_state,
    )

    logger.info(
        "campaign_started",
        campaign_id=session_id,
        brand_id=campaign_input.brand_id,
        platforms=[p.value for p in campaign_input.platforms],
    )

    # Kick off the pipeline with the campaign brief as the initial user message
    kick_off = Content(
        role="user",
        parts=[Part(text=(
            f"Inicie a campanha.\n"
            f"Brief: {campaign_input.brief}\n"
            f"Marca: {campaign_input.brand.name}\n"
            f"Plataformas: {[p.value for p in campaign_input.platforms]}"
        ))],
    )

    async for _event in _runner.run_async(
        user_id="api",
        session_id=session_id,
        new_message=kick_off,
    ):
        # Events are streamed; we only need the final state
        pass

    final_session = await _session_service.get_session(
        app_name=APP_NAME,
        user_id="api",
        session_id=session_id,
    )

    final_state: dict = dict(final_session.state) if final_session else initial_state
    logger.info("campaign_completed", campaign_id=session_id, status=final_state.get("status"))
    return final_state
