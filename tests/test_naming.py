# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.naming.output_path_for."""

from __future__ import annotations

from pathlib import Path

from safetool_pdf_core.constants import OUTPUT_SUFFIX
from safetool_pdf_core.naming import output_path_for

class TestOutputNaming:
    """Verify output file naming and collision handling."""

    def test_default_suffix(self, tmp_output: Path) -> None:
        src = tmp_output / "report.pdf"
        src.touch()
        result = output_path_for(src)
        assert OUTPUT_SUFFIX in result.name
        assert result.suffix == ".pdf"
        assert result.parent == tmp_output

    def test_collision_numbering(self, tmp_output: Path) -> None:
        src = tmp_output / "report.pdf"
        src.touch()

        # Create the first expected output so a collision occurs
        first = tmp_output / f"report{OUTPUT_SUFFIX}.pdf"
        first.touch()

        result = output_path_for(src)
        assert "(1)" in result.name

        # Create (1) too
        result.touch()
        result2 = output_path_for(src)
        assert "(2)" in result2.name

    def test_custom_output_dir(self, tmp_output: Path) -> None:
        src = tmp_output / "input.pdf"
        src.touch()
        custom_dir = tmp_output / "custom_out"
        custom_dir.mkdir()

        result = output_path_for(src, output_dir=custom_dir)
        assert result.parent == custom_dir
        assert OUTPUT_SUFFIX in result.name

    def test_custom_suffix(self, tmp_output: Path) -> None:
        """Custom suffix is used when provided."""
        src = tmp_output / "input.pdf"
        src.touch()
        result = output_path_for(src, suffix="_custom")
        assert "_custom" in result.name
        assert result.suffix == ".pdf"
