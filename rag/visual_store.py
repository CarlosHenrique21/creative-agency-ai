"""
RAG store for visual reference images.

Each image is analysed by GPT-4o Vision, which extracts a structured
style description. That description is embedded and stored in ChromaDB.
At query time the Designer retrieves the top-K most relevant descriptions
and injects them as "visual DNA" into the gpt-image-1 prompt.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions
from openai import AsyncOpenAI
import structlog

from core.config import settings

logger = structlog.get_logger()

_SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_VISION_MODEL = "gpt-4o"
_COLLECTION_PREFIX = "visuals_"


def _collection_name(brand_id: str) -> str:
    return f"{_COLLECTION_PREFIX}{brand_id}"


_VISION_SYSTEM = """You are a senior visual art director.
Analyse the provided image and return a JSON object with these exact keys:
{
  "style": "<overall aesthetic — e.g. minimalist, editorial, bold, organic>",
  "color_palette": ["<hex or name>", ...],
  "typography_feel": "<describe font weight, size contrast, spacing feel>",
  "composition": "<layout structure — rule of thirds, centered, asymmetric, etc.>",
  "mood": "<emotional tone — energetic, calm, luxurious, playful, etc.>",
  "key_elements": ["<recurring visual element>", ...],
  "lighting": "<natural, studio, dramatic, flat, etc.>",
  "texture_and_depth": "<flat design, layered, photographic depth, etc.>",
  "prompt_keywords": ["<English keyword for image generation>", ...]
}
Return ONLY valid JSON, no markdown."""


class VisualStore:
    """Per-brand ChromaDB collection for visual reference retrieval."""

    def __init__(self, persist_dir: str = "./chroma_db/visuals") -> None:
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key,
            model_name="text-embedding-3-small",
        )
        self._openai = AsyncOpenAI(api_key=settings.openai_api_key)
        self.log = structlog.get_logger().bind(component="VisualStore")

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    async def ingest_image(self, brand_id: str, file_path: str | Path) -> dict[str, Any]:
        """Analyse an image with Vision, embed the description, upsert into store."""
        path = Path(file_path)
        if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported image type: {path.suffix}")

        description = await self._describe_image(path)
        self.log.info("image_described", brand_id=brand_id, file=path.name)

        collection = self._get_collection(brand_id)
        doc_id = f"{brand_id}_{path.stem}"
        text_repr = self._description_to_text(description)

        collection.upsert(
            ids=[doc_id],
            documents=[text_repr],
            metadatas=[{
                "source": path.name,
                "brand_id": brand_id,
                "style": description.get("style", ""),
                "mood": description.get("mood", ""),
                "prompt_keywords": json.dumps(description.get("prompt_keywords", [])),
            }],
        )
        return description

    async def ingest_directory(
        self, brand_id: str, directory: str | Path
    ) -> dict[str, dict[str, Any]]:
        """Analyse and ingest all images in a directory."""
        results: dict[str, dict[str, Any]] = {}
        for file in Path(directory).iterdir():
            if file.is_file() and file.suffix.lower() in _SUPPORTED_EXTENSIONS:
                try:
                    results[file.name] = await self.ingest_image(brand_id, file)
                except Exception as exc:
                    self.log.error("visual_ingest_failed", file=file.name, error=str(exc))
        return results

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def query(self, brand_id: str, context: str, k: int = 3) -> str:
        """
        Return a synthesised visual style guide string derived from the
        top-K reference images most semantically close to `context`.
        Ready to be injected into gpt-image-1 prompts.
        """
        collection = self._get_collection(brand_id)
        count = collection.count()
        if count == 0:
            return ""

        results = collection.query(
            query_texts=[context],
            n_results=min(k, count),
            include=["documents", "metadatas"],
        )
        docs: list[str] = results.get("documents", [[]])[0]
        metas: list[dict[str, Any]] = results.get("metadatas", [[]])[0]

        style_notes: list[str] = []
        all_keywords: list[str] = []

        for doc, meta in zip(docs, metas):
            style_notes.append(
                f"Reference '{meta.get('source', '?')}': {meta.get('style', '')} / "
                f"{meta.get('mood', '')} mood"
            )
            keywords = json.loads(meta.get("prompt_keywords", "[]"))
            all_keywords.extend(keywords)

        # Deduplicate keywords preserving order
        seen: set[str] = set()
        unique_keywords = [kw for kw in all_keywords if not (kw in seen or seen.add(kw))]  # type: ignore[func-returns-value]

        guide_lines = [
            "=== VISUAL STYLE GUIDE (from brand reference images) ===",
            "\n".join(f"• {note}" for note in style_notes),
            f"Key visual keywords: {', '.join(unique_keywords[:20])}",
            "Match this visual DNA when composing the flyer.",
        ]
        return "\n".join(guide_lines)

    def list_images(self, brand_id: str) -> list[str]:
        collection = self._get_collection(brand_id)
        results = collection.get(include=["metadatas"])
        sources = [m["source"] for m in results.get("metadatas", []) if m]
        return sorted(sources)

    def delete_brand(self, brand_id: str) -> None:
        try:
            self._client.delete_collection(_collection_name(brand_id))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_collection(self, brand_id: str) -> chromadb.Collection:
        return self._client.get_or_create_collection(
            name=_collection_name(brand_id),
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )

    async def _describe_image(self, path: Path) -> dict[str, Any]:
        b64 = base64.b64encode(path.read_bytes()).decode()
        mime = _mime_type(path.suffix)

        response = await self._openai.chat.completions.create(
            model=_VISION_MODEL,
            messages=[
                {"role": "system", "content": _VISION_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"},
                        },
                        {"type": "text", "text": "Analyse this brand reference image."},
                    ],
                },
            ],
            temperature=0.2,
        )
        raw = response.choices[0].message.content or "{}"
        # Strip markdown code fences if model wraps JSON
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw)

    @staticmethod
    def _description_to_text(desc: dict[str, Any]) -> str:
        """Flatten description dict to a single string for embedding."""
        parts = [
            f"Style: {desc.get('style', '')}",
            f"Mood: {desc.get('mood', '')}",
            f"Composition: {desc.get('composition', '')}",
            f"Lighting: {desc.get('lighting', '')}",
            f"Colors: {', '.join(desc.get('color_palette', []))}",
            f"Typography feel: {desc.get('typography_feel', '')}",
            f"Texture/depth: {desc.get('texture_and_depth', '')}",
            f"Key elements: {', '.join(desc.get('key_elements', []))}",
            f"Prompt keywords: {', '.join(desc.get('prompt_keywords', []))}",
        ]
        return " | ".join(parts)


def _mime_type(suffix: str) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(suffix.lower(), "image/jpeg")
