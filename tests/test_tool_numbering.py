# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.tools.numbering."""

from __future__ import annotations

import threading
from pathlib import Path

import fitz
import pytest

from safetool_pdf_core.models import ToolName
from safetool_pdf_core.tools.numbering import execute


class TestNumberingTool:
    """Tests for the PDF numbering tool."""

    def test_number_single_file(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["simple_text"]
        results = execute([src], output_dir=tmp_output)
        assert len(results) == 1
        r = results[0]
        assert r.success is True
        assert r.tool == ToolName.NUMBER
        assert r.output_path is not None
        assert r.output_path.is_file()

    def test_number_stamps_text_on_first_page(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["simple_text"]
        results = execute([src], output_dir=tmp_output, start_number=42)
        r = results[0]
        doc = fitz.open(str(r.output_path))
        first_page_text = doc[0].get_text()
        assert "42" in first_page_text
        doc.close()

    def test_number_batch_correlative(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        srcs = [
            generated_pdfs["simple_text"],
            generated_pdfs["multiple_fonts"],
            generated_pdfs["with_bookmarks"],
        ]
        results = execute(srcs, output_dir=tmp_output, start_number=1)
        assert len(results) == 3
        for i, r in enumerate(results):
            assert r.success is True
            doc = fitz.open(str(r.output_path))
            first_page_text = doc[0].get_text()
            assert str(i + 1) in first_page_text
            doc.close()

    def test_number_preserves_page_count(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["with_bookmarks"]
        doc_orig = fitz.open(str(src))
        orig_pages = len(doc_orig)
        doc_orig.close()

        results = execute([src], output_dir=tmp_output)
        doc_result = fitz.open(str(results[0].output_path))
        assert len(doc_result) == orig_pages
        doc_result.close()

    def test_number_custom_start(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        srcs = [generated_pdfs["simple_text"], generated_pdfs["multiple_fonts"]]
        results = execute(srcs, output_dir=tmp_output, start_number=10)
        assert len(results) == 2

        doc1 = fitz.open(str(results[0].output_path))
        assert "10" in doc1[0].get_text()
        doc1.close()

        doc2 = fitz.open(str(results[1].output_path))
        assert "11" in doc2[0].get_text()
        doc2.close()

    def test_number_cancellation(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        cancel = threading.Event()
        cancel.set()
        src = generated_pdfs["simple_text"]
        results = execute([src], output_dir=tmp_output, cancel=cancel)
        assert len(results) == 1
        assert results[0].success is False

    def test_number_output_suffix(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["simple_text"]
        results = execute([src], output_dir=tmp_output, output_suffix="_numbered")
        assert results[0].output_path is not None
        assert "_numbered" in results[0].output_path.name
