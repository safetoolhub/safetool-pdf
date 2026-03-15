# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.tools.metadata."""

from __future__ import annotations

import threading
from pathlib import Path

import pikepdf
import pytest

from safetool_pdf_core.models import ToolName
from safetool_pdf_core.tools.metadata import execute


class TestMetadataTool:
    """Tests for the metadata stripping tool."""

    def test_strip_metadata_basic(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["with_metadata"]
        results = execute([src], output_dir=tmp_output)
        assert len(results) == 1
        r = results[0]
        assert r.success is True
        assert r.tool == ToolName.STRIP_METADATA
        assert r.output_path is not None
        assert r.output_path.is_file()

    def test_strip_metadata_removes_docinfo(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["with_metadata"]
        results = execute([src], output_dir=tmp_output)
        r = results[0]

        with pikepdf.open(str(r.output_path)) as pdf:
            # DocInfo should be empty or absent
            docinfo = pdf.docinfo
            for key in ["/Title", "/Author", "/Subject", "/Creator", "/Producer"]:
                assert key not in docinfo or str(docinfo.get(key, "")) == ""

    def test_strip_metadata_removes_xmp(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["with_metadata"]
        results = execute([src], output_dir=tmp_output)
        r = results[0]

        with pikepdf.open(str(r.output_path)) as pdf:
            # /Metadata stream should be absent from the root
            assert "/Metadata" not in pdf.Root

    def test_strip_metadata_batch(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        srcs = [generated_pdfs["with_metadata"], generated_pdfs["simple_text"]]
        results = execute(srcs, output_dir=tmp_output)
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_strip_metadata_preserves_content(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        import fitz

        src = generated_pdfs["with_metadata"]
        doc_orig = fitz.open(str(src))
        orig_pages = len(doc_orig)
        doc_orig.close()

        results = execute([src], output_dir=tmp_output)
        doc_result = fitz.open(str(results[0].output_path))
        assert len(doc_result) == orig_pages
        doc_result.close()

    def test_strip_metadata_already_clean(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Stripping metadata from a PDF with no metadata should still succeed."""
        src = generated_pdfs["simple_text"]
        results = execute([src], output_dir=tmp_output)
        assert len(results) == 1
        assert results[0].success is True

    def test_strip_metadata_cancellation(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        cancel = threading.Event()
        cancel.set()
        src = generated_pdfs["with_metadata"]
        results = execute([src], output_dir=tmp_output, cancel=cancel)
        assert len(results) == 1
        assert results[0].success is False
