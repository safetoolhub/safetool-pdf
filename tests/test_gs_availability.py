# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for Ghostscript availability handling.

Verifies that:
- preset_requires_gs correctly identifies presets needing GS
- The optimizer gracefully disables GS when unavailable
- Lossless preset works without GS
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from safetool_pdf_core.models import PresetName, OptimizeOptions
from safetool_pdf_core.tools.optimize.presets import (
    lossless,
    moderate,
    aggressive,
    custom,
    preset_by_name,
    preset_requires_gs,
)


class TestPresetRequiresGS:
    """Verify preset_requires_gs correctly identifies GS-dependent presets."""

    def test_lossless_does_not_require_gs(self) -> None:
        assert preset_requires_gs(PresetName.LOSSLESS) is False

    def test_moderate_requires_gs(self) -> None:
        assert preset_requires_gs(PresetName.MODERATE) is True

    def test_aggressive_requires_gs(self) -> None:
        assert preset_requires_gs(PresetName.AGGRESSIVE) is True

    def test_custom_does_not_require_gs(self) -> None:
        assert preset_requires_gs(PresetName.CUSTOM) is False

    def test_all_presets_covered(self) -> None:
        """Every preset must have a defined answer."""
        for name in PresetName:
            result = preset_requires_gs(name)
            assert isinstance(result, bool)


class TestOptimizerGSFallback:
    """Verify the optimizer disables GS when unavailable."""

    def test_lossless_works_without_gs(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Lossless optimization should succeed even if GS is absent."""
        from safetool_pdf_core.tools.optimize import optimize

        src = generated_pdfs["simple_text"]
        with patch("safetool_pdf_core.tools.optimize.optimize.gs_available", return_value=False):
            result = optimize(src, lossless(), output_dir=tmp_output)
        assert result.output_path.is_file()
        assert result.optimized_size > 0

    def test_moderate_disables_gs_when_unavailable(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Moderate preset should still produce output when GS is missing,
        but with a warning about GS being skipped."""
        from safetool_pdf_core.tools.optimize import optimize

        src = generated_pdfs["simple_text"]
        opts = moderate()
        with patch("safetool_pdf_core.tools.optimize.optimize.gs_available", return_value=False):
            result = optimize(src, opts, output_dir=tmp_output)
        assert result.output_path.is_file()
        assert result.optimized_size > 0
        assert any("Ghostscript" in w for w in result.warnings)
        # GS should have been disabled in the options
        assert opts.ghostscript.enabled is False

    def test_aggressive_disables_gs_when_unavailable(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Aggressive preset should still produce output when GS is missing."""
        from safetool_pdf_core.tools.optimize import optimize

        src = generated_pdfs["simple_text"]
        opts = aggressive()
        with patch("safetool_pdf_core.tools.optimize.optimize.gs_available", return_value=False):
            result = optimize(src, opts, output_dir=tmp_output)
        assert result.output_path.is_file()
        assert result.optimized_size > 0
        assert any("Ghostscript" in w for w in result.warnings)


class TestPresetGSConsistency:
    """Verify preset options match preset_requires_gs."""

    def test_gs_required_presets_enable_gs(self) -> None:
        """Presets that require GS should have ghostscript.enabled=True."""
        for name in PresetName:
            opts = preset_by_name(name)
            if preset_requires_gs(name):
                assert opts.ghostscript.enabled is True, (
                    f"{name} requires GS but has ghostscript.enabled=False"
                )

    def test_gs_not_required_presets_disable_gs(self) -> None:
        """Presets that don't require GS should have ghostscript.enabled=False."""
        for name in (PresetName.LOSSLESS,):
            opts = preset_by_name(name)
            assert opts.ghostscript.enabled is False
