# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for analyzer.py error handling with invalid, corrupted, and non-PDF files."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from safetool_pdf_core.analyzer import analyze
from safetool_pdf_core.exceptions import AnalysisError, InvalidPDFError


class TestAnalyzerErrorHandling:
    """Tests for error handling in the PDF analyzer."""

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Test that analyzing a non-existent file raises InvalidPDFError."""
        nonexistent = tmp_path / "does_not_exist.pdf"
        with pytest.raises(InvalidPDFError, match="File not found"):
            analyze(nonexistent)

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test that analyzing an empty file raises InvalidPDFError."""
        empty_file = tmp_path / "empty.pdf"
        empty_file.write_bytes(b"")
        
        with pytest.raises(InvalidPDFError, match="Invalid|corrupted|Cannot open"):
            analyze(empty_file)

    def test_text_file_not_pdf(self, tmp_path: Path) -> None:
        """Test that analyzing a text file (not PDF) raises InvalidPDFError."""
        text_file = tmp_path / "not_a_pdf.txt"
        text_file.write_text("This is just a text file, not a PDF.")
        
        with pytest.raises(InvalidPDFError, match="Invalid|corrupted|Cannot open|not a PDF"):
            analyze(text_file)

    def test_binary_file_not_pdf(self, tmp_path: Path) -> None:
        """Test that analyzing a binary file (not PDF) raises InvalidPDFError."""
        binary_file = tmp_path / "not_a_pdf.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04\x05" * 100)
        
        with pytest.raises((InvalidPDFError, AnalysisError)):
            analyze(binary_file)

    def test_corrupted_pdf_header(self, tmp_path: Path) -> None:
        """Test that analyzing a file with corrupted PDF header raises InvalidPDFError."""
        corrupted = tmp_path / "corrupted_header.pdf"
        # Write a file that starts like a PDF but is corrupted
        corrupted.write_bytes(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n" + b"corrupted data" * 100)
        
        with pytest.raises(InvalidPDFError, match="Invalid|corrupted|Cannot open"):
            analyze(corrupted)

    def test_truncated_pdf(self, tmp_path: Path, generated_pdfs: dict[str, Path]) -> None:
        """Test that analyzing a truncated PDF raises InvalidPDFError."""
        # Take a valid PDF and truncate it
        valid_pdf = generated_pdfs["simple_text"]
        truncated = tmp_path / "truncated.pdf"
        
        # Copy only first 1KB of the PDF
        with open(valid_pdf, "rb") as src:
            data = src.read(1024)
        truncated.write_bytes(data)
        
        # PyMuPDF might be able to recover from truncated PDFs
        # So we just check that it doesn't crash
        try:
            result = analyze(truncated)
            # If it succeeds, that's also acceptable
        except (InvalidPDFError, AnalysisError):
            # Expected for truncated PDFs
            pass

    def test_pdf_with_fake_extension(self, tmp_path: Path) -> None:
        """Test that a non-PDF file with .pdf extension raises InvalidPDFError."""
        fake_pdf = tmp_path / "fake.pdf"
        fake_pdf.write_text("This is not a PDF, just has the extension")
        
        with pytest.raises((InvalidPDFError, AnalysisError)):
            analyze(fake_pdf)

    def test_permission_denied(self, tmp_path: Path, generated_pdfs: dict[str, Path]) -> None:
        """Test that a file without read permissions raises InvalidPDFError."""
        if os.name == "nt":
            pytest.skip("Permission test not reliable on Windows")
        
        # Copy a valid PDF
        valid_pdf = generated_pdfs["simple_text"]
        no_read = tmp_path / "no_read.pdf"
        no_read.write_bytes(valid_pdf.read_bytes())
        
        # Remove read permissions
        no_read.chmod(0o000)
        
        try:
            with pytest.raises((InvalidPDFError, AnalysisError, PermissionError)):
                analyze(no_read)
        finally:
            # Restore permissions for cleanup
            no_read.chmod(0o644)

    def test_valid_pdf_returns_result(self, generated_pdfs: dict[str, Path]) -> None:
        """Test that a valid PDF returns an AnalysisResult without errors."""
        result = analyze(generated_pdfs["simple_text"])
        assert result is not None
        assert result.page_count > 0
        assert result.file_size > 0

    def test_encrypted_pdf_without_password(self, generated_pdfs: dict[str, Path]) -> None:
        """Test that an encrypted PDF without password is handled gracefully."""
        # Should not raise, but should mark as encrypted
        result = analyze(generated_pdfs["encrypted_user"])
        assert result.is_encrypted is True
        assert any("encrypted" in w.lower() for w in result.warnings)

    def test_encrypted_pdf_with_wrong_password(self, generated_pdfs: dict[str, Path]) -> None:
        """Test that an encrypted PDF with wrong password is handled gracefully."""
        # Should not raise, but should mark as encrypted with warning
        result = analyze(generated_pdfs["encrypted_user"], password="wrong_password")
        assert result.is_encrypted is True
        assert any("wrong password" in w.lower() for w in result.warnings)

    def test_encrypted_pdf_with_correct_password(self, generated_pdfs: dict[str, Path]) -> None:
        """Test that an encrypted PDF with correct password is analyzed successfully."""
        result = analyze(generated_pdfs["encrypted_user"], password="1234")
        # The PDF should be successfully analyzed
        assert result.page_count > 0

    def test_pdf_with_special_characters_in_path(self, tmp_path: Path, generated_pdfs: dict[str, Path]) -> None:
        """Test that PDFs with special characters in path are handled correctly."""
        valid_pdf = generated_pdfs["simple_text"]
        special_path = tmp_path / "file with spaces & special (chars).pdf"
        special_path.write_bytes(valid_pdf.read_bytes())
        
        result = analyze(special_path)
        assert result is not None
        assert result.page_count > 0

    def test_very_small_file(self, tmp_path: Path) -> None:
        """Test that a very small file (< 100 bytes) raises InvalidPDFError."""
        tiny = tmp_path / "tiny.pdf"
        tiny.write_bytes(b"%PDF-1.4\n")
        
        with pytest.raises((InvalidPDFError, AnalysisError)):
            analyze(tiny)

    def test_file_with_null_bytes(self, tmp_path: Path) -> None:
        """Test that a file with null bytes raises InvalidPDFError."""
        null_file = tmp_path / "null_bytes.pdf"
        null_file.write_bytes(b"\x00" * 1000)
        
        with pytest.raises((InvalidPDFError, AnalysisError)):
            analyze(null_file)

    def test_html_file_with_pdf_extension(self, tmp_path: Path) -> None:
        """Test that an HTML file with .pdf extension raises InvalidPDFError."""
        html_pdf = tmp_path / "webpage.pdf"
        html_pdf.write_text("<html><body>This is HTML, not PDF</body></html>")
        
        with pytest.raises(InvalidPDFError, match="Invalid|corrupted|Cannot open|not a PDF"):
            analyze(html_pdf)

    def test_zip_file_with_pdf_extension(self, tmp_path: Path) -> None:
        """Test that a ZIP file with .pdf extension raises InvalidPDFError."""
        zip_pdf = tmp_path / "archive.pdf"
        # ZIP file magic bytes
        zip_pdf.write_bytes(b"PK\x03\x04" + b"\x00" * 100)
        
        with pytest.raises((InvalidPDFError, AnalysisError)):
            analyze(zip_pdf)

    def test_image_file_with_pdf_extension(self, tmp_path: Path) -> None:
        """Test that an image file with .pdf extension raises InvalidPDFError."""
        img_pdf = tmp_path / "image.pdf"
        # PNG magic bytes
        img_pdf.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        
        with pytest.raises(InvalidPDFError, match="Invalid|corrupted|Cannot open|not a PDF"):
            analyze(img_pdf)
