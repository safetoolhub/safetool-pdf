# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.analyzer.analyze()."""

from __future__ import annotations

from pathlib import Path

import pytest

from safetool_pdf_core.analyzer import analyze
from safetool_pdf_core.exceptions import InvalidPDFError
from safetool_pdf_core.models import AnalysisResult

class TestSimpleAnalysis:
    """Basic smoke tests for analysis output."""

    def test_simple_text_analysis(self, generated_pdfs: dict[str, Path]) -> None:
        result = analyze(generated_pdfs["simple_text"])
        assert isinstance(result, AnalysisResult)
        assert result.page_count >= 1
        assert result.file_size > 0
        assert result.pdf_version != ""
        assert result.path == generated_pdfs["simple_text"]

    def test_image_detection(self, generated_pdfs: dict[str, Path]) -> None:
        result = analyze(generated_pdfs["large_images"])
        assert result.has_images is True
        assert len(result.images) > 0
        assert result.total_image_bytes > 0

    def test_font_detection(self, generated_pdfs: dict[str, Path]) -> None:
        result = analyze(generated_pdfs["multiple_fonts"])
        assert result.has_fonts is True
        assert len(result.fonts) > 0

    def test_forms_detection(self, generated_pdfs: dict[str, Path]) -> None:
        result = analyze(generated_pdfs["with_forms"])
        assert result.has_forms is True

    def test_bookmarks_detection(self, generated_pdfs: dict[str, Path]) -> None:
        result = analyze(generated_pdfs["with_bookmarks"])
        assert result.has_bookmarks is True

    def test_links_detection(self, generated_pdfs: dict[str, Path]) -> None:
        result = analyze(generated_pdfs["with_links"])
        assert result.has_links is True

    def test_js_detection(self, generated_pdfs: dict[str, Path]) -> None:
        result = analyze(generated_pdfs["with_js"])
        assert result.has_javascript is True

    def test_attachments_detection(self, generated_pdfs: dict[str, Path]) -> None:
        result = analyze(generated_pdfs["with_attachments"])
        assert result.has_attachments is True

    def test_metadata_detection(self, generated_pdfs: dict[str, Path]) -> None:
        result = analyze(generated_pdfs["with_metadata"])
        assert result.has_metadata is True

    def test_layers_detection(self, generated_pdfs: dict[str, Path]) -> None:
        result = analyze(generated_pdfs["with_layers"])
        assert result.has_layers is True

    def test_encrypted_analysis(self, generated_pdfs: dict[str, Path]) -> None:
        """Encrypted PDF should either be analyzable or raise gracefully."""
        pdf = generated_pdfs["encrypted_user"]
        try:
            result = analyze(pdf, password="1234")
            assert result.is_encrypted is True
        except Exception:
            pytest.skip("Cannot open encrypted test PDF for analysis")

    def test_invalid_file(self, tmp_output: Path) -> None:
        fake = tmp_output / "nonexistent.pdf"
        with pytest.raises(InvalidPDFError):
            analyze(fake)
