# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.optimizer.optimize_batch."""

from __future__ import annotations

from pathlib import Path

import pytest

from safetool_pdf_core.tools.optimize import optimize_batch
from safetool_pdf_core.tools.optimize.presets import lossless

class TestBatchOptimization:
    """Tests for batch optimization of multiple files."""

    def test_batch_multiple_files(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Batch processing of several valid PDFs should produce results
        for each file."""
        files = [
            generated_pdfs["simple_text"],
            generated_pdfs["mixed_content"],
        ]
        opts = lossless()
        results = optimize_batch(files, options=opts, output_dir=tmp_output)

        assert len(results) == len(files)
        for r in results:
            if not r.skipped:
                assert r.output_path.is_file()
                assert r.optimized_size > 0

    def test_batch_with_error(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Batch should continue after an error on one file."""
        bogus = tmp_output / "bogus.pdf"
        bogus.write_text("not a pdf")

        files = [
            bogus,
            generated_pdfs["simple_text"],
        ]
        opts = lossless()
        results = optimize_batch(files, options=opts, output_dir=tmp_output)

        assert len(results) == 2
        # First file should be skipped/errored
        assert results[0].skipped is True
        # Second file should succeed
        assert results[1].skipped is False
        assert results[1].output_path.is_file()
