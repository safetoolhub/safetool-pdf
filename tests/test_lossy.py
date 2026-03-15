# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.stages.lossy_images."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from safetool_pdf_core.models import LossyImageOptions
from safetool_pdf_core.tools.optimize.stages.lossy_images import run_lossy_images

class TestLossyImagesStage:
    """Tests for the lossy image (PyMuPDF) optimization stage."""

    def test_lossy_disabled_copies(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """When lossy is disabled the output should be a copy of the same size."""
        src = generated_pdfs["simple_text"]
        dst = tmp_output / "disabled_copy.pdf"
        opts = LossyImageOptions(enabled=False)
        run_lossy_images(src, dst, opts)
        assert dst.is_file()
        assert dst.stat().st_size == src.stat().st_size

    def test_lossy_reduces_images(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Image-heavy PDF should get smaller with lossy image rewriting."""
        src = generated_pdfs["large_images"]
        dst = tmp_output / "lossy_images.pdf"
        opts = LossyImageOptions(enabled=True, target_dpi=96, jpeg_quality=50)
        run_lossy_images(src, dst, opts)
        assert dst.is_file()
        assert dst.stat().st_size > 0
        # Should be noticeably smaller for image-heavy content
        assert dst.stat().st_size < src.stat().st_size

    def test_lossy_preserves_pages(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["large_images"]
        dst = tmp_output / "lossy_pages.pdf"
        opts = LossyImageOptions(enabled=True, target_dpi=150, jpeg_quality=80)
        run_lossy_images(src, dst, opts)

        doc_src = fitz.open(str(src))
        doc_dst = fitz.open(str(dst))
        try:
            assert doc_dst.page_count == doc_src.page_count
        finally:
            doc_src.close()
            doc_dst.close()
