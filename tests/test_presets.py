# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.presets factory functions."""

from __future__ import annotations

import pytest

from safetool_pdf_core.models import PresetName
from safetool_pdf_core.tools.optimize.presets import custom, lossless, moderate, aggressive, preset_by_name

class TestPresets:
    """Verify each preset returns the expected options."""

    def test_lossless_preset(self) -> None:
        opts = lossless()
        assert opts.preset is PresetName.LOSSLESS
        assert opts.lossy_images.enabled is False
        assert opts.ghostscript.enabled is False
        assert opts.lossless.recompress_flate is True
        assert opts.lossless.remove_unreferenced is True

    def test_moderate_preset(self) -> None:
        opts = moderate()
        assert opts.preset is PresetName.MODERATE
        assert opts.lossy_images.enabled is True
        assert opts.lossy_images.target_dpi == 150
        assert opts.lossy_images.jpeg_quality == 80
        assert opts.ghostscript.enabled is True
        assert opts.ghostscript.font_subsetting is True

    def test_aggressive_preset(self) -> None:
        opts = aggressive()
        assert opts.preset is PresetName.AGGRESSIVE
        assert opts.lossy_images.enabled is True
        assert opts.lossy_images.target_dpi == 96
        assert opts.lossy_images.jpeg_quality == 50
        assert opts.ghostscript.enabled is True
        assert opts.ghostscript.full_rewrite is True

    def test_custom_preset(self) -> None:
        opts = custom()
        assert opts.preset is PresetName.CUSTOM

    @pytest.mark.parametrize("name", list(PresetName))
    def test_preset_by_name(self, name: PresetName) -> None:
        opts = preset_by_name(name)
        assert opts.preset is name
