from __future__ import annotations
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from models.requests import GenerateContentRequest, GenerateFlyersRequest
from models.responses import (
    ContentResponse,
    FlyerVariation,
    GenerateFlyersResponse,
    GenerateImageResponse,
    ImproveFlyerResponse,
)
from core.config import settings
from core.state import CampaignInput
from core.orchestrator import run_campaign
from tools.content_tools import generate_content
from tools.image_tools import generate_from_reference, improve_flyer
import structlog

router = APIRouter(prefix="/api/v1", tags=["flyers"])
logger = structlog.get_logger()

_ALLOWED_UPLOAD_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def _file_url(path: str) -> str:
    """Map an output-dir file path to its /files static URL."""
    return f"/files/{Path(path).name}"


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


@router.post("/flyers/improve", response_model=ImproveFlyerResponse)
async def improve_flyer_endpoint(
    file: UploadFile | None = File(
        default=None, description="Imagem do flyer a melhorar (PNG/JPEG/WEBP)."
    ),
    image_path: str = Form(
        default="", description="Alternativa ao upload: caminho server-side de um flyer já gerado."
    ),
    instructions: str = Form(default="", description="Direção extra (ex: 'mais contraste no CTA')."),
    n_variations: int = Form(default=1, ge=1, le=4, description="Quantas variações gerar (1-4)."),
    extra_image: UploadFile | None = File(
        default=None,
        description="Segunda imagem para MESCLAR na base (ex: foto de uma modelo). Opcional.",
    ),
) -> ImproveFlyerResponse:
    """
    Melhora um flyer existente: refina a arte mantendo o texto, gerando variações
    via gpt-image-1. Aceita upload de imagem OU o caminho de um flyer já produzido.
    Quando `extra_image` é enviada, o sujeito dela (ex: uma modelo) é integrado à
    imagem base preservando a paleta, o layout e o texto.
    """
    output_dir = os.path.abspath(settings.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Resolve the source image: uploaded file takes precedence over image_path.
    if file is not None:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in _ALLOWED_UPLOAD_EXT:
            raise HTTPException(status_code=400, detail=f"Formato não suportado: {ext or 'desconhecido'}")
        src_path = os.path.join(output_dir, f"upload_{uuid.uuid4().hex[:8]}{ext}")
        with open(src_path, "wb") as f:
            f.write(await file.read())
    elif image_path:
        # Restrict to files inside the output dir to avoid path traversal.
        candidate = os.path.abspath(image_path)
        if os.path.commonpath([candidate, output_dir]) != output_dir or not os.path.exists(candidate):
            raise HTTPException(status_code=400, detail="image_path inválido ou inexistente.")
        src_path = candidate
    else:
        raise HTTPException(status_code=400, detail="Envie um arquivo (file) ou um image_path.")

    # Optional second image to merge into the base.
    extra_path = ""
    if extra_image is not None and extra_image.filename:
        eext = Path(extra_image.filename).suffix.lower()
        if eext not in _ALLOWED_UPLOAD_EXT:
            raise HTTPException(status_code=400, detail=f"Imagem extra em formato não suportado: {eext or 'desconhecido'}")
        extra_path = os.path.join(output_dir, f"merge_{uuid.uuid4().hex[:8]}{eext}")
        with open(extra_path, "wb") as f:
            f.write(await extra_image.read())

    logger.info("improve_started", source=src_path, n_variations=n_variations, merge=bool(extra_path))
    try:
        result = improve_flyer(
            src_path, instructions=instructions, n_variations=n_variations,
            extra_image_path=extra_path,
        )
    except Exception as exc:
        logger.error("improve_failed", source=src_path, error=str(exc))
        raise HTTPException(status_code=500, detail=f"Improve failed: {exc}") from exc

    if result.get("status") != "success":
        raise HTTPException(status_code=500, detail=result.get("error", "improve falhou"))

    return ImproveFlyerResponse(
        status="success",
        source=result["source"],
        count=result["count"],
        used_references=result["used_references"],
        variations=[FlyerVariation(path=p, url=_file_url(p)) for p in result["variations"]],
    )


# --------------------------------------------------------------------------- #
# Content flow — generate the copy first (user edits it, then generates image).
# --------------------------------------------------------------------------- #
@router.post("/content/generate", response_model=ContentResponse)
async def generate_content_endpoint(request: GenerateContentRequest) -> ContentResponse:
    """
    Turn a brief into structured, editable copy for a single platform.
    Step 1 of the direct flow: the user reviews/edits this before generating the image.
    """
    try:
        data = generate_content(
            brief=request.brief,
            platform=request.platform.value,
            brand_name=request.brand_name,
            tone=request.tone,
            extra_instructions=request.extra_instructions,
        )
    except Exception as exc:
        logger.error("content_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Content generation failed: {exc}") from exc

    return ContentResponse(**data)


# --------------------------------------------------------------------------- #
# Image flow — generate the flyer from an uploaded reference image + the copy.
# --------------------------------------------------------------------------- #
@router.post("/images/generate", response_model=GenerateImageResponse)
async def generate_image_endpoint(
    reference: UploadFile = File(..., description="Imagem de referência (PNG/JPG/WEBP)."),
    platform: str = Form(default="instagram_feed"),
    headline: str = Form(...),
    subheadline: str = Form(default=""),
    body_copy: str = Form(default=""),
    badge: str = Form(default=""),
    metric: str = Form(default=""),
    call_to_action: str = Form(default=""),
    trust_items: str = Form(default="", description="Itens de confiança separados por '|'."),
    image_prompt: str = Form(default="", description="Direção extra opcional para a cena de fundo."),
    brand_id: str = Form(default="", description="Fallback de logo (só quando apply_logo=true e sem upload)."),
    apply_logo: bool = Form(default=False, description="Aplicar um logo sobre o flyer."),
    logo: UploadFile | None = File(
        default=None, description="Logo enviado pelo usuário (PNG recomendado). Usado quando apply_logo=true."
    ),
    match_reference_colors: bool = Form(
        default=True, description="Compor o texto com as cores amostradas da imagem de referência."
    ),
) -> GenerateImageResponse:
    """
    Generate a flyer directly from an uploaded reference image + the copy
    (GPT-Image style). Step 2 of the direct flow.
    """
    ext = Path(reference.filename or "").suffix.lower()
    if ext not in _ALLOWED_UPLOAD_EXT:
        raise HTTPException(status_code=400, detail=f"Formato não suportado: {ext or 'desconhecido'}")

    output_dir = os.path.abspath(settings.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    ref_path = os.path.join(output_dir, f"ref_{uuid.uuid4().hex[:8]}{ext}")
    with open(ref_path, "wb") as f:
        f.write(await reference.read())

    # Save an uploaded logo, if any, so it (not a stored brand logo) is used.
    logo_path = ""
    if logo is not None and logo.filename:
        lext = Path(logo.filename).suffix.lower()
        if lext not in _ALLOWED_UPLOAD_EXT:
            raise HTTPException(status_code=400, detail=f"Logo em formato não suportado: {lext or 'desconhecido'}")
        logo_path = os.path.join(output_dir, f"logo_{uuid.uuid4().hex[:8]}{lext}")
        with open(logo_path, "wb") as f:
            f.write(await logo.read())

    trust = [t.strip() for t in trust_items.split("|") if t.strip()]

    logger.info("image_gen_started", platform=platform, reference=ref_path, has_logo=bool(logo_path))
    try:
        result = generate_from_reference(
            reference_paths=[ref_path],
            platform_key=platform,
            headline=headline,
            body_copy=body_copy,
            badge=badge,
            metric=metric,
            call_to_action=call_to_action,
            trust_items=trust,
            image_prompt=image_prompt,
            brand_id=brand_id,
            apply_logo=apply_logo,
            logo_path=logo_path,
            match_reference_colors=match_reference_colors,
        )
    except Exception as exc:
        logger.error("image_gen_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Image generation failed: {exc}") from exc

    if result.get("status") != "success":
        raise HTTPException(status_code=500, detail=result.get("error", "image generation falhou"))

    return GenerateImageResponse(
        status="success",
        platform=result["platform"],
        image_path=result["image_path"],
        image_url=_file_url(result["image_path"]),
        size=result["size"],
        used_references=result["used_references"],
        metric_status=result["metric_status"],
        logo_status=result["logo_status"],
        palette_status=result.get("palette_status", ""),
    )


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
