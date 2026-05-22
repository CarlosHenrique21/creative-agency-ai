from __future__ import annotations
import uuid
from fastapi import APIRouter, HTTPException
from models.requests import GenerateFlyersRequest
from models.responses import GenerateFlyersResponse
from core.state import CampaignInput
from core.orchestrator import run_campaign
import structlog

router = APIRouter(prefix="/api/v1", tags=["flyers"])
logger = structlog.get_logger()


@router.post("/flyers/generate", response_model=GenerateFlyersResponse)
async def generate_flyers(request: GenerateFlyersRequest) -> GenerateFlyersResponse:
    campaign_id = str(uuid.uuid4())
    logger.info("campaign_started", campaign_id=campaign_id, brief=request.brief[:80])

    campaign_input = CampaignInput(
        campaign_id=campaign_id,
        brief=request.brief,
        brand=request.brand,
        platforms=request.platforms,
        brand_id=request.brand_id,
    )

    try:
        final_state = await run_campaign(campaign_input)
    except Exception as exc:
        logger.error("campaign_failed", campaign_id=campaign_id, error=str(exc))
        raise HTTPException(status_code=500, detail=f"Campaign failed: {exc}") from exc

    return GenerateFlyersResponse.from_state(final_state)


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
