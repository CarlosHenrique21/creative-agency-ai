"""
RAG store for brand documents.

Ingests PDF / DOCX / TXT / MD / JSON files, chunks them, embeds with
text-embedding-3-small and persists in a per-brand ChromaDB collection.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions
import structlog

from core.config import settings

logger = structlog.get_logger()

_SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".json"}
_CHUNK_SIZE = 800       # tokens (approx chars / 4)
_CHUNK_OVERLAP = 120


def _collection_name(brand_id: str) -> str:
    return f"brand_{brand_id}"


class BrandStore:
    """Per-brand ChromaDB collection for brand document retrieval."""

    def __init__(self, persist_dir: str = "./chroma_db/brands") -> None:
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key,
            model_name="text-embedding-3-small",
        )
        self.log = structlog.get_logger().bind(component="BrandStore")

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_file(self, brand_id: str, file_path: str | Path) -> int:
        """Parse, chunk and upsert a single file. Returns number of chunks added."""
        path = Path(file_path)
        if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        text = self._read_file(path)
        chunks = self._chunk_text(text, source=path.name)

        collection = self._get_collection(brand_id)
        ids = [f"{path.stem}_{i}" for i in range(len(chunks))]
        docs = [c["text"] for c in chunks]
        metas = [{"source": c["source"], "chunk_index": c["index"]} for c in chunks]

        collection.upsert(ids=ids, documents=docs, metadatas=metas)
        self.log.info("brand_docs_ingested", brand_id=brand_id, file=path.name, chunks=len(chunks))
        return len(chunks)

    def ingest_directory(self, brand_id: str, directory: str | Path) -> dict[str, int]:
        """Ingest all supported files in a directory. Returns {filename: chunk_count}."""
        results: dict[str, int] = {}
        for file in Path(directory).iterdir():
            if file.is_file() and file.suffix.lower() in _SUPPORTED_EXTENSIONS:
                try:
                    results[file.name] = self.ingest_file(brand_id, file)
                except Exception as exc:
                    self.log.error("ingest_failed", file=file.name, error=str(exc))
        return results

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def query(self, brand_id: str, question: str, k: int = 5) -> str:
        """Return the top-k relevant chunks as a single concatenated string."""
        collection = self._get_collection(brand_id)
        count = collection.count()
        if count == 0:
            return ""

        results = collection.query(
            query_texts=[question],
            n_results=min(k, count),
            include=["documents", "metadatas"],
        )
        docs: list[str] = results.get("documents", [[]])[0]
        metas: list[dict[str, Any]] = results.get("metadatas", [[]])[0]

        parts = []
        for doc, meta in zip(docs, metas):
            parts.append(f"[{meta.get('source', '?')}]\n{doc}")

        return "\n\n---\n\n".join(parts)

    def list_files(self, brand_id: str) -> list[str]:
        collection = self._get_collection(brand_id)
        results = collection.get(include=["metadatas"])
        sources = {m["source"] for m in results.get("metadatas", []) if m}
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

    @staticmethod
    def _read_file(path: Path) -> str:
        suffix = path.suffix.lower()

        if suffix in (".txt", ".md"):
            return path.read_text(encoding="utf-8")

        if suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            return json.dumps(data, ensure_ascii=False, indent=2)

        if suffix == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)

        if suffix == ".docx":
            from docx import Document  # type: ignore[import]
            doc = Document(str(path))
            return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

        raise ValueError(f"Unhandled suffix: {suffix}")

    @staticmethod
    def _chunk_text(text: str, source: str) -> list[dict[str, Any]]:
        """Simple character-based chunking with overlap."""
        # Approximate tokens → chars (1 token ≈ 4 chars)
        size = _CHUNK_SIZE * 4
        overlap = _CHUNK_OVERLAP * 4

        chunks: list[dict[str, Any]] = []
        start = 0
        idx = 0
        while start < len(text):
            end = start + size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append({"text": chunk, "source": source, "index": idx})
                idx += 1
            start += size - overlap

        return chunks
