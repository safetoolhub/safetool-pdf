# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Shared pytest fixtures."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

@pytest.fixture(scope="session")
def test_pdfs_dir() -> Path:
    """Path to the test_pdfs directory."""
    return Path(__file__).parent / "test_pdfs"

@pytest.fixture(scope="session")
def generated_pdfs(test_pdfs_dir: Path) -> dict[str, Path]:
    """Generate all test PDFs once per session.

    Returns a dict mapping short name → Path.
    """
    # Lazy import so that fpdf2 + reportlab are only required for tests
    from tests.test_pdfs.generate_test_pdfs import generate_all

    output_dir = test_pdfs_dir / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    return generate_all(output_dir)

@pytest.fixture()
def tmp_output(tmp_path: Path) -> Path:
    """Temporary output directory for each test."""
    out = tmp_path / "output"
    out.mkdir()
    return out

@pytest.fixture(scope="session")
def encrypted_pdf(generated_pdfs: dict[str, Path]) -> Path:
    """Get an encrypted PDF for testing (password: 1234).
    
    Returns a Path to an encrypted PDF file.
    """
    return generated_pdfs["encrypted_user"]
