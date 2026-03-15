# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for signed PDF handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from safetool_pdf_core.analyzer import analyze
from safetool_pdf_core.exceptions import SignedPDFError
from safetool_pdf_core.models import PreservationMode
from safetool_pdf_core.tools.optimize import optimize
from safetool_pdf_core.tools.optimize.presets import lossless

class TestSignedPDFs:
    """Verify that signed PDFs are detected and protected."""

    @pytest.fixture()
    def _signed_pdf(self, generated_pdfs: dict[str, Path]) -> Path | None:
        """Try to find or create a signed-like test PDF.

        The test PDF generator may not produce a truly signed PDF;
        return *None* so dependent tests can skip.
        """
        # Check all generated PDFs for a signature flag
        for key in ("with_forms", "simple_text"):
            pdf = generated_pdfs[key]
            result = analyze(pdf)
            if result.has_signatures:
                return pdf
        return None

    def test_signed_pdf_detected(self, _signed_pdf: Path | None) -> None:
        if _signed_pdf is None:
            pytest.skip("No signed test PDF available")
        result = analyze(_signed_pdf)
        assert result.has_signatures is True

    def test_signed_blocks_simplify(
        self, _signed_pdf: Path | None, tmp_output: Path
    ) -> None:
        """Simplify mode on a signed PDF must raise SignedPDFError."""
        if _signed_pdf is None:
            pytest.skip("No signed test PDF available")
        opts = lossless(preservation=PreservationMode.SIMPLIFY)
        with pytest.raises(SignedPDFError):
            optimize(_signed_pdf, options=opts, output_dir=tmp_output)
