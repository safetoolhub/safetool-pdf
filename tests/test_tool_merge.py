# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.tools.merge."""

from __future__ import annotations

import threading
from pathlib import Path

import fitz
import pytest

from safetool_pdf_core.models import ToolName
from safetool_pdf_core.tools.merge import execute


class TestMergeTool:
    """Tests for the PDF merge tool."""

    def test_merge_two_files(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src_a = generated_pdfs["simple_text"]
        src_b = generated_pdfs["multiple_fonts"]
        results = execute([src_a, src_b], output_dir=tmp_output)

        assert len(results) == 1
        r = results[0]
        assert r.success is True
        assert r.tool == ToolName.MERGE
        assert r.output_path is not None
        assert r.output_path.is_file()

        doc = fitz.open(str(r.output_path))
        doc_a = fitz.open(str(src_a))
        doc_b = fitz.open(str(src_b))
        assert len(doc) == len(doc_a) + len(doc_b)
        doc.close()
        doc_a.close()
        doc_b.close()

    def test_merge_three_files(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        srcs = [
            generated_pdfs["simple_text"],
            generated_pdfs["multiple_fonts"],
            generated_pdfs["with_bookmarks"],
        ]
        results = execute(srcs, output_dir=tmp_output)
        assert len(results) == 1
        assert results[0].success is True

        doc = fitz.open(str(results[0].output_path))
        expected_pages = sum(len(fitz.open(str(s))) for s in srcs)
        assert len(doc) == expected_pages
        doc.close()

    def test_merge_requires_two_files(self, generated_pdfs: dict[str, Path], tmp_output: Path) -> None:
        src = generated_pdfs["simple_text"]
        results = execute([src], output_dir=tmp_output)
        assert len(results) == 1
        assert results[0].success is False

    def test_merge_output_filename(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src_a = generated_pdfs["simple_text"]
        src_b = generated_pdfs["multiple_fonts"]
        results = execute([src_a, src_b], output_dir=tmp_output, output_suffix="_merged")
        r = results[0]
        assert r.output_path is not None
        assert "_merged" in r.output_path.name

    def test_merge_cancellation(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        cancel = threading.Event()
        cancel.set()  # pre-cancel
        src_a = generated_pdfs["simple_text"]
        src_b = generated_pdfs["multiple_fonts"]
        results = execute([src_a, src_b], output_dir=tmp_output, cancel=cancel)
        assert len(results) == 1
        assert results[0].success is False

    def test_merge_page_count_recorded(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src_a = generated_pdfs["simple_text"]
        src_b = generated_pdfs["multiple_fonts"]
        results = execute([src_a, src_b], output_dir=tmp_output)
        r = results[0]
        assert r.page_count > 0
