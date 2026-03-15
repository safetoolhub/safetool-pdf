# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for CLI subcommands (merge, number, strip-metadata, unlock)."""

from __future__ import annotations

from pathlib import Path

import pytest

from safetool_pdf_cli.main import main


class TestCLISubcommands:
    """Tests for the new CLI subcommands."""

    # ---------------------------------------------------------------
    # Help / dispatch
    # ---------------------------------------------------------------

    def test_no_subcommand_shows_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = main([])
        assert rc == 2

    def test_optimize_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["optimize", "--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "preset" in captured.out.lower()

    def test_merge_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["merge", "--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "files" in captured.out.lower()

    # ---------------------------------------------------------------
    # optimize subcommand (backward compat)
    # ---------------------------------------------------------------

    def test_optimize_subcommand(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["simple_text"]
        rc = main(["optimize", "-o", str(tmp_output), str(src)])
        assert rc == 0
        assert len(list(tmp_output.glob("*.pdf"))) >= 1

    def test_optimize_dry_run(
        self, generated_pdfs: dict[str, Path], capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = generated_pdfs["simple_text"]
        rc = main(["optimize", "--dry-run", str(src)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Pages" in captured.out or "pages" in captured.out.lower()

    # ---------------------------------------------------------------
    # merge subcommand
    # ---------------------------------------------------------------

    def test_merge_subcommand(
        self, generated_pdfs: dict[str, Path], tmp_output: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src_a = generated_pdfs["simple_text"]
        src_b = generated_pdfs["multiple_fonts"]
        rc = main(["merge", "-o", str(tmp_output), str(src_a), str(src_b)])
        assert rc == 0
        outputs = list(tmp_output.glob("*.pdf"))
        assert len(outputs) == 1

    def test_merge_single_file_fails(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["simple_text"]
        rc = main(["merge", "-o", str(tmp_output), str(src)])
        assert rc == 1

    # ---------------------------------------------------------------
    # number subcommand
    # ---------------------------------------------------------------

    def test_number_subcommand(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["simple_text"]
        rc = main(["number", "-o", str(tmp_output), str(src)])
        assert rc == 0
        assert len(list(tmp_output.glob("*.pdf"))) >= 1

    def test_number_start_flag(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["simple_text"]
        rc = main(["number", "--start", "5", "-o", str(tmp_output), str(src)])
        assert rc == 0

        import fitz
        output = list(tmp_output.glob("*.pdf"))[0]
        doc = fitz.open(str(output))
        assert "5" in doc[0].get_text()
        doc.close()

    # ---------------------------------------------------------------
    # strip-metadata subcommand
    # ---------------------------------------------------------------

    def test_strip_metadata_subcommand(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["with_metadata"]
        rc = main(["strip-metadata", "-o", str(tmp_output), str(src)])
        assert rc == 0
        assert len(list(tmp_output.glob("*.pdf"))) >= 1

    # ---------------------------------------------------------------
    # unlock subcommand
    # ---------------------------------------------------------------

    def test_unlock_subcommand(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["encrypted_user"]
        rc = main(["unlock", "--password", "1234", "-o", str(tmp_output), str(src)])
        assert rc == 0
        assert len(list(tmp_output.glob("*.pdf"))) >= 1

    def test_unlock_wrong_password(
        self, generated_pdfs: dict[str, Path], tmp_output: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src = generated_pdfs["encrypted_user"]
        rc = main(["unlock", "--password", "wrong", "-o", str(tmp_output), str(src)])
        # Should complete without crashing (tool returns failure result)
        assert rc == 0

    def test_nonexistent_file(self, tmp_output: Path) -> None:
        rc = main(["number", "-o", str(tmp_output), "/nonexistent/file.pdf"])
        assert rc == 1
