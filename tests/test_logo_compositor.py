"""Tests for the logo compositor — no OpenAI calls, no filesystem side-effects."""
import base64
import io
import pytest
from pathlib import Path
from PIL import Image
from unittest.mock import patch


def _make_b64_image(width: int = 100, height: int = 100, color: str = "blue") -> str:
    img = Image.new("RGBA", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _make_logo_file(tmp_path: Path, name: str = "testbrand.png") -> Path:
    logo = Image.new("RGBA", (200, 100), (255, 0, 0, 200))
    path = tmp_path / name
    logo.save(path, format="PNG")
    return path


class TestFindLogo:
    def test_returns_none_when_no_logo(self, tmp_path: Path) -> None:
        from rag.logo_compositor import find_logo, _LOGO_DIR
        with patch("rag.logo_compositor._LOGO_DIR", tmp_path):
            result = find_logo("nonexistent_brand")
        assert result is None

    def test_finds_brand_specific_logo(self, tmp_path: Path) -> None:
        from rag.logo_compositor import find_logo
        logo_path = _make_logo_file(tmp_path, "mybrand.png")
        with patch("rag.logo_compositor._LOGO_DIR", tmp_path):
            result = find_logo("mybrand")
        assert result == logo_path

    def test_falls_back_to_default_logo(self, tmp_path: Path) -> None:
        from rag.logo_compositor import find_logo
        default_path = _make_logo_file(tmp_path, "default.png")
        with patch("rag.logo_compositor._LOGO_DIR", tmp_path):
            result = find_logo("some_other_brand")
        assert result == default_path

    def test_brand_specific_takes_priority_over_default(self, tmp_path: Path) -> None:
        from rag.logo_compositor import find_logo
        _make_logo_file(tmp_path, "default.png")
        brand_path = _make_logo_file(tmp_path, "mybrand.png")
        with patch("rag.logo_compositor._LOGO_DIR", tmp_path):
            result = find_logo("mybrand")
        assert result == brand_path


class TestCompositor:
    def test_returns_original_when_no_logo(self) -> None:
        from rag.logo_compositor import composite_logo
        original = _make_b64_image()
        with patch("rag.logo_compositor.find_logo", return_value=None):
            result = composite_logo(original, "nobrand", "instagram_feed")
        assert result == original

    def test_composites_logo_onto_flyer(self, tmp_path: Path) -> None:
        from rag.logo_compositor import composite_logo
        logo_path = _make_logo_file(tmp_path)
        flyer_b64 = _make_b64_image(500, 500)

        with patch("rag.logo_compositor.find_logo", return_value=logo_path):
            result = composite_logo(flyer_b64, "testbrand", "instagram_feed")

        # Result should be valid base64 PNG and differ from the original
        result_bytes = base64.b64decode(result)
        img = Image.open(io.BytesIO(result_bytes))
        assert img.size == (500, 500)
        assert result != flyer_b64

    def test_all_platform_placements_succeed(self, tmp_path: Path) -> None:
        from rag.logo_compositor import composite_logo
        logo_path = _make_logo_file(tmp_path)
        platforms = [
            ("instagram_feed", 500, 500),
            ("instagram_story", 300, 533),
            ("linkedin_post", 600, 314),
            ("linkedin_banner", 792, 198),
        ]
        for platform, w, h in platforms:
            flyer_b64 = _make_b64_image(w, h)
            with patch("rag.logo_compositor.find_logo", return_value=logo_path):
                result = composite_logo(flyer_b64, "testbrand", platform)
            result_bytes = base64.b64decode(result)
            img = Image.open(io.BytesIO(result_bytes))
            assert img.size == (w, h), f"Size changed for {platform}"


class TestResizeAndPosition:
    def test_resize_logo_scales_to_fraction(self) -> None:
        from rag.logo_compositor import _resize_logo
        logo = Image.new("RGBA", (400, 200))
        resized = _resize_logo(logo, fw=1080, fh=1080, scale=0.18)
        expected_w = int(1080 * 0.18)
        assert resized.width == expected_w

    def test_compute_position_bottom_right(self) -> None:
        from rag.logo_compositor import _compute_position
        x, y = _compute_position(1080, 1080, 200, 100, 40, "bottom_right")
        assert x == 1080 - 200 - 40
        assert y == 1080 - 100 - 40

    def test_compute_position_top_center(self) -> None:
        from rag.logo_compositor import _compute_position
        x, y = _compute_position(1080, 1920, 200, 100, 40, "top_center")
        assert x == (1080 - 200) // 2
        assert y == 40
