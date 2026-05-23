"""
ADK orchestration for the Social Media Agency pipeline.

Fluxo interativo (com pausas para aprovação humana):

FASE 1 — Pesquisa e escolha de tema:
  brand_strategist → visual_analyst → market_analyst
  [PAUSA — usuário escolhe o tema]
  theme_selector

FASE 2 — Direção criativa e textos:
  creative_director → copywriter → copy_approver
  [PAUSA — usuário aprova ou altera os textos]
  copy_reviewer

FASE 3 — Geração de imagens e revisão:
  revision_loop (LoopAgent):
    designer → social_media_manager → quality_reviewer
  [quality_reviewer chama exit_loop quando aprovado]
"""
from __future__ import annotations

from google.adk.agents import SequentialAgent, LoopAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from agents import (
    brand_strategist_agent,
    visual_analyst_agent,
    market_analyst_agent,
    theme_selector_agent,
    creative_director_agent,
    copywriter_agent,
    copy_approver_agent,
    copy_reviewer_agent,
    designer_agent,
    social_media_manager_agent,
    quality_reviewer_agent,
)
from core.config import settings
from core.state import CampaignInput
import structlog

logger = structlog.get_logger()

APP_NAME = "social_media_agency"

# Fase 3 — Geração de imagens com revisão automática
image_revision_loop = LoopAgent(
    name="image_revision_loop",
    max_iterations=settings.max_revision_cycles,
    sub_agents=[
        designer_agent,
        social_media_manager_agent,
        quality_reviewer_agent,
    ],
)

# Pipeline completo com pausas para input humano
agency_pipeline = SequentialAgent(
    name="agency_pipeline",
    description="Pipeline interativo de criação de flyers com aprovação humana em pontos-chave.",
    sub_agents=[
        # Fase 1 — Pesquisa e escolha de tema
        brand_strategist_agent,
        visual_analyst_agent,
        market_analyst_agent,   # [PAUSA] aguarda usuário escolher tema
        theme_selector_agent,   # processa escolha e seta selected_theme

        # Fase 2 — Direção criativa e textos
        creative_director_agent,
        copywriter_agent,
        copy_approver_agent,    # [PAUSA] aguarda aprovação/alteração dos textos
        copy_reviewer_agent,    # processa resposta e aplica alterações se houver

        # Fase 3 — Geração de imagens
        image_revision_loop,
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
        pass

    final_session = await _session_service.get_session(
        app_name=APP_NAME,
        user_id="api",
        session_id=session_id,
    )

    final_state: dict = dict(final_session.state) if final_session else initial_state
    logger.info("campaign_completed", campaign_id=session_id, status=final_state.get("status"))
    return final_state
