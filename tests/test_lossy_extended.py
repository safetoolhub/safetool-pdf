# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.stages.lossy_images — PyMuPDF rewrite_images.

Validates the dpi_target / dpi_threshold fix (previously used 'resolution' kwarg).
"""

from __future__ import annotations

import shutil
import threading
from pathlib import Path

import pytest

from safetool_pdf_core.exceptions import CancellationError
from safetool_pdf_core.models import LossyImageOptions, ProgressInfo
from safetool_pdf_core.tools.optimize.stages.lossy_images import run_lossy_images


class TestLossyImagesDPIFix:
    """Ensure rewrite_images uses dpi_target/dpi_threshold, not resolution."""

    def test_balanced_settings(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """150 DPI Q80 — typical balanced preset image options."""
        src = generated_pdfs["large_images"]
        out = tmp_output / "balanced_images.pdf"
        opts = LossyImageOptions(enabled=True, target_dpi=150, jpeg_quality=80)

        warnings = run_lossy_images(src, out, opts)
        assert out.is_file()
        assert out.stat().st_size > 0
        # Image-heavy PDF should shrink
        assert out.stat().st_size < src.stat().st_size

    def test_maximum_settings(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """96 DPI Q50 — aggressive maximum preset settings."""
        src = generated_pdfs["large_images"]
        out = tmp_output / "maximum_images.pdf"
        opts = LossyImageOptions(enabled=True, target_dpi=96, jpeg_quality=50)

        warnings = run_lossy_images(src, out, opts)
        assert out.is_file()
        assert out.stat().st_size < src.stat().st_size

    def test_png_images(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """PNG images are also rewritten."""
        src = generated_pdfs["png_images"]
        out = tmp_output / "png_rewrite.pdf"
        opts = LossyImageOptions(enabled=True, target_dpi=150, jpeg_quality=80)

        warnings = run_lossy_images(src, out, opts)
        assert out.is_file()

    def test_high_dpi_no_downscale(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """High target DPI (600) should not upscale or cause errors."""
        src = generated_pdfs["large_images"]
        out = tmp_output / "high_dpi.pdf"
        opts = LossyImageOptions(enabled=True, target_dpi=600, jpeg_quality=95)

        warnings = run_lossy_images(src, out, opts)
        assert out.is_file()

    def test_disabled_copies_file(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Disabled lossy stage simply copies the file."""
        src = generated_pdfs["simple_text"]
        out = tmp_output / "copy.pdf"
        opts = LossyImageOptions(enabled=False)

        warnings = run_lossy_images(src, out, opts)
        assert out.is_file()
        assert out.stat().st_size == src.stat().st_size

    def test_preserves_page_count(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Image rewrite must not change page count."""
        import fitz

        src = generated_pdfs["large_images"]
        out = tmp_output / "pages_ok.pdf"
        opts = LossyImageOptions(enabled=True, target_dpi=150, jpeg_quality=80)

        run_lossy_images(src, out, opts)

        doc_src = fitz.open(str(src))
        doc_out = fitz.open(str(out))
        assert doc_out.page_count == doc_src.page_count
        doc_src.close()
        doc_out.close()

    def test_progress_callback(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Progress callback is invoked during image rewrite."""
        events: list[ProgressInfo] = []

        def cb(info: ProgressInfo) -> None:
            events.append(info)

        src = generated_pdfs["large_images"]
        out = tmp_output / "progress.pdf"
        opts = LossyImageOptions(enabled=True, target_dpi=150, jpeg_quality=80)

        run_lossy_images(src, out, opts, progress_cb=cb)
        assert len(events) > 0
        assert any(e.stage == "lossy_images" for e in events)

    def test_cancellation(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Cancellation in lossy stage raises CancellationError."""
        cancel = threading.Event()
        cancel.set()

        src = generated_pdfs["large_images"]
        out = tmp_output / "cancel.pdf"
        opts = LossyImageOptions(enabled=True, target_dpi=150, jpeg_quality=80)

        with pytest.raises(CancellationError):
            run_lossy_images(src, out, opts, cancel=cancel)
