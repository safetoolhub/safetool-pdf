# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for the dedicated UnlockScreen UI."""

from __future__ import annotations

from pathlib import Path

import pytest

from safetool_pdf_desktop.screens.unlock_screen import UnlockScreen


class TestUnlockScreen:
    """Tests for UnlockScreen handling of encrypted and non-encrypted files."""

    @pytest.fixture
    def unlock_screen(self, qtbot):
        """Create an UnlockScreen instance."""
        screen = UnlockScreen()
        qtbot.addWidget(screen)
        return screen

    def test_set_files_stores_files(
        self, unlock_screen: UnlockScreen, generated_pdfs: dict[str, Path]
    ) -> None:
        """Test that set_files correctly stores the file list."""
        files = [generated_pdfs["simple_text"]]
        unlock_screen.set_files(files)
        assert unlock_screen._files == files

    def test_set_files_multiple(
        self, unlock_screen: UnlockScreen, generated_pdfs: dict[str, Path]
    ) -> None:
        """Test that set_files works with multiple files."""
        files = [generated_pdfs["simple_text"], generated_pdfs["multiple_fonts"]]
        unlock_screen.set_files(files)
        assert len(unlock_screen._files) == 2

    def test_encrypted_file_detected(
        self, unlock_screen: UnlockScreen, generated_pdfs: dict[str, Path]
    ) -> None:
        """Test that encrypted files are detected during set_files."""
        encrypted_file = generated_pdfs["encrypted_user"]
        unlock_screen.set_files([encrypted_file])
        assert unlock_screen._file_needs_password.get(0) is True
        assert unlock_screen._file_unlocked.get(0) is False

    def test_unencrypted_file_detected(
        self, unlock_screen: UnlockScreen, generated_pdfs: dict[str, Path]
    ) -> None:
        """Test that non-encrypted files are detected during set_files."""
        unencrypted_file = generated_pdfs["simple_text"]
        unlock_screen.set_files([unencrypted_file])
        assert unlock_screen._file_needs_password.get(0) is False
        assert unlock_screen._file_unlocked.get(0) is True

    def test_mixed_files_encryption_status(
        self, unlock_screen: UnlockScreen, generated_pdfs: dict[str, Path]
    ) -> None:
        """Test that mixed files are correctly classified."""
        files = [generated_pdfs["simple_text"], generated_pdfs["encrypted_user"]]
        unlock_screen.set_files(files)
        assert unlock_screen._file_needs_password[0] is False
        assert unlock_screen._file_needs_password[1] is True
        assert unlock_screen._file_unlocked[0] is True
        assert unlock_screen._file_unlocked[1] is False
