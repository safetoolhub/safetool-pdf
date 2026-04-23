# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.stages.lossy_ghostscript and gs_detect."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from safetool_pdf_core.exceptions import GhostscriptNotFoundError
from safetool_pdf_core.gs_detect import find_gs, gs_available
from safetool_pdf_core.models import GhostscriptOptions
from safetool_pdf_core.tools.optimize.stages.lossy_ghostscript import run_ghostscript

_GS_IS_AVAILABLE = gs_available()

class TestGSDetect:
    """Tests for Ghostscript binary detection."""

    def test_gs_detect(self) -> None:
        result = find_gs()
        # Should return a Path or None — never anything else
        assert result is None or isinstance(result, Path)

class TestGhostscriptStage:
    """Tests for the Ghostscript optimization stage."""

    def test_gs_disabled_copies(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """When GS is disabled the stage just copies the input."""
        src = generated_pdfs["simple_text"]
        dst = tmp_output / "gs_disabled.pdf"
        opts = GhostscriptOptions(enabled=False)
        run_ghostscript(src, dst, opts)
        assert dst.is_file()
        assert dst.stat().st_size == src.stat().st_size

    def test_gs_not_found(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """When GS is not found, GhostscriptNotFoundError should be raised."""
        src = generated_pdfs["simple_text"]
        dst = tmp_output / "gs_missing.pdf"
        opts = GhostscriptOptions(enabled=True)
        with patch("safetool_pdf_core.tools.optimize.stages.lossy_ghostscript.find_gs", return_value=None):
            with pytest.raises(GhostscriptNotFoundError):
                run_ghostscript(src, dst, opts)

    @pytest.mark.skipif(not _GS_IS_AVAILABLE, reason="Ghostscript not available")
    def test_gs_runs(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Ghostscript should produce a valid output file."""
        src = generated_pdfs["simple_text"]
        dst = tmp_output / "gs_output.pdf"
        opts = GhostscriptOptions(
            enabled=True, font_subsetting=True, full_rewrite=False
        )
        warnings = run_ghostscript(src, dst, opts)
        assert dst.is_file()
        assert dst.stat().st_size > 0
        assert isinstance(warnings, list)
