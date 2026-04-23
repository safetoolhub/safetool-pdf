# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.stages.cleanup — selective removal / flattening."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from safetool_pdf_core.models import CleanupOptions
from safetool_pdf_core.tools.optimize.stages.cleanup import run_cleanup


class TestCleanupStage:
    """Tests for the cleanup stage."""

    def test_no_cleanup_copies_file(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """With all cleanup toggles off, file is just copied."""
        src = generated_pdfs["simple_text"]
        out = tmp_output / "out.pdf"
        opts = CleanupOptions()  # all False

        warnings = run_cleanup(src, out, opts)
        assert out.is_file()
        assert out.stat().st_size == src.stat().st_size
        assert warnings == []

    def test_remove_metadata(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Remove metadata from a PDF that has XMP metadata."""
        src = generated_pdfs["with_metadata"]
        out = tmp_output / "no_meta.pdf"
        opts = CleanupOptions(remove_metadata=True)

        warnings = run_cleanup(src, out, opts)
        assert out.is_file()
        assert out.stat().st_size > 0

    def test_remove_attachments(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Remove embedded attachments."""
        src = generated_pdfs["with_attachments"]
        out = tmp_output / "no_attach.pdf"
        opts = CleanupOptions(remove_attachments=True)

        warnings = run_cleanup(src, out, opts)
        assert out.is_file()

        # Verify attachments are gone
        import pikepdf
        pdf = pikepdf.open(str(out))
        root = pdf.Root
        if "/Names" in root:
            names = root["/Names"]
            assert "/EmbeddedFiles" not in names
        pdf.close()

    def test_remove_javascript(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Remove JavaScript from PDF."""
        src = generated_pdfs["with_js"]
        out = tmp_output / "no_js.pdf"
        opts = CleanupOptions(remove_javascript=True)

        warnings = run_cleanup(src, out, opts)
        assert out.is_file()

    def test_remove_thumbnails(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Remove page thumbnails."""
        src = generated_pdfs["with_thumbnails"]
        out = tmp_output / "no_thumbs.pdf"
        opts = CleanupOptions(remove_thumbnails=True)

        warnings = run_cleanup(src, out, opts)
        assert out.is_file()

    def test_remove_bookmarks(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Remove bookmarks/outline."""
        src = generated_pdfs["with_bookmarks"]
        out = tmp_output / "no_bookmarks.pdf"
        opts = CleanupOptions(remove_bookmarks=True)

        warnings = run_cleanup(src, out, opts)
        assert out.is_file()

        import pikepdf
        pdf = pikepdf.open(str(out))
        assert "/Outlines" not in pdf.Root
        pdf.close()

    def test_flatten_forms(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Flatten form fields."""
        src = generated_pdfs["with_forms"]
        out = tmp_output / "flat_forms.pdf"
        opts = CleanupOptions(flatten_forms=True)

        warnings = run_cleanup(src, out, opts)
        assert out.is_file()

    def test_flatten_layers(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Remove OCG layer definitions."""
        src = generated_pdfs["with_layers"]
        out = tmp_output / "no_layers.pdf"
        opts = CleanupOptions(flatten_layers=True)

        warnings = run_cleanup(src, out, opts)
        assert out.is_file()

        import pikepdf
        pdf = pikepdf.open(str(out))
        assert "/OCProperties" not in pdf.Root
        pdf.close()

    def test_multiple_cleanup_ops(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Combine several cleanup options at once."""
        src = generated_pdfs["with_metadata"]
        out = tmp_output / "multi_cleanup.pdf"
        opts = CleanupOptions(
            remove_metadata=True,
            remove_thumbnails=True,
            remove_javascript=True,
        )

        warnings = run_cleanup(src, out, opts)
        assert out.is_file()
        assert out.stat().st_size > 0

    def test_cancellation(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Cleanup respects cancellation."""
        import threading
        from safetool_pdf_core.exceptions import CancellationError

        cancel = threading.Event()
        cancel.set()

        src = generated_pdfs["with_metadata"]
        out = tmp_output / "cancelled.pdf"
        opts = CleanupOptions(remove_metadata=True)

        with pytest.raises(CancellationError):
            run_cleanup(src, out, opts, cancel=cancel)
