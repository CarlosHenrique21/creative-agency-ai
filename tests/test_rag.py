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


# ------------------------------------------------------------------ RAG tools
class TestRagTools:
    def test_query_brand_knowledge_skips_without_brand_id(self) -> None:
        from tools.rag_tools import query_brand_knowledge
        from unittest.mock import MagicMock

        ctx = MagicMock()
        ctx.state = {"brand_id": ""}
        result = query_brand_knowledge("test query", ctx)
        assert result == ""

    def test_query_visual_references_skips_without_brand_id(self) -> None:
        from tools.rag_tools import query_visual_references
        from unittest.mock import MagicMock

        ctx = MagicMock()
        ctx.state = {"brand_id": ""}
        result = query_visual_references("visual query", ctx)
        assert result == ""

    def test_query_brand_knowledge_calls_store(self) -> None:
        from tools.rag_tools import query_brand_knowledge
        from unittest.mock import MagicMock

        ctx = MagicMock()
        ctx.state = {"brand_id": "ecobrand"}

        with patch("tools.rag_tools.brand_store") as mock_store:
            mock_store.query.return_value = "Brand knowledge result"
            result = query_brand_knowledge("sustainability values", ctx)

        assert result == "Brand knowledge result"
        mock_store.query.assert_called_once_with("ecobrand", "sustainability values", k=6)
        assert ctx.state["brand_rag_context"] == "Brand knowledge result"
