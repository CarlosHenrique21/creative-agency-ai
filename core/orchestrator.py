from __future__ import annotations
from langgraph.graph import StateGraph, END
from core.state import CampaignState
from core.config import settings
from agents import (
    BrandStrategistAgent,
    CreativeDirectorAgent,
    CopywriterAgent,
    DesignerAgent,
    SocialMediaManagerAgent,
    QualityReviewerAgent,
)
import structlog

logger = structlog.get_logger()

# Instantiate agents once (they hold a shared AsyncOpenAI client)
brand_strategist = BrandStrategistAgent()
creative_director = CreativeDirectorAgent()
copywriter = CopywriterAgent()
designer = DesignerAgent()
social_media_manager = SocialMediaManagerAgent()
quality_reviewer = QualityReviewerAgent()


async def run_brand_strategist(state: CampaignState) -> dict:
    return await brand_strategist.run(state)


async def run_creative_director(state: CampaignState) -> dict:
    return await creative_director.run(state)


async def run_copywriter(state: CampaignState) -> dict:
    return await copywriter.run(state)


async def run_designer(state: CampaignState) -> dict:
    return await designer.run(state)


async def run_social_media_manager(state: CampaignState) -> dict:
    return await social_media_manager.run(state)


async def run_quality_reviewer(state: CampaignState) -> dict:
    return await quality_reviewer.run(state)


def should_revise(state: CampaignState) -> str:
    if state.status == "completed":
        return "done"
    if state.revision_cycle >= settings.max_revision_cycles:
        logger.warning("max_revisions_reached", cycle=state.revision_cycle)
        return "done"
    return "revise"


def build_graph() -> StateGraph:
    graph = StateGraph(CampaignState)

    graph.add_node("brand_strategist", run_brand_strategist)
    graph.add_node("creative_director", run_creative_director)
    graph.add_node("copywriter", run_copywriter)
    graph.add_node("designer", run_designer)
    graph.add_node("social_media_manager", run_social_media_manager)
    graph.add_node("quality_reviewer", run_quality_reviewer)

    graph.set_entry_point("brand_strategist")
    graph.add_edge("brand_strategist", "creative_director")
    graph.add_edge("creative_director", "copywriter")
    graph.add_edge("copywriter", "designer")
    graph.add_edge("designer", "social_media_manager")
    graph.add_edge("social_media_manager", "quality_reviewer")

    graph.add_conditional_edges(
        "quality_reviewer",
        should_revise,
        {"done": END, "revise": "copywriter"},
    )

    return graph


agency_graph = build_graph().compile()
