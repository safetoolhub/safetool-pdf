# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Comprehensive end-to-end test suite for all 5 SafeTool PDF tools.

Each test generates synthetic PDFs → runs a core tool → verifies the output
file exists and has the correct properties.  Tests cover:

  1. OPTIMIZE  — lossless, moderate, aggressive presets on varied inputs
  2. MERGE     — combining 2-5 PDFs, page count validation
  3. NUMBER    — correlative stamping, custom start, batch numbering
  4. STRIP_METADATA — DocInfo, XMP, mixed, already-clean
  5. UNLOCK    — user pw, owner pw, both, AES-256, permission combos

All encrypted test PDFs use the password **1234**.
"""

from __future__ import annotations

import threading
from pathlib import Path

import fitz  # PyMuPDF
import pikepdf
import pytest

from safetool_pdf_core.analyzer import analyze
from safetool_pdf_core.models import (
    OptimizeOptions,
    PdfPermissions,
    PresetName,
    ToolName,
)
from safetool_pdf_core.tools.merge import execute as merge_execute
from safetool_pdf_core.tools.metadata import execute as metadata_execute
from safetool_pdf_core.tools.numbering import execute as numbering_execute
from safetool_pdf_core.tools.optimize import optimize, optimize_batch, preset_by_name
from safetool_pdf_core.tools.unlock import execute as unlock_execute, read_permissions


# ───────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────

def _page_count(path: Path) -> int:
    """Return the number of pages in *path* (using PyMuPDF)."""
    doc = fitz.open(str(path))
    count = len(doc)
    doc.close()
    return count


def _is_encrypted(path: Path) -> bool:
    """Return True if *path* requires a password to open."""
    try:
        pdf = pikepdf.open(str(path))
        encrypted = pdf.is_encrypted
        pdf.close()
        return encrypted
    except pikepdf.PasswordError:
        return True


def _has_docinfo(path: Path, key: str) -> bool:
    """Check whether DocInfo contains a given *key* (e.g. '/Author')."""
    with pikepdf.open(str(path)) as pdf:
        if "/Info" not in pdf.trailer:
            return False
        return key in pdf.trailer["/Info"]


def _has_xmp(path: Path) -> bool:
    """Return True if the PDF has an XMP metadata stream."""
    with pikepdf.open(str(path)) as pdf:
        return "/Metadata" in pdf.Root


def _text_on_page(path: Path, page_index: int = 0) -> str:
    """Extract text from a page (useful for checking number stamps)."""
    doc = fitz.open(str(path))
    text = doc[page_index].get_text()
    doc.close()
    return text


# ═══════════════════════════════════════════════════════════════════════════
# 1. OPTIMIZE — end-to-end
# ═══════════════════════════════════════════════════════════════════════════


class TestOptimizeE2E:
    """End-to-end tests for the optimize tool."""

    # -- Lossless preset on different PDF structures ----------------------

    def test_lossless_simple_text(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["simple_text"]
        opts = preset_by_name(PresetName.LOSSLESS)
        result = optimize(src, options=opts, output_dir=tmp_output)
        assert result.output_path.is_file()
        assert result.optimized_size > 0
        assert _page_count(result.output_path) == _page_count(src)

    def test_lossless_uncompressed(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Uncompressed PDFs should benefit the most from lossless."""
        src = generated_pdfs["uncompressed"]
        opts = preset_by_name(PresetName.LOSSLESS)
        result = optimize(src, options=opts, output_dir=tmp_output)
        assert result.output_path.is_file()
        assert result.reduction_pct >= 0  # should almost always save some space

    def test_lossless_with_bookmarks(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["with_bookmarks"]
        opts = preset_by_name(PresetName.LOSSLESS)
        result = optimize(src, options=opts, output_dir=tmp_output)
        assert result.output_path.is_file()
        assert _page_count(result.output_path) == _page_count(src)

    def test_lossless_with_forms(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["with_forms"]
        opts = preset_by_name(PresetName.LOSSLESS)
        result = optimize(src, options=opts, output_dir=tmp_output)
        assert result.output_path.is_file()

    def test_lossless_already_optimized(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["already_optimized"]
        opts = preset_by_name(PresetName.LOSSLESS)
        result = optimize(src, options=opts, output_dir=tmp_output)
        assert result.output_path.is_file()

    def test_lossless_with_metadata(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["with_metadata"]
        opts = preset_by_name(PresetName.LOSSLESS)
        result = optimize(src, options=opts, output_dir=tmp_output)
        assert result.output_path.is_file()

    def test_lossless_with_layers(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["with_layers"]
        opts = preset_by_name(PresetName.LOSSLESS)
        result = optimize(src, options=opts, output_dir=tmp_output)
        assert result.output_path.is_file()

    # -- Moderate preset with image-heavy PDFs ----------------------------

    def test_moderate_large_images(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["large_images"]
        opts = preset_by_name(PresetName.MODERATE)
        # Disable GS so the test doesn't depend on external binary
        opts.ghostscript.enabled = False
        result = optimize(src, options=opts, output_dir=tmp_output)
        assert result.output_path.is_file()
        assert result.optimized_size < result.original_size

    def test_moderate_mixed_content(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["mixed_content"]
        opts = preset_by_name(PresetName.MODERATE)
        opts.ghostscript.enabled = False
        result = optimize(src, options=opts, output_dir=tmp_output)
        assert result.output_path.is_file()
        assert _page_count(result.output_path) == _page_count(src)

    def test_moderate_png_images(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["png_images"]
        opts = preset_by_name(PresetName.MODERATE)
        opts.ghostscript.enabled = False
        result = optimize(src, options=opts, output_dir=tmp_output)
        assert result.output_path.is_file()

    def test_moderate_multipage_images(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["multipage_images"]
        opts = preset_by_name(PresetName.MODERATE)
        opts.ghostscript.enabled = False
        result = optimize(src, options=opts, output_dir=tmp_output)
        assert result.output_path.is_file()
        assert _page_count(result.output_path) == 10

    # -- Aggressive preset -----------------------------------------------

    def test_aggressive_large_images(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["large_images"]
        opts = preset_by_name(PresetName.AGGRESSIVE)
        opts.ghostscript.enabled = False
        result = optimize(src, options=opts, output_dir=tmp_output)
        assert result.output_path.is_file()
        assert result.optimized_size < result.original_size

    def test_aggressive_large_100pages(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["large_100pages"]
        opts = preset_by_name(PresetName.AGGRESSIVE)
        opts.ghostscript.enabled = False
        result = optimize(src, options=opts, output_dir=tmp_output)
        assert result.output_path.is_file()
        assert _page_count(result.output_path) == 100

    def test_aggressive_with_thumbnails(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["with_thumbnails"]
        opts = preset_by_name(PresetName.AGGRESSIVE)
        opts.ghostscript.enabled = False
        result = optimize(src, options=opts, output_dir=tmp_output)
        assert result.output_path.is_file()

    # -- Batch optimize --------------------------------------------------

    def test_batch_optimize_lossless(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        sources = [
            generated_pdfs["simple_text"],
            generated_pdfs["mixed_content"],
            generated_pdfs["with_bookmarks"],
        ]
        opts = preset_by_name(PresetName.LOSSLESS)
        results = optimize_batch(sources, options=opts, output_dir=tmp_output)
        assert len(results) == 3
        for r in results:
            assert r.output_path.is_file()

    def test_batch_optimize_moderate_images(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        sources = [
            generated_pdfs["large_images"],
            generated_pdfs["png_images"],
        ]
        opts = preset_by_name(PresetName.MODERATE)
        opts.ghostscript.enabled = False
        results = optimize_batch(sources, options=opts, output_dir=tmp_output)
        assert len(results) == 2
        for r in results:
            assert r.output_path.is_file()
            assert r.optimized_size > 0

    # -- Cancellation ----------------------------------------------------

    def test_optimize_cancellation(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        cancel = threading.Event()
        cancel.set()  # pre-cancel
        src = generated_pdfs["simple_text"]
        opts = preset_by_name(PresetName.LOSSLESS)
        with pytest.raises(Exception):
            optimize(src, options=opts, output_dir=tmp_output, cancel=cancel)

    # -- Progress callback -----------------------------------------------

    def test_optimize_progress_callback(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        stages_seen: list[str] = []

        def _on_progress(info):
            stages_seen.append(info.stage)

        src = generated_pdfs["simple_text"]
        opts = preset_by_name(PresetName.LOSSLESS)
        optimize(src, options=opts, output_dir=tmp_output, progress_cb=_on_progress)
        assert len(stages_seen) > 0

    # -- Optimize with multiple fonts ------------------------------------

    def test_lossless_multiple_fonts(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["multiple_fonts"]
        opts = preset_by_name(PresetName.LOSSLESS)
        result = optimize(src, options=opts, output_dir=tmp_output)
        assert result.output_path.is_file()
        assert _page_count(result.output_path) == _page_count(src)


# ═══════════════════════════════════════════════════════════════════════════
# 2. MERGE — end-to-end
# ═══════════════════════════════════════════════════════════════════════════


class TestMergeE2E:
    """End-to-end tests for the merge tool."""

    def test_merge_two_simple(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        a = generated_pdfs["simple_text"]
        b = generated_pdfs["multiple_fonts"]
        results = merge_execute([a, b], output_dir=tmp_output)
        assert len(results) == 1
        r = results[0]
        assert r.success is True
        assert r.tool == ToolName.MERGE
        assert r.output_path is not None
        assert r.output_path.is_file()
        expected_pages = _page_count(a) + _page_count(b)
        assert _page_count(r.output_path) == expected_pages

    def test_merge_three_files(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        files = [
            generated_pdfs["simple_text"],
            generated_pdfs["with_bookmarks"],
            generated_pdfs["mixed_content"],
        ]
        results = merge_execute(files, output_dir=tmp_output)
        r = results[0]
        assert r.success is True
        expected = sum(_page_count(f) for f in files)
        assert _page_count(r.output_path) == expected

    def test_merge_five_files(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        files = [
            generated_pdfs["simple_text"],
            generated_pdfs["multiple_fonts"],
            generated_pdfs["with_links"],
            generated_pdfs["with_forms"],
            generated_pdfs["mixed_content"],
        ]
        results = merge_execute(files, output_dir=tmp_output)
        r = results[0]
        assert r.success is True
        expected = sum(_page_count(f) for f in files)
        assert _page_count(r.output_path) == expected

    def test_merge_multipage_pdfs(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Merge two multi-page PDFs and verify total page count."""
        a = generated_pdfs["with_bookmarks"]  # 11 pages
        b = generated_pdfs["multipage_images"]  # 10 pages
        results = merge_execute([a, b], output_dir=tmp_output)
        r = results[0]
        assert r.success is True
        assert _page_count(r.output_path) == _page_count(a) + _page_count(b)

    def test_merge_custom_output_filename(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        a = generated_pdfs["simple_text"]
        b = generated_pdfs["mixed_content"]
        results = merge_execute(
            [a, b], output_dir=tmp_output, output_filename="combined_report"
        )
        r = results[0]
        assert r.success is True
        assert "combined_report" in r.output_path.name

    def test_merge_requires_at_least_two(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        results = merge_execute(
            [generated_pdfs["simple_text"]], output_dir=tmp_output
        )
        assert len(results) == 1
        assert results[0].success is False

    def test_merge_output_size_recorded(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        a = generated_pdfs["simple_text"]
        b = generated_pdfs["multiple_fonts"]
        results = merge_execute([a, b], output_dir=tmp_output)
        r = results[0]
        assert r.output_size > 0
        assert r.original_size > 0

    def test_merge_different_content_types(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Merge PDFs with different content: text, images, forms."""
        files = [
            generated_pdfs["simple_text"],
            generated_pdfs["large_images"],
            generated_pdfs["with_forms"],
        ]
        results = merge_execute(files, output_dir=tmp_output)
        r = results[0]
        assert r.success is True
        expected = sum(_page_count(f) for f in files)
        assert _page_count(r.output_path) == expected

    def test_merge_cancellation(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        cancel = threading.Event()
        cancel.set()
        a = generated_pdfs["simple_text"]
        b = generated_pdfs["multiple_fonts"]
        results = merge_execute([a, b], output_dir=tmp_output, cancel=cancel)
        assert results[0].success is False


# ═══════════════════════════════════════════════════════════════════════════
# 3. NUMBERING — end-to-end
# ═══════════════════════════════════════════════════════════════════════════


class TestNumberingE2E:
    """End-to-end tests for the page numbering tool."""

    def test_number_single_file(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["simple_text"]
        results = numbering_execute([src], output_dir=tmp_output)
        assert len(results) == 1
        r = results[0]
        assert r.success is True
        assert r.output_path.is_file()
        assert _page_count(r.output_path) == _page_count(src)

    def test_number_stamp_appears_on_page1(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Verify the number '1' is stamped on the first page."""
        src = generated_pdfs["simple_text"]
        results = numbering_execute([src], output_dir=tmp_output, start_number=1)
        text = _text_on_page(results[0].output_path, page_index=0)
        assert "1" in text

    def test_number_custom_start(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["simple_text"]
        results = numbering_execute([src], output_dir=tmp_output, start_number=42)
        text = _text_on_page(results[0].output_path, page_index=0)
        assert "42" in text

    def test_number_batch_correlative(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Batch numbering: file 0 → start, file 1 → start+1, etc."""
        files = [
            generated_pdfs["simple_text"],
            generated_pdfs["multiple_fonts"],
            generated_pdfs["mixed_content"],
        ]
        results = numbering_execute(files, output_dir=tmp_output, start_number=10)
        assert len(results) == 3
        for idx, r in enumerate(results):
            assert r.success is True
            expected_num = str(10 + idx)
            text = _text_on_page(r.output_path, page_index=0)
            assert expected_num in text

    def test_number_preserves_page_count(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["with_bookmarks"]  # multi-page
        orig_pages = _page_count(src)
        results = numbering_execute([src], output_dir=tmp_output)
        assert _page_count(results[0].output_path) == orig_pages

    def test_number_only_stamps_first_page(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Only the 1st page should get a number — 2nd page stays clean."""
        src = generated_pdfs["with_bookmarks"]  # 11 pages
        orig_text_p2 = _text_on_page(src, page_index=1)
        results = numbering_execute([src], output_dir=tmp_output, start_number=99)
        # Page 1 has the stamp
        assert "99" in _text_on_page(results[0].output_path, page_index=0)
        # Page 2 should NOT have "99"
        new_text_p2 = _text_on_page(results[0].output_path, page_index=1)
        assert "99" not in new_text_p2

    def test_number_output_suffix(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["simple_text"]
        results = numbering_execute(
            [src], output_dir=tmp_output, output_suffix="_numbered"
        )
        assert "_numbered" in results[0].output_path.name

    def test_number_multipage_images(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["multipage_images"]
        results = numbering_execute([src], output_dir=tmp_output, start_number=1)
        r = results[0]
        assert r.success is True
        assert _page_count(r.output_path) == 10

    def test_number_cancellation(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        cancel = threading.Event()
        cancel.set()
        src = generated_pdfs["simple_text"]
        results = numbering_execute([src], output_dir=tmp_output, cancel=cancel)
        assert results[0].success is False


# ═══════════════════════════════════════════════════════════════════════════
# 4. STRIP METADATA — end-to-end
# ═══════════════════════════════════════════════════════════════════════════


class TestStripMetadataE2E:
    """End-to-end tests for the metadata removal tool."""

    def test_strip_xmp_metadata(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """with_metadata has XMP — verify it's gone after stripping."""
        src = generated_pdfs["with_metadata"]
        assert _has_xmp(src), "Source should have XMP metadata"
        results = metadata_execute([src], output_dir=tmp_output)
        r = results[0]
        assert r.success is True
        assert r.output_path.is_file()
        assert not _has_xmp(r.output_path), "Output should NOT have XMP"

    def test_strip_docinfo_author(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["metadata_author_only"]
        assert _has_docinfo(src, "/Author")
        results = metadata_execute([src], output_dir=tmp_output)
        r = results[0]
        assert r.success is True
        assert not _has_docinfo(r.output_path, "/Author")

    def test_strip_full_docinfo(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """metadata_full_docinfo has Author, Title, Subject, Keywords, etc."""
        src = generated_pdfs["metadata_full_docinfo"]
        for key in ["/Author", "/Title", "/Subject", "/Keywords", "/Creator"]:
            assert _has_docinfo(src, key), f"Source should have {key}"
        results = metadata_execute([src], output_dir=tmp_output)
        r = results[0]
        assert r.success is True
        # All DocInfo keys should be gone
        with pikepdf.open(str(r.output_path)) as pdf:
            assert "/Info" not in pdf.trailer

    def test_strip_rich_xmp(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["metadata_xmp_rich"]
        assert _has_xmp(src)
        assert _has_docinfo(src, "/Author")
        results = metadata_execute([src], output_dir=tmp_output)
        r = results[0]
        assert r.success is True
        assert not _has_xmp(r.output_path)
        assert not _has_docinfo(r.output_path, "/Author")

    def test_strip_gps_metadata(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["metadata_gps_location"]
        assert _has_docinfo(src, "/Subject")  # contains GPS-like info
        results = metadata_execute([src], output_dir=tmp_output)
        r = results[0]
        assert r.success is True
        with pikepdf.open(str(r.output_path)) as pdf:
            assert "/Info" not in pdf.trailer

    def test_strip_already_clean(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Stripping a PDF that already has no metadata should succeed."""
        src = generated_pdfs["simple_text"]
        results = metadata_execute([src], output_dir=tmp_output)
        assert results[0].success is True

    def test_strip_preserves_page_count(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["with_metadata"]
        results = metadata_execute([src], output_dir=tmp_output)
        assert _page_count(results[0].output_path) == _page_count(src)

    def test_strip_batch(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        files = [
            generated_pdfs["metadata_author_only"],
            generated_pdfs["metadata_full_docinfo"],
            generated_pdfs["metadata_xmp_rich"],
            generated_pdfs["metadata_gps_location"],
        ]
        results = metadata_execute(files, output_dir=tmp_output)
        assert len(results) == 4
        for r in results:
            assert r.success is True
            assert r.output_path.is_file()
            # Verify no remaining metadata
            with pikepdf.open(str(r.output_path)) as pdf:
                assert "/Info" not in pdf.trailer
                assert "/Metadata" not in pdf.Root

    def test_strip_preserves_content(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Ensure text content is preserved after stripping metadata."""
        src = generated_pdfs["metadata_full_docinfo"]
        results = metadata_execute([src], output_dir=tmp_output)
        orig_text = _text_on_page(src)
        new_text = _text_on_page(results[0].output_path)
        assert orig_text.strip() == new_text.strip()

    def test_strip_cancellation(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        cancel = threading.Event()
        cancel.set()
        src = generated_pdfs["with_metadata"]
        results = metadata_execute([src], output_dir=tmp_output, cancel=cancel)
        assert results[0].success is False


# ═══════════════════════════════════════════════════════════════════════════
# 5. UNLOCK — end-to-end
# ═══════════════════════════════════════════════════════════════════════════


class TestUnlockE2E:
    """End-to-end tests for the unlock (password / permission removal) tool.

    All test PDFs use the password **1234**.
    """

    # -- Basic decryption ------------------------------------------------

    def test_unlock_user_password(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["encrypted_user"]
        results = unlock_execute([src], password="1234", output_dir=tmp_output)
        assert len(results) == 1
        r = results[0]
        assert r.success is True
        assert r.output_path.is_file()
        # Output must be openable without password
        with pikepdf.open(str(r.output_path)) as pdf:
            assert len(pdf.pages) >= 1

    def test_unlock_owner_password(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["encrypted_owner"]
        results = unlock_execute([src], password="1234", output_dir=tmp_output)
        r = results[0]
        assert r.success is True
        assert r.output_path.is_file()

    def test_unlock_both_passwords(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["encrypted_both"]
        results = unlock_execute([src], password="1234", output_dir=tmp_output)
        r = results[0]
        assert r.success is True
        assert r.output_path.is_file()
        # Verify the output is not encrypted
        with pikepdf.open(str(r.output_path)) as pdf:
            assert not pdf.is_encrypted

    def test_unlock_aes256(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["encrypted_aes256"]
        results = unlock_execute([src], password="1234", output_dir=tmp_output)
        r = results[0]
        assert r.success is True
        assert r.output_path.is_file()
        with pikepdf.open(str(r.output_path)) as pdf:
            assert not pdf.is_encrypted

    def test_unlock_wrong_password(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["encrypted_user"]
        results = unlock_execute([src], password="wrong", output_dir=tmp_output)
        assert results[0].success is False

    def test_unlock_preserves_page_count(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["encrypted_user"]
        doc = fitz.open(str(src))
        doc.authenticate("1234")
        orig_pages = len(doc)
        doc.close()
        results = unlock_execute([src], password="1234", output_dir=tmp_output)
        assert _page_count(results[0].output_path) == orig_pages

    # -- Permission removal (owner-only pw) ------------------------------

    def test_unlock_removes_no_print_restriction(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """permissions_no_print denies printing — unlock should remove that."""
        src = generated_pdfs["permissions_no_print"]
        # Verify the source has restricted permissions
        perms = read_permissions(src)
        assert perms.print_lowres is False or perms.print_highres is False

        results = unlock_execute(
            [src], password="1234", output_dir=tmp_output, remove_encryption=True
        )
        r = results[0]
        assert r.success is True
        # Output should be freely openable, no encryption
        with pikepdf.open(str(r.output_path)) as pdf:
            assert not pdf.is_encrypted

    def test_unlock_removes_no_extract_restriction(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["permissions_no_extract"]
        perms = read_permissions(src)
        assert perms.extract is False

        results = unlock_execute(
            [src], password="1234", output_dir=tmp_output, remove_encryption=True
        )
        r = results[0]
        assert r.success is True
        with pikepdf.open(str(r.output_path)) as pdf:
            assert not pdf.is_encrypted

    def test_unlock_removes_no_modify_restriction(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["permissions_no_modify"]
        perms = read_permissions(src)
        assert perms.modify_other is False

        results = unlock_execute(
            [src], password="1234", output_dir=tmp_output, remove_encryption=True
        )
        r = results[0]
        assert r.success is True
        with pikepdf.open(str(r.output_path)) as pdf:
            assert not pdf.is_encrypted

    def test_unlock_removes_readonly_restriction(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """permissions_readonly has all permissions denied."""
        src = generated_pdfs["permissions_readonly"]
        perms = read_permissions(src)
        assert perms.print_lowres is False
        assert perms.extract is False
        assert perms.modify_other is False

        results = unlock_execute(
            [src], password="1234", output_dir=tmp_output, remove_encryption=True
        )
        r = results[0]
        assert r.success is True
        with pikepdf.open(str(r.output_path)) as pdf:
            assert not pdf.is_encrypted

    def test_unlock_removes_print_only_restriction(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["permissions_print_only"]
        results = unlock_execute(
            [src], password="1234", output_dir=tmp_output, remove_encryption=True
        )
        r = results[0]
        assert r.success is True
        with pikepdf.open(str(r.output_path)) as pdf:
            assert not pdf.is_encrypted

    def test_unlock_permissions_with_user_pw(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """PDF that requires user password + has restrictions."""
        src = generated_pdfs["permissions_with_user_pw"]
        results = unlock_execute(
            [src], password="1234", output_dir=tmp_output, remove_encryption=True
        )
        r = results[0]
        assert r.success is True
        with pikepdf.open(str(r.output_path)) as pdf:
            assert not pdf.is_encrypted

    # -- Read permissions helper -----------------------------------------

    def test_read_permissions_no_print(
        self, generated_pdfs: dict[str, Path]
    ) -> None:
        perms = read_permissions(generated_pdfs["permissions_no_print"])
        assert perms.print_lowres is False
        assert perms.print_highres is False
        # Other permissions should remain True
        assert perms.extract is True
        assert perms.modify_other is True

    def test_read_permissions_no_extract(
        self, generated_pdfs: dict[str, Path]
    ) -> None:
        perms = read_permissions(generated_pdfs["permissions_no_extract"])
        assert perms.extract is False
        assert perms.print_lowres is True

    def test_read_permissions_readonly(
        self, generated_pdfs: dict[str, Path]
    ) -> None:
        perms = read_permissions(generated_pdfs["permissions_readonly"])
        assert perms.print_lowres is False
        assert perms.print_highres is False
        assert perms.extract is False
        assert perms.modify_other is False
        assert perms.modify_annotation is False
        assert perms.fill_forms is False
        # Note: pikepdf forces accessibility=True per PDF spec
        assert perms.modify_assembly is False

    def test_read_permissions_unencrypted(
        self, generated_pdfs: dict[str, Path]
    ) -> None:
        """Unencrypted PDF should return all-True permissions."""
        perms = read_permissions(generated_pdfs["simple_text"])
        assert perms.print_lowres is True
        assert perms.extract is True
        assert perms.modify_other is True

    # -- Apply new permissions -------------------------------------------

    def test_set_new_permissions_no_print(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Apply no-print restriction to a plain PDF."""
        src = generated_pdfs["simple_text"]
        new_perms = PdfPermissions(
            print_lowres=False,
            print_highres=False,
        )
        results = unlock_execute(
            [src],
            output_dir=tmp_output,
            new_permissions=new_perms,
            new_owner_password="1234",
        )
        r = results[0]
        assert r.success is True
        # Verify the new permissions
        output_perms = read_permissions(r.output_path)
        assert output_perms.print_lowres is False
        assert output_perms.print_highres is False

    def test_set_new_permissions_extract_only(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["simple_text"]
        new_perms = PdfPermissions(
            print_lowres=False,
            print_highres=False,
            modify_other=False,
            extract=True,
            modify_annotation=False,
            fill_forms=False,
            accessibility=True,
            modify_assembly=False,
        )
        results = unlock_execute(
            [src],
            output_dir=tmp_output,
            new_permissions=new_perms,
            new_owner_password="1234",
        )
        r = results[0]
        assert r.success is True
        output_perms = read_permissions(r.output_path)
        assert output_perms.extract is True
        assert output_perms.print_lowres is False
        assert output_perms.modify_other is False

    # -- Batch unlock ----------------------------------------------------

    def test_unlock_batch(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        files = [
            generated_pdfs["encrypted_user"],
            generated_pdfs["encrypted_owner"],
            generated_pdfs["encrypted_both"],
        ]
        results = unlock_execute(
            files, password="1234", output_dir=tmp_output, remove_encryption=True
        )
        assert len(results) == 3
        for r in results:
            assert r.success is True
            assert r.output_path.is_file()
            with pikepdf.open(str(r.output_path)) as pdf:
                assert not pdf.is_encrypted

    def test_unlock_batch_permissions(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Batch-unlock permission-restricted PDFs."""
        files = [
            generated_pdfs["permissions_no_print"],
            generated_pdfs["permissions_no_extract"],
            generated_pdfs["permissions_readonly"],
        ]
        results = unlock_execute(
            files, password="1234", output_dir=tmp_output, remove_encryption=True
        )
        assert len(results) == 3
        for r in results:
            assert r.success is True
            with pikepdf.open(str(r.output_path)) as pdf:
                assert not pdf.is_encrypted

    # -- Cancellation / Edge cases ---------------------------------------

    def test_unlock_cancellation(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        cancel = threading.Event()
        cancel.set()
        src = generated_pdfs["encrypted_user"]
        results = unlock_execute(
            [src], password="1234", output_dir=tmp_output, cancel=cancel
        )
        assert results[0].success is False

    def test_unlock_output_suffix(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["encrypted_user"]
        results = unlock_execute(
            [src], password="1234", output_dir=tmp_output, output_suffix="_unlocked"
        )
        assert results[0].success is True
        assert "_unlocked" in results[0].output_path.name

    def test_unlock_nonexistent_file(self, tmp_output: Path) -> None:
        fake = Path("/tmp/nonexistent_file_12345.pdf")
        results = unlock_execute([fake], password="1234", output_dir=tmp_output)
        assert results[0].success is False


# ═══════════════════════════════════════════════════════════════════════════
# 6. CROSS-TOOL WORKFLOWS — pipelines
# ═══════════════════════════════════════════════════════════════════════════


class TestCrossToolE2E:
    """Test common multi-tool workflows end-to-end."""

    def test_unlock_then_optimize(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Unlock an encrypted PDF, then optimize the result."""
        src = generated_pdfs["encrypted_user"]
        # Step 1: unlock
        unlock_results = unlock_execute(
            [src], password="1234", output_dir=tmp_output
        )
        assert unlock_results[0].success is True
        unlocked = unlock_results[0].output_path

        # Step 2: optimize the unlocked PDF
        opts = preset_by_name(PresetName.LOSSLESS)
        opt_result = optimize(unlocked, options=opts, output_dir=tmp_output)
        assert opt_result.output_path.is_file()

    def test_strip_metadata_then_merge(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Strip metadata from files, then merge them."""
        files = [
            generated_pdfs["metadata_full_docinfo"],
            generated_pdfs["metadata_xmp_rich"],
        ]
        # Step 1: strip metadata
        strip_results = metadata_execute(files, output_dir=tmp_output)
        stripped_paths = [r.output_path for r in strip_results]
        for r in strip_results:
            assert r.success is True

        # Step 2: merge the stripped PDFs
        merge_results = merge_execute(stripped_paths, output_dir=tmp_output)
        assert merge_results[0].success is True
        expected_pages = sum(_page_count(f) for f in files)
        assert _page_count(merge_results[0].output_path) == expected_pages

    def test_number_then_merge(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Number PDFs then merge them."""
        files = [
            generated_pdfs["simple_text"],
            generated_pdfs["multiple_fonts"],
        ]
        # Step 1: number
        num_results = numbering_execute(
            files, output_dir=tmp_output, start_number=1
        )
        numbered_paths = [r.output_path for r in num_results]

        # Step 2: merge
        merge_results = merge_execute(numbered_paths, output_dir=tmp_output)
        assert merge_results[0].success is True

    def test_unlock_then_strip_metadata(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Unlock, then strip metadata from the result."""
        src = generated_pdfs["encrypted_user"]
        # Step 1: unlock
        unlock_results = unlock_execute(
            [src], password="1234", output_dir=tmp_output
        )
        unlocked = unlock_results[0].output_path

        # Step 2: strip metadata
        strip_results = metadata_execute([unlocked], output_dir=tmp_output)
        assert strip_results[0].success is True
        assert strip_results[0].output_path.is_file()
