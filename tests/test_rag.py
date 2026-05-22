"""
Unit tests for RAG stores — no OpenAI calls, no ChromaDB writes.
Uses monkeypatching to isolate the logic under test.
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
import json


# ------------------------------------------------------------------ BrandStore
class TestBrandStoreChunking:
    def test_chunk_text_produces_chunks(self) -> None:
        from rag.brand_store import BrandStore
        text = "word " * 1000
        chunks = BrandStore._chunk_text(text, source="test.txt")
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk["source"] == "test.txt"
            assert "text" in chunk
            assert "index" in chunk

    def test_chunk_text_short_produces_one_chunk(self) -> None:
        from rag.brand_store import BrandStore
        text = "Short brand description."
        chunks = BrandStore._chunk_text(text, source="brief.txt")
        assert len(chunks) == 1
        assert chunks[0]["index"] == 0

    def test_read_txt_file(self, tmp_path: Path) -> None:
        from rag.brand_store import BrandStore
        f = tmp_path / "brand.txt"
        f.write_text("Brand guidelines content.", encoding="utf-8")
        result = BrandStore._read_file(f)
        assert "Brand guidelines" in result

    def test_read_json_file(self, tmp_path: Path) -> None:
        from rag.brand_store import BrandStore
        data = {"name": "TestBrand", "colors": ["#000", "#FFF"]}
        f = tmp_path / "palette.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        result = BrandStore._read_file(f)
        parsed = json.loads(result)
        assert parsed["name"] == "TestBrand"

    def test_read_md_file(self, tmp_path: Path) -> None:
        from rag.brand_store import BrandStore
        f = tmp_path / "guide.md"
        f.write_text("# Brand Guide\nPrimary color: green.", encoding="utf-8")
        result = BrandStore._read_file(f)
        assert "Brand Guide" in result

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        from rag.brand_store import BrandStore
        f = tmp_path / "photo.svg"
        f.write_bytes(b"<svg/>")
        with pytest.raises(ValueError, match="Unsupported"):
            BrandStore._read_file(f)


# ------------------------------------------------------------------ VisualStore
class TestVisualStoreHelpers:
    def test_description_to_text_flattens_dict(self) -> None:
        from rag.visual_store import VisualStore
        desc = {
            "style": "minimalist",
            "mood": "calm",
            "composition": "centered",
            "lighting": "natural",
            "color_palette": ["#FFF", "#000"],
            "typography_feel": "light weight",
            "texture_and_depth": "flat",
            "key_elements": ["white space", "bold type"],
            "prompt_keywords": ["minimalist", "clean", "white"],
        }
        text = VisualStore._description_to_text(desc)
        assert "minimalist" in text
        assert "calm" in text
        assert "#FFF" in text

    def test_mime_type_mapping(self) -> None:
        from rag.visual_store import _mime_type
        assert _mime_type(".png") == "image/png"
        assert _mime_type(".jpg") == "image/jpeg"
        assert _mime_type(".webp") == "image/webp"
        assert _mime_type(".unknown") == "image/jpeg"

    def test_query_returns_empty_when_no_data(self) -> None:
        from rag.visual_store import VisualStore
        import tempfile, os

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("rag.visual_store.chromadb.PersistentClient"),
                patch("rag.visual_store.embedding_functions.OpenAIEmbeddingFunction"),
                patch("rag.visual_store.AsyncOpenAI"),
            ):
                store = VisualStore(persist_dir=tmpdir)
                mock_coll = MagicMock()
                mock_coll.count.return_value = 0
                store._get_collection = MagicMock(return_value=mock_coll)  # type: ignore[method-assign]
                result = store.query("mybrand", "test query")
                assert result == ""


# ------------------------------------------------------------------ Orchestrator RAG node
class TestRagContextNode:
    @pytest.mark.asyncio
    async def test_rag_skipped_without_brand_id(self) -> None:
        from core.orchestrator import run_rag_context
        from core.state import CampaignState, BrandProfile, Platform

        state = CampaignState(
            campaign_id="test",
            brief="Test campaign",
            brand=BrandProfile(name="TestBrand"),
            platforms=[Platform.INSTAGRAM_FEED],
            brand_id="",
        )
        result = await run_rag_context(state)
        assert result == {}

    @pytest.mark.asyncio
    async def test_rag_queries_stores_when_brand_id_provided(self) -> None:
        from core.orchestrator import run_rag_context
        from core.state import CampaignState, BrandProfile, Platform

        state = CampaignState(
            campaign_id="test",
            brief="Eco product launch",
            brand=BrandProfile(name="EcoBrand", tone="sustainable"),
            platforms=[Platform.INSTAGRAM_FEED],
            brand_id="ecobrand",
        )

        with (
            patch("core.orchestrator.brand_store") as mock_bs,
            patch("core.orchestrator.visual_store") as mock_vs,
        ):
            mock_bs.query.return_value = "Brand values: sustainability."
            mock_vs.query.return_value = "Visual DNA: earthy tones."

            result = await run_rag_context(state)

        assert result["brand_rag_context"] == "Brand values: sustainability."
        assert result["visual_rag_context"] == "Visual DNA: earthy tones."
        mock_bs.query.assert_called_once_with("ecobrand", pytest.approx, k=6)  # type: ignore[call-arg]
