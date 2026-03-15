# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_cli.main (CLI entry point)."""

from __future__ import annotations

from pathlib import Path

import pytest

from safetool_pdf_cli.main import main

class TestCLI:
    """Tests for the command-line interface."""

    def test_cli_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "safetool-pdf" in captured.out.lower() or "SafeTool PDF" in captured.out

    def test_cli_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "SafeTool PDF" in captured.out or "0." in captured.out

    def test_cli_dry_run(
        self,
        generated_pdfs: dict[str, Path],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """--dry-run should analyze without producing an output file."""
        src = generated_pdfs["simple_text"]
        rc = main(["optimize", "--dry-run", str(src)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Pages" in captured.out or "pages" in captured.out.lower()

    def test_cli_single_file(
        self,
        generated_pdfs: dict[str, Path],
        tmp_output: Path,
    ) -> None:
        """Optimizing a single file via the CLI should succeed."""
        src = generated_pdfs["simple_text"]
        rc = main(["optimize", "-o", str(tmp_output), str(src)])
        assert rc == 0
        # There should be at least one PDF in the output directory
        outputs = list(tmp_output.glob("*.pdf"))
        assert len(outputs) >= 1

    def test_cli_suffix_flag(
        self,
        generated_pdfs: dict[str, Path],
        tmp_output: Path,
    ) -> None:
        """--suffix flag changes output filename."""
        src = generated_pdfs["simple_text"]
        rc = main(["optimize", "--suffix", "_test_suffix", "-o", str(tmp_output), str(src)])
        assert rc == 0
        outputs = list(tmp_output.glob("*_test_suffix.pdf"))
        assert len(outputs) >= 1

    def test_cli_custom_mode(
        self,
        generated_pdfs: dict[str, Path],
        tmp_output: Path,
    ) -> None:
        """--custom mode with --dpi and --quality."""
        src = generated_pdfs["simple_text"]
        rc = main([
            "optimize", "--custom", "--dpi", "120", "--quality", "70",
            "-o", str(tmp_output), str(src),
        ])
        assert rc == 0
        outputs = list(tmp_output.glob("*.pdf"))
        assert len(outputs) >= 1
