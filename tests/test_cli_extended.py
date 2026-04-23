# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_cli.main — CLI batch mode and preset flags."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run safetool-pdf CLI as subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "safetool_pdf_cli.main", *args],
        capture_output=True,
        text=True,
        timeout=120,
    )


def _run_optimize(*args: str) -> subprocess.CompletedProcess:
    """Run safetool-pdf optimize subcommand as subprocess."""
    return _run_cli("optimize", *args)


class TestCLIPresets:
    """Test preset selection via CLI flags."""

    def test_lossless_preset(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        result = _run_optimize(
            str(generated_pdfs["simple_text"]),
            "--preset", "lossless",
            "--output-dir", str(tmp_output),
        )
        assert result.returncode == 0

    def test_moderate_preset(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        result = _run_optimize(
            str(generated_pdfs["simple_text"]),
            "--preset", "moderate",
            "--output-dir", str(tmp_output),
        )
        assert result.returncode == 0

    def test_aggressive_preset(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        result = _run_optimize(
            str(generated_pdfs["simple_text"]),
            "--preset", "aggressive",
            "--output-dir", str(tmp_output),
        )
        assert result.returncode == 0


class TestCLIBatchMode:
    """CLI batch mode with multiple files."""

    def test_batch_two_files(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        result = _run_optimize(
            str(generated_pdfs["simple_text"]),
            str(generated_pdfs["mixed_content"]),
            "--output-dir", str(tmp_output),
        )
        assert result.returncode == 0

    def test_batch_with_glob_pattern(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Multiple files passed on command line."""
        files = [
            str(generated_pdfs["simple_text"]),
            str(generated_pdfs["large_100pages"]),
        ]
        result = _run_optimize(*files, "--output-dir", str(tmp_output))
        assert result.returncode == 0


class TestCLIVerbose:
    """Verbose flag produces more output."""

    def test_verbose_flag(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        result = _run_optimize(
            str(generated_pdfs["simple_text"]),
            "--verbose",
            "--output-dir", str(tmp_output),
        )
        assert result.returncode == 0

    def test_dry_run_verbose(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        result = _run_optimize(
            str(generated_pdfs["simple_text"]),
            "--dry-run",
            "--verbose",
        )
        assert result.returncode == 0


class TestCLIErrors:
    """Error handling in CLI."""

    def test_nonexistent_file(self, tmp_output: Path) -> None:
        result = _run_optimize("/tmp/not_a_real_file.pdf", "--output-dir", str(tmp_output))
        assert result.returncode != 0

    def test_invalid_preset(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        result = _run_optimize(
            str(generated_pdfs["simple_text"]),
            "--preset", "supermax",
            "--output-dir", str(tmp_output),
        )
        assert result.returncode != 0


class TestCLISuffix:
    """Tests for --suffix flag."""

    def test_suffix_flag(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        result = _run_optimize(
            str(generated_pdfs["simple_text"]),
            "--suffix", "_custom_suffix",
            "--output-dir", str(tmp_output),
        )
        assert result.returncode == 0
        outputs = list(tmp_output.glob("*_custom_suffix.pdf"))
        assert len(outputs) >= 1


class TestCLICustomMode:
    """Tests for --custom mode with sub-options."""

    def test_custom_basic(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        result = _run_optimize(
            str(generated_pdfs["simple_text"]),
            "--custom", "--dpi", "120", "--quality", "70",
            "--output-dir", str(tmp_output),
        )
        assert result.returncode == 0

    def test_custom_with_cleanup(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        result = _run_optimize(
            str(generated_pdfs["simple_text"]),
            "--custom", "--remove-metadata", "--remove-js",
            "--output-dir", str(tmp_output),
        )
        assert result.returncode == 0
