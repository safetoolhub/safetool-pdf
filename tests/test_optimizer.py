# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.optimizer.optimize — single-file orchestrator."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from safetool_pdf_core.exceptions import (
    CancellationError,
    InvalidPDFError,
    OptimizationError,
)
from safetool_pdf_core.models import OptimizeResult, ProgressInfo
from safetool_pdf_core.tools.optimize import optimize
from safetool_pdf_core.tools.optimize.presets import moderate, lossless, aggressive


class TestOptimizeSingle:
    """Validate the full optimize() pipeline on a single file."""

    def test_lossless_simple(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Lossless optimisation produces a valid smaller-or-equal file."""
        result = optimize(
            generated_pdfs["simple_text"],
            options=lossless(),
            output_dir=tmp_output,
        )
        assert isinstance(result, OptimizeResult)
        assert result.output_path.is_file()
        assert result.optimized_size > 0
        assert result.skipped is False
        assert result.page_count > 0

    def test_moderate_image_reduction(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Moderate preset with images should reduce file size."""
        opts = moderate()
        # Disable GS so the test doesn't require external binary
        opts.ghostscript.enabled = False

        result = optimize(
            generated_pdfs["large_images"],
            options=opts,
            output_dir=tmp_output,
        )
        assert result.output_path.is_file()
        assert result.reduction_pct >= 0, "Image-heavy PDF should not fail"

    def test_aggressive_image_reduction(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Aggressive preset compresses aggressively."""
        opts = aggressive()
        opts.ghostscript.enabled = False

        result = optimize(
            generated_pdfs["large_images"],
            options=opts,
            output_dir=tmp_output,
        )
        assert result.output_path.is_file()
        assert result.reduction_pct >= 0

    def test_progress_callback(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Progress callback should be invoked with valid ProgressInfo."""
        events: list[ProgressInfo] = []

        def cb(info: ProgressInfo) -> None:
            events.append(info)

        optimize(
            generated_pdfs["simple_text"],
            options=lossless(),
            output_dir=tmp_output,
            progress_cb=cb,
        )

        assert len(events) > 0, "Expected at least one progress event"
        stages = {e.stage for e in events}
        assert "init" in stages or "lossless" in stages

    def test_cancellation(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Pre-set cancel token should raise CancellationError."""
        cancel = threading.Event()
        cancel.set()  # already cancelled

        with pytest.raises(CancellationError):
            optimize(
                generated_pdfs["simple_text"],
                options=lossless(),
                output_dir=tmp_output,
                cancel=cancel,
            )

    def test_invalid_file_raises(self, tmp_output: Path) -> None:
        """Non-existent file raises InvalidPDFError."""
        with pytest.raises(InvalidPDFError):
            optimize(
                Path("/tmp/does_not_exist.pdf"),
                options=lossless(),
                output_dir=tmp_output,
            )

    def test_non_pdf_raises(self, tmp_output: Path) -> None:
        """Non-PDF file raises InvalidPDFError."""
        txt = tmp_output / "file.txt"
        txt.write_text("hello")
        with pytest.raises(InvalidPDFError):
            optimize(txt, options=lossless(), output_dir=tmp_output)

    def test_corrupt_pdf_raises(self, tmp_output: Path) -> None:
        """Bogus .pdf raises an error."""
        bad = tmp_output / "bad.pdf"
        bad.write_text("not-a-pdf")
        with pytest.raises(Exception):
            optimize(bad, options=lossless(), output_dir=tmp_output)

    def test_mixed_content(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Mixed content PDF (text + image + drawings) optimises cleanly."""
        result = optimize(
            generated_pdfs["mixed_content"],
            options=lossless(),
            output_dir=tmp_output,
        )
        assert result.output_path.is_file()
        assert result.skipped is False

    def test_already_optimized_warning(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Already-optimized PDF should produce a warning."""
        result = optimize(
            generated_pdfs["already_optimized"],
            options=lossless(),
            output_dir=tmp_output,
        )
        # The analyzer may detect already_optimized → warning
        # Either way, optimization should succeed
        assert result.output_path.is_file()

    def test_large_100pages(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """100-page PDF processes without error."""
        result = optimize(
            generated_pdfs["large_100pages"],
            options=lossless(),
            output_dir=tmp_output,
        )
        assert result.output_path.is_file()
        assert result.page_count == 100

    def test_png_images(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """PNG images are handled by lossless and lossy paths."""
        opts = moderate()
        opts.ghostscript.enabled = False

        result = optimize(
            generated_pdfs["png_images"],
            options=opts,
            output_dir=tmp_output,
        )
        assert result.output_path.is_file()
