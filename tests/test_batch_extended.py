# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Extended batch tests: progress callbacks, cancellation, multi-file edge cases."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from safetool_pdf_core.exceptions import CancellationError
from safetool_pdf_core.models import OptimizeResult, ProgressInfo
from safetool_pdf_core.tools.optimize import optimize_batch
from safetool_pdf_core.tools.optimize.presets import moderate, lossless


class TestBatchProgress:
    """Verify batch progress-callback behaviour."""

    def test_progress_reports_file_index(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Progress callback must report file_index and file_total."""
        events: list[ProgressInfo] = []

        def cb(info: ProgressInfo) -> None:
            events.append(
                ProgressInfo(
                    stage=info.stage,
                    message=info.message,
                    percent=info.percent,
                    file_index=info.file_index,
                    file_total=info.file_total,
                )
            )

        files = [
            generated_pdfs["simple_text"],
            generated_pdfs["mixed_content"],
        ]
        results = optimize_batch(
            files, options=lossless(), output_dir=tmp_output, progress_cb=cb,
        )

        assert len(results) == 2
        # At least one event per file
        indices = {e.file_index for e in events}
        assert 1 in indices
        assert 2 in indices
        # file_total should always equal 2
        assert all(e.file_total == 2 for e in events)


class TestBatchCancellation:
    """Batch processing respects cancellation."""

    def test_cancel_mid_batch(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Setting cancel after first file stops processing."""
        cancel = threading.Event()
        processed: list[Path] = []

        def progress_cb(info: ProgressInfo) -> None:
            if info.file_index == 1 and info.stage == "done":
                cancel.set()

        files = [
            generated_pdfs["simple_text"],
            generated_pdfs["mixed_content"],
            generated_pdfs["large_100pages"],
        ]
        results = optimize_batch(
            files, options=lossless(), output_dir=tmp_output,
            progress_cb=progress_cb, cancel=cancel,
        )

        # At most 1 file completed (cancelled before or during 2nd)
        assert len(results) <= 2

    def test_cancel_before_batch(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Pre-set cancel should return empty results."""
        cancel = threading.Event()
        cancel.set()

        files = [generated_pdfs["simple_text"]]
        results = optimize_batch(
            files, options=lossless(), output_dir=tmp_output, cancel=cancel,
        )
        assert len(results) == 0


class TestBatchMultiFile:
    """Edge cases for multi-file batch processing."""

    def test_many_files(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Batch with 5+ files all succeed."""
        keys = ["simple_text", "mixed_content", "multiple_fonts",
                "with_bookmarks", "large_100pages"]
        files = [generated_pdfs[k] for k in keys]

        results = optimize_batch(files, options=lossless(), output_dir=tmp_output)
        assert len(results) == 5
        for r in results:
            assert r.skipped is False
            assert r.output_path.is_file()

    def test_all_invalid_files(self, tmp_output: Path) -> None:
        """Batch with all invalid files — all skipped."""
        bad1 = tmp_output / "bad1.pdf"
        bad2 = tmp_output / "bad2.pdf"
        bad1.write_text("nope")
        bad2.write_text("nope2")

        results = optimize_batch([bad1, bad2], options=lossless(), output_dir=tmp_output)
        assert len(results) == 2
        assert all(r.skipped for r in results)

    def test_single_file_batch(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Batch with exactly one file behaves identically to optimize()."""
        results = optimize_batch(
            [generated_pdfs["simple_text"]],
            options=lossless(),
            output_dir=tmp_output,
        )
        assert len(results) == 1
        assert results[0].output_path.is_file()
        assert results[0].skipped is False

    def test_empty_list(self, tmp_output: Path) -> None:
        """Batch with zero files returns empty list."""
        results = optimize_batch([], options=lossless(), output_dir=tmp_output)
        assert results == []

    def test_balanced_batch(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Batch with moderate preset (lossy images enabled, GS disabled)."""
        opts = moderate()
        opts.ghostscript.enabled = False

        files = [
            generated_pdfs["large_images"],
            generated_pdfs["png_images"],
        ]
        results = optimize_batch(files, options=opts, output_dir=tmp_output)
        assert len(results) == 2
        for r in results:
            assert r.skipped is False
            assert r.output_path.is_file()
