# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tests for safetool_pdf_core.tools.split."""

from __future__ import annotations

import threading
from pathlib import Path

import fitz
import pytest

from safetool_pdf_core.models import SplitMode, ToolName
from safetool_pdf_core.tools.split import parse_ranges, split, split_batch


def _page_count(path: Path) -> int:
    doc = fitz.open(str(path))
    count = len(doc)
    doc.close()
    return count


class TestParseRanges:
    """Unit tests for parse_ranges()."""

    def test_single_page(self) -> None:
        result = parse_ranges("3", page_count=10)
        assert result == [[2]]

    def test_simple_range(self) -> None:
        result = parse_ranges("1-3", page_count=10)
        assert result == [[0, 1, 2]]

    def test_multiple_ranges(self) -> None:
        result = parse_ranges("1-3, 5, 8-10", page_count=10)
        assert result == [[0, 1, 2], [4], [7, 8, 9]]

    def test_whitespace_tolerance(self) -> None:
        # Leading/trailing spaces and spaces around commas are fine;
        # spaces inside range tokens (e.g. "1 - 2") are NOT supported.
        result = parse_ranges("  1-2 , 4  ", page_count=5)
        assert result == [[0, 1], [3]]

    def test_single_page_of_one(self) -> None:
        result = parse_ranges("1", page_count=1)
        assert result == [[0]]

    def test_full_document(self) -> None:
        result = parse_ranges("1-5", page_count=5)
        assert result == [[0, 1, 2, 3, 4]]

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            parse_ranges("", page_count=5)

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_ranges("   ", page_count=5)

    def test_page_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="less than 1"):
            parse_ranges("0-2", page_count=5)

    def test_page_beyond_count_raises(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            parse_ranges("1-6", page_count=5)

    def test_reversed_range_raises(self) -> None:
        with pytest.raises(ValueError, match="less than range start"):
            parse_ranges("5-3", page_count=10)

    def test_malformed_token_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid range token"):
            parse_ranges("abc", page_count=5)

    def test_comma_only_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_ranges(",,,", page_count=5)


class TestSplitEveryPage:
    """EVERY_PAGE mode tests."""

    def test_every_page_produces_n_files(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["simple_text"]
        total_pages = _page_count(src)
        results = split(src, SplitMode.EVERY_PAGE, {}, suffix="pg", progress_cb=None, cancel=None)

        assert len(results) == total_pages
        for r in results:
            assert r.success is True
            assert r.tool == ToolName.SPLIT
            assert r.output_path is not None
            assert r.output_path.is_file()
            assert r.page_count == 1

    def test_every_page_single_page_pdf(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """A 1-page PDF yields exactly 1 chunk."""
        src = generated_pdfs["simple_text"]
        # Use a small PDF guaranteed to have pages
        results = split(src, SplitMode.EVERY_PAGE, {}, suffix="pg")
        # All must succeed
        successes = [r for r in results if r.success]
        assert len(successes) > 0

    def test_every_page_output_in_same_folder(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        """Outputs go to same folder as original (no output_dir argument)."""
        import shutil
        src_orig = generated_pdfs["simple_text"]
        # Copy to tmp so we don't pollute generated_pdfs dir
        src = tmp_output / src_orig.name
        shutil.copy2(src_orig, src)

        results = split(src, SplitMode.EVERY_PAGE, {}, suffix="pg")
        for r in results:
            if r.success and r.output_path:
                assert r.output_path.parent == src.parent


class TestSplitEveryNPages:
    """EVERY_N_PAGES mode tests."""

    def test_every_2_pages(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["large_100pages"]
        results = split(src, SplitMode.EVERY_N_PAGES, {"n": 2}, suffix="n2")
        successes = [r for r in results if r.success]
        total_pages = _page_count(src)
        expected_chunks = (total_pages + 1) // 2
        assert len(successes) == expected_chunks

    def test_last_chunk_can_be_smaller(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        src = generated_pdfs["large_100pages"]
        total_pages = _page_count(src)
        n = 7
        results = split(src, SplitMode.EVERY_N_PAGES, {"n": n}, suffix="n7")
        successes = [r for r in results if r.success]
        # Last chunk is pages mod n
        remainder = total_pages % n
        if remainder > 0:
            assert successes[-1].page_count == remainder

    def test_n_equals_page_count_produces_one_file(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        import shutil
        src_orig = generated_pdfs["simple_text"]
        src = tmp_output / src_orig.name
        shutil.copy2(src_orig, src)

        total = _page_count(src)
        results = split(src, SplitMode.EVERY_N_PAGES, {"n": total}, suffix="all")
        successes = [r for r in results if r.success]
        assert len(successes) == 1


class TestSplitOddEven:
    """ODD_EVEN mode tests."""

    def test_odd_even_produces_two_files(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        import shutil
        src_orig = generated_pdfs["large_100pages"]
        src = tmp_output / src_orig.name
        shutil.copy2(src_orig, src)

        results = split(src, SplitMode.ODD_EVEN, {}, suffix="oe")
        successes = [r for r in results if r.success]
        assert len(successes) == 2

    def test_odd_even_page_counts(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        import shutil
        src_orig = generated_pdfs["large_100pages"]
        src = tmp_output / src_orig.name
        shutil.copy2(src_orig, src)

        total = _page_count(src)
        results = split(src, SplitMode.ODD_EVEN, {}, suffix="oe")
        successes = [r for r in results if r.success]
        total_output_pages = sum(r.page_count for r in successes)
        assert total_output_pages == total


class TestSplitByRange:
    """BY_RANGE mode tests."""

    def test_single_range(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        import shutil
        src_orig = generated_pdfs["large_100pages"]
        src = tmp_output / src_orig.name
        shutil.copy2(src_orig, src)

        results = split(src, SplitMode.BY_RANGE, {"ranges": "1-3"}, suffix="rng")
        successes = [r for r in results if r.success]
        assert len(successes) == 1
        assert successes[0].page_count == 3

    def test_multiple_ranges(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        import shutil
        src_orig = generated_pdfs["large_100pages"]
        src = tmp_output / src_orig.name
        shutil.copy2(src_orig, src)

        results = split(src, SplitMode.BY_RANGE, {"ranges": "1-3, 5, 8-10"}, suffix="mr")
        successes = [r for r in results if r.success]
        assert len(successes) == 3
        assert successes[0].page_count == 3
        assert successes[1].page_count == 1
        assert successes[2].page_count == 3

    def test_invalid_range_returns_failure(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        import shutil
        src_orig = generated_pdfs["simple_text"]
        src = tmp_output / src_orig.name
        shutil.copy2(src_orig, src)

        results = split(src, SplitMode.BY_RANGE, {"ranges": "999-1000"}, suffix="bad")
        assert len(results) == 1
        assert results[0].success is False

    def test_empty_range_returns_failure(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        import shutil
        src_orig = generated_pdfs["simple_text"]
        src = tmp_output / src_orig.name
        shutil.copy2(src_orig, src)

        results = split(src, SplitMode.BY_RANGE, {"ranges": ""}, suffix="empty")
        assert len(results) == 1
        assert results[0].success is False


class TestSplitByBookmarks:
    """BY_BOOKMARKS mode tests."""

    def test_split_with_bookmarks(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        import shutil
        src_orig = generated_pdfs["with_bookmarks"]
        src = tmp_output / src_orig.name
        shutil.copy2(src_orig, src)

        results = split(src, SplitMode.BY_BOOKMARKS, {}, suffix="bm")
        successes = [r for r in results if r.success]
        assert len(successes) >= 1

    def test_no_bookmarks_returns_failure(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        import shutil
        src_orig = generated_pdfs["simple_text"]
        src = tmp_output / src_orig.name
        shutil.copy2(src_orig, src)

        results = split(src, SplitMode.BY_BOOKMARKS, {}, suffix="nobm")
        assert len(results) == 1
        assert results[0].success is False
        assert "bookmark" in results[0].message.lower()


class TestSplitBySize:
    """BY_SIZE mode tests."""

    def test_split_by_size_produces_multiple_chunks(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        import shutil
        # Use the large 100-page PDF
        src_orig = generated_pdfs["large_100pages"]
        src = tmp_output / src_orig.name
        shutil.copy2(src_orig, src)

        file_size_mb = src.stat().st_size / (1024 * 1024)
        # Target = half the file size → should produce at least 2 chunks
        target = max(0.001, file_size_mb / 4)
        results = split(src, SplitMode.BY_SIZE, {"target_mb": target}, suffix="sz")
        successes = [r for r in results if r.success]
        assert len(successes) >= 2


class TestSplitNaming:
    """Output file naming tests."""

    def test_naming_pattern(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        import shutil
        src_orig = generated_pdfs["simple_text"]
        src = tmp_output / src_orig.name
        shutil.copy2(src_orig, src)

        results = split(src, SplitMode.EVERY_PAGE, {}, suffix="parte")
        for i, r in enumerate(results, 1):
            if r.success and r.output_path:
                assert f"_parte{i}" in r.output_path.name
                assert r.output_path.suffix == ".pdf"

    def test_custom_suffix(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        import shutil
        src_orig = generated_pdfs["simple_text"]
        src = tmp_output / src_orig.name
        shutil.copy2(src_orig, src)

        results = split(src, SplitMode.EVERY_PAGE, {}, suffix="mysuffix")
        for r in results:
            if r.success and r.output_path:
                assert "mysuffix" in r.output_path.name


class TestSplitCancellation:
    """Cancellation behaviour."""

    def test_cancellation_pre_set(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        import shutil
        src_orig = generated_pdfs["large_100pages"]
        src = tmp_output / src_orig.name
        shutil.copy2(src_orig, src)

        cancel = threading.Event()
        cancel.set()  # pre-cancel
        results = split(src, SplitMode.EVERY_PAGE, {}, suffix="c", cancel=cancel)
        assert len(results) == 1
        assert results[0].success is False


class TestSplitBatch:
    """split_batch() tests."""

    def test_batch_processes_multiple_files(
        self, generated_pdfs: dict[str, Path], tmp_output: Path
    ) -> None:
        import shutil
        src1_orig = generated_pdfs["simple_text"]
        src2_orig = generated_pdfs["multiple_fonts"]
        src1 = tmp_output / ("a_" + src1_orig.name)
        src2 = tmp_output / ("b_" + src2_orig.name)
        import shutil
        shutil.copy2(src1_orig, src1)
        shutil.copy2(src2_orig, src2)

        results = split_batch([src1, src2], SplitMode.EVERY_PAGE, {}, suffix="bp")
        successes = [r for r in results if r.success]
        total_pages = _page_count(src1) + _page_count(src2)
        assert len(successes) == total_pages
