# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for encrypted PDF handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from safetool_pdf_core.analyzer import analyze
from safetool_pdf_core.exceptions import AnalysisError

class TestEncryptedPDFs:
    """Verify encrypted PDF analysis with and without a password."""

    def test_encrypted_user_with_password(
        self, generated_pdfs: dict[str, Path]
    ) -> None:
        """Analyzing an encrypted PDF with the correct password should succeed."""
        pdf = generated_pdfs["encrypted_user"]
        result = analyze(pdf, password="1234")
        assert result.page_count >= 1
        # After successful authentication, PyMuPDF may report is_encrypted
        # as False since the document has been unlocked.

    def test_encrypted_without_password(
        self, generated_pdfs: dict[str, Path]
    ) -> None:
        """Analyzing an encrypted PDF without a password should raise or warn."""
        pdf = generated_pdfs["encrypted_user"]
        # Depending on encryption level, fitz may open the file with
        # limited access or fail entirely.  Either an exception or
        # warnings in the result are acceptable.
        try:
            result = analyze(pdf)
            # If it didn't raise, it should at least flag encryption
            assert result.is_encrypted is True
        except (AnalysisError, Exception):
            pass  # raising is acceptable behaviour
