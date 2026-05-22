"""
Endpoints for ingesting brand documents and visual references into the RAG stores.

Brand docs  → POST /api/v1/brands/{brand_id}/ingest/docs
Visual refs → POST /api/v1/brands/{brand_id}/ingest/images
List files  → GET  /api/v1/brands/{brand_id}/assets
Delete      → DELETE /api/v1/brands/{brand_id}
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File
from pathlib import Path
import tempfile
import aiofiles

from rag.dependencies import brand_store, visual_store
import structlog

router = APIRouter(prefix="/api/v1/brands", tags=["brand-rag"])
logger = structlog.get_logger()

_DOC_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".json"}
_IMG_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@router.post("/{brand_id}/ingest/docs")
async def ingest_brand_docs(
    brand_id: str,
    files: list[UploadFile] = File(...),
) -> dict:
    """
    Upload one or more brand documents (PDF, DOCX, TXT, MD, JSON).
    They are chunked, embedded and stored in ChromaDB under this brand_id.
    """
    results: dict[str, int] = {}
    errors: dict[str, str] = {}

    for upload in files:
        filename = upload.filename or "unknown"
        suffix = Path(filename).suffix.lower()

        if suffix not in _DOC_EXTENSIONS:
            errors[filename] = f"Unsupported type '{suffix}'. Allowed: {sorted(_DOC_EXTENSIONS)}"
            continue

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)

        async with aiofiles.open(tmp_path, "wb") as f:
            await f.write(await upload.read())

        try:
            chunks = brand_store.ingest_file(brand_id, tmp_path)
            results[filename] = chunks
        except Exception as exc:
            errors[filename] = str(exc)
            logger.error("doc_ingest_failed", brand_id=brand_id, file=filename, error=str(exc))
        finally:
            tmp_path.unlink(missing_ok=True)

    if not results and errors:
        raise HTTPException(status_code=422, detail=errors)

    return {
        "brand_id": brand_id,
        "ingested": results,
        "errors": errors,
        "total_chunks": sum(results.values()),
    }


@router.post("/{brand_id}/ingest/images")
async def ingest_visual_refs(
    brand_id: str,
    files: list[UploadFile] = File(...),
) -> dict:
    """
    Upload one or more reference images (JPG, PNG, WEBP, GIF).
    Each image is analysed by GPT-4o Vision, which extracts a structured
    style description that is embedded and stored in ChromaDB.
    """
    results: dict[str, dict] = {}
    errors: dict[str, str] = {}

    for upload in files:
        filename = upload.filename or "unknown"
        suffix = Path(filename).suffix.lower()

        if suffix not in _IMG_EXTENSIONS:
            errors[filename] = f"Unsupported type '{suffix}'. Allowed: {sorted(_IMG_EXTENSIONS)}"
            continue

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)

        async with aiofiles.open(tmp_path, "wb") as f:
            await f.write(await upload.read())

        try:
            description = await visual_store.ingest_image(brand_id, tmp_path)
            results[filename] = description
        except Exception as exc:
            errors[filename] = str(exc)
            logger.error("image_ingest_failed", brand_id=brand_id, file=filename, error=str(exc))
        finally:
            tmp_path.unlink(missing_ok=True)

    if not results and errors:
        raise HTTPException(status_code=422, detail=errors)

    return {
        "brand_id": brand_id,
        "ingested": list(results.keys()),
        "descriptions": results,
        "errors": errors,
    }


@router.get("/{brand_id}/assets")
async def list_brand_assets(brand_id: str) -> dict:
    """List all documents and images ingested for a brand."""
    return {
        "brand_id": brand_id,
        "documents": brand_store.list_files(brand_id),
        "images": visual_store.list_images(brand_id),
    }


@router.delete("/{brand_id}")
async def delete_brand(brand_id: str) -> dict:
    """Remove all RAG data for a brand (both documents and images)."""
    brand_store.delete_brand(brand_id)
    visual_store.delete_brand(brand_id)
    return {"brand_id": brand_id, "deleted": True}
