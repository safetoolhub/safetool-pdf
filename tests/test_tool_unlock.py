# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.tools.unlock."""

from __future__ import annotations

import threading
from pathlib import Path

import fitz
import pikepdf
import pytest

from safetool_pdf_core.models import ToolName
from safetool_pdf_core.tools.unlock import execute


class TestUnlockTool:
    """Tests for the PDF unlock (password removal) tool."""

    def test_unlock_user_password(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["encrypted_user"]
        results = execute([src], password="1234", output_dir=tmp_output)
        assert len(results) == 1
        r = results[0]
        assert r.success is True
        assert r.tool == ToolName.UNLOCK
        assert r.output_path is not None
        assert r.output_path.is_file()

    def test_unlock_produces_unencrypted_file(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["encrypted_user"]
        results = execute([src], password="1234", output_dir=tmp_output)
        r = results[0]

        # The output should be openable without a password
        with pikepdf.open(str(r.output_path)) as pdf:
            assert len(pdf.pages) >= 1

    def test_unlock_wrong_password(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["encrypted_user"]
        results = execute([src], password="wrong_password", output_dir=tmp_output)
        assert len(results) == 1
        assert results[0].success is False

    def test_unlock_owner_password(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["encrypted_owner"]
        results = execute([src], password="1234", output_dir=tmp_output)
        assert len(results) == 1
        r = results[0]
        assert r.success is True
        assert r.output_path is not None
        assert r.output_path.is_file()

    def test_unlock_preserves_page_count(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["encrypted_user"]
        # Open with password to get original page count
        doc_orig = fitz.open(str(src))
        doc_orig.authenticate("1234")
        orig_pages = len(doc_orig)
        doc_orig.close()

        results = execute([src], password="1234", output_dir=tmp_output)
        doc_result = fitz.open(str(results[0].output_path))
        assert len(doc_result) == orig_pages
        doc_result.close()

    def test_unlock_cancellation(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        cancel = threading.Event()
        cancel.set()
        src = generated_pdfs["encrypted_user"]
        results = execute([src], password="1234", output_dir=tmp_output, cancel=cancel)
        assert len(results) == 1
        assert results[0].success is False

    def test_unlock_output_suffix(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["encrypted_user"]
        results = execute([src], password="1234", output_dir=tmp_output, output_suffix="_unlocked")
        r = results[0]
        assert r.output_path is not None
        assert "_unlocked" in r.output_path.name
