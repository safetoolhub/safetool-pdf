# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.stages.lossless."""

from __future__ import annotations

import threading
from pathlib import Path

import fitz
import pytest

from safetool_pdf_core.exceptions import CancellationError
from safetool_pdf_core.models import LosslessOptions
from safetool_pdf_core.tools.optimize.stages.lossless import run_lossless

class TestLosslessStage:
    """Tests for the lossless (pikepdf) optimization stage."""

    def test_lossless_simple(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["simple_text"]
        dst = tmp_output / "simple_lossless.pdf"
        warnings = run_lossless(src, dst, LosslessOptions())
        assert dst.is_file()
        assert dst.stat().st_size > 0
        # Lossless output should be <= original (or at worst very close)
        assert dst.stat().st_size <= src.stat().st_size * 1.05
        assert isinstance(warnings, list)

    def test_lossless_uncompressed(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["uncompressed"]
        dst = tmp_output / "uncompressed_lossless.pdf"
        run_lossless(src, dst, LosslessOptions())
        assert dst.is_file()
        # Uncompressed PDF should get noticeably smaller
        assert dst.stat().st_size < src.stat().st_size

    def test_lossless_preserves_pages(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["simple_text"]
        dst = tmp_output / "pages_check.pdf"
        run_lossless(src, dst, LosslessOptions())

        doc_src = fitz.open(str(src))
        doc_dst = fitz.open(str(dst))
        try:
            assert doc_dst.page_count == doc_src.page_count
        finally:
            doc_src.close()
            doc_dst.close()

    def test_lossless_cancellation(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["simple_text"]
        dst = tmp_output / "cancelled.pdf"
        cancel = threading.Event()
        cancel.set()  # already cancelled
        with pytest.raises(CancellationError):
            run_lossless(src, dst, LosslessOptions(), cancel=cancel)
