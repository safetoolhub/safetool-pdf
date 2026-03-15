# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.verifier.verify."""

from __future__ import annotations

import shutil
from pathlib import Path

import fitz
import pytest

from safetool_pdf_core.exceptions import VerificationError
from safetool_pdf_core.tools.optimize.verifier import verify

class TestVerifier:
    """Tests for post-optimization verification."""

    def test_verify_valid(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """A valid PDF should pass verification without errors."""
        src = generated_pdfs["simple_text"]
        copy = tmp_output / "valid.pdf"
        shutil.copy2(str(src), str(copy))

        doc = fitz.open(str(src))
        page_count = doc.page_count
        original_size = src.stat().st_size
        doc.close()

        warnings = verify(copy, page_count, original_size)
        assert isinstance(warnings, list)

    def test_verify_missing(self, tmp_output: Path) -> None:
        """Verification of a non-existent file should raise VerificationError."""
        missing = tmp_output / "does_not_exist.pdf"
        with pytest.raises(VerificationError):
            verify(missing, expected_page_count=1, original_size=1000)

    def test_verify_page_mismatch(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Verification with wrong page count should raise VerificationError."""
        src = generated_pdfs["simple_text"]
        copy = tmp_output / "mismatch.pdf"
        shutil.copy2(str(src), str(copy))

        # Pass a deliberately wrong page count
        with pytest.raises(VerificationError, match="Page count mismatch"):
            verify(copy, expected_page_count=9999, original_size=src.stat().st_size)
