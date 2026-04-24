# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Split tool — divide a PDF into multiple files using various strategies."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pikepdf

from safetool_pdf_core.exceptions import CancellationError, InvalidPDFError
from safetool_pdf_core.models import ProgressInfo, SplitMode, ToolName, ToolResult

if TYPE_CHECKING:
    from safetool_pdf_core.progress import CancellationToken, ProgressCallback

logger = logging.getLogger(__name__)

_STAGE = "split"


# ---------------------------------------------------------------------------
# Range parsing helpers
# ---------------------------------------------------------------------------

def parse_ranges(text: str, page_count: int) -> list[list[int]]:
    """Parse a human-readable page range string into groups of 0-based page indices.

    Syntax (1-based page numbers):
        "1-3"         → [[0, 1, 2]]
        "1-3, 5"      → [[0, 1, 2], [4]]
        "1-3, 5, 8-10" → [[0, 1, 2], [4], [7, 8, 9]]
        "2"           → [[1]]

    Parameters
    ----------
    text:
        User-supplied range string.
    page_count:
        Total number of pages in the PDF (for bounds validation).

    Returns
    -------
    list[list[int]]
        Each element is a list of 0-based page indices forming one output chunk.

    Raises
    ------
    ValueError
        If the text is malformed or any page number is out of range.
    """
    text = text.strip()
    if not text:
        raise ValueError("Page range is empty.")

    groups: list[list[int]] = []
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        raise ValueError("Page range is empty.")

    range_re = re.compile(r"^(\d+)(?:-(\d+))?$")
    for part in parts:
        m = range_re.match(part)
        if not m:
            raise ValueError(
                f"Invalid range token '{part}'. Expected a page number or range like '1-3'."
            )
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else start

        if start < 1:
            raise ValueError(f"Page number {start} is less than 1.")
        if end < start:
            raise ValueError(
                f"Range end {end} is less than range start {start}."
            )
        if end > page_count:
            raise ValueError(
                f"Page {end} is out of range (document has {page_count} page(s))."
            )

        groups.append(list(range(start - 1, end)))  # convert to 0-based

    return groups


def estimate_chunk_count(
    page_count: int,
    file_size: int,
    mode: SplitMode,
    options: dict,
) -> int:
    """Estimate how many output chunks will be produced.

    This is used by the UI preview table; it does not open the file.

    Returns
    -------
    int
        Estimated number of output files. Returns 0 when estimation is not
        possible (e.g. BY_BOOKMARKS requires prior analysis).
    """
    if page_count <= 0:
        return 0

    if mode == SplitMode.EVERY_PAGE:
        return page_count

    if mode == SplitMode.EVERY_N_PAGES:
        n = max(1, options.get("n", 1))
        return (page_count + n - 1) // n

    if mode == SplitMode.ODD_EVEN:
        odds = (page_count + 1) // 2
        evens = page_count // 2
        # Only 2 outputs even if one side would be empty
        return 2 if odds > 0 and evens > 0 else 1

    if mode == SplitMode.BY_RANGE:
        ranges_text = options.get("ranges", "")
        try:
            return len(parse_ranges(ranges_text, page_count))
        except ValueError:
            return 0

    if mode == SplitMode.BY_BOOKMARKS:
        # Need the actual bookmark list; unknown until file is analysed
        return options.get("bookmark_count", 0)

    if mode == SplitMode.BY_SIZE:
        target_mb = options.get("target_mb", 1.0)
        if target_mb <= 0 or file_size <= 0:
            return 0
        target_bytes = target_mb * 1024 * 1024
        # Naive proportional estimate: assume uniform page size
        size_per_page = file_size / page_count
        pages_per_chunk = max(1, int(target_bytes / size_per_page))
        return (page_count + pages_per_chunk - 1) // pages_per_chunk

    return 0


# ---------------------------------------------------------------------------
# Output naming
# ---------------------------------------------------------------------------

def _split_output_path(
    original: Path,
    suffix: str,
    chunk_index: int,
) -> Path:
    """Build a collision-safe output path for one split chunk.

    Pattern: ``{stem}_{suffix}{N}.pdf`` (N is 1-based).
    Collisions are avoided by appending ``_(2)``, ``_(3)``, etc.
    """
    stem = original.stem
    directory = original.parent
    base_name = f"{stem}_{suffix}{chunk_index}"
    candidate = directory / f"{base_name}.pdf"
    if not candidate.exists():
        return candidate
    counter = 2
    while True:
        candidate = directory / f"{base_name}_({counter}).pdf"
        if not candidate.exists():
            return candidate
        counter += 1
        if counter > 9999:
            raise RuntimeError("Too many output file collisions.")


# ---------------------------------------------------------------------------
# Core split logic
# ---------------------------------------------------------------------------

def _write_chunk(
    source: pikepdf.Pdf,
    page_indices: list[int],
    out_path: Path,
) -> None:
    """Write a subset of *source* pages to *out_path*."""
    chunk = pikepdf.Pdf.new()
    for idx in page_indices:
        chunk.pages.append(source.pages[idx])
    chunk.save(str(out_path))
    chunk.close()


def _split_by_chunks(
    source: pikepdf.Pdf,
    chunks: list[list[int]],
    original: Path,
    suffix: str,
    tool_results_so_far: list[ToolResult],
    progress_cb: ProgressCallback | None,
    cancel: CancellationToken | None,
    total_chunks: int,
    base_chunk_index: int = 0,
) -> list[ToolResult]:
    """Write *chunks* as individual PDFs and return ToolResults."""
    results: list[ToolResult] = []
    original_size = original.stat().st_size

    for i, page_indices in enumerate(chunks):
        if cancel is not None and cancel.is_set():
            raise CancellationError("Operation cancelled during split.")

        chunk_num = base_chunk_index + i + 1
        out_path = _split_output_path(original, suffix, chunk_num)

        if progress_cb is not None:
            progress_cb(ProgressInfo(
                stage=_STAGE,
                message=f"Writing chunk {chunk_num}/{total_chunks}…",
                percent=((len(tool_results_so_far) + i) / total_chunks) * 100,
            ))

        _write_chunk(source, page_indices, out_path)
        output_size = out_path.stat().st_size

        results.append(ToolResult(
            tool=ToolName.SPLIT,
            input_paths=[original],
            output_path=out_path,
            success=True,
            message=f"Pages {min(p+1 for p in page_indices)}–{max(p+1 for p in page_indices)} → {out_path.name}",
            original_size=original_size,
            output_size=output_size,
            page_count=len(page_indices),
        ))

    return results


def split(
    input_path: Path,
    mode: SplitMode,
    options: dict,
    suffix: str = "parte",
    progress_cb: ProgressCallback | None = None,
    cancel: CancellationToken | None = None,
) -> list[ToolResult]:
    """Split *input_path* according to *mode* and *options*.

    Parameters
    ----------
    input_path:
        Source PDF file.
    mode:
        Split strategy (``SplitMode`` enum value).
    options:
        Mode-specific settings:
        - ``EVERY_N_PAGES``: ``{"n": int}``
        - ``BY_RANGE``:       ``{"ranges": "1-3, 5, 8-10"}``
        - ``BY_BOOKMARKS``:   *(no options needed)*
        - ``BY_SIZE``:        ``{"target_mb": float}``
        - ``EVERY_PAGE`` / ``ODD_EVEN``: *(no options needed)*
    suffix:
        String inserted between the file stem and the chunk number in output names.
    progress_cb:
        Optional progress callback.
    cancel:
        Optional cancellation token.

    Returns
    -------
    list[ToolResult]
        One ToolResult per output chunk. Returns a single failure ToolResult on error.
    """
    if not input_path.is_file():
        return [ToolResult(
            tool=ToolName.SPLIT,
            input_paths=[input_path],
            success=False,
            message=f"File not found: {input_path}",
        )]

    def _check_cancel() -> None:
        if cancel is not None and cancel.is_set():
            raise CancellationError("Operation cancelled.")

    def _progress(msg: str, pct: float) -> None:
        if progress_cb is not None:
            progress_cb(ProgressInfo(stage=_STAGE, message=msg, percent=pct))

    try:
        _check_cancel()
        _progress("Opening PDF…", 0)

        try:
            src = pikepdf.open(str(input_path))
        except Exception as exc:
            return [ToolResult(
                tool=ToolName.SPLIT,
                input_paths=[input_path],
                success=False,
                message=f"Cannot open PDF: {exc}",
            )]

        page_count = len(src.pages)
        if page_count == 0:
            src.close()
            return [ToolResult(
                tool=ToolName.SPLIT,
                input_paths=[input_path],
                success=False,
                message="PDF has no pages.",
            )]

        chunks: list[list[int]] = []

        # ── Build chunk list per mode ──

        if mode == SplitMode.EVERY_PAGE:
            chunks = [[i] for i in range(page_count)]

        elif mode == SplitMode.EVERY_N_PAGES:
            n = max(1, options.get("n", 1))
            chunks = [
                list(range(start, min(start + n, page_count)))
                for start in range(0, page_count, n)
            ]

        elif mode == SplitMode.ODD_EVEN:
            odds = [i for i in range(page_count) if i % 2 == 0]   # 0-based: 0,2,4… = pages 1,3,5…
            evens = [i for i in range(page_count) if i % 2 == 1]  # 0-based: 1,3,5… = pages 2,4,6…
            if odds:
                chunks.append(odds)
            if evens:
                chunks.append(evens)

        elif mode == SplitMode.BY_RANGE:
            ranges_text = options.get("ranges", "")
            try:
                chunks = parse_ranges(ranges_text, page_count)
            except ValueError as exc:
                src.close()
                return [ToolResult(
                    tool=ToolName.SPLIT,
                    input_paths=[input_path],
                    success=False,
                    message=f"Invalid page range: {exc}",
                )]

        elif mode == SplitMode.BY_BOOKMARKS:
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(str(input_path))
                toc = doc.get_toc(simple=True)
                doc.close()
            except Exception as exc:
                src.close()
                return [ToolResult(
                    tool=ToolName.SPLIT,
                    input_paths=[input_path],
                    success=False,
                    message=f"Could not read bookmarks: {exc}",
                )]

            # Keep only top-level bookmarks (level == 1)
            top_level = [entry for entry in toc if entry[0] == 1]
            if not top_level:
                src.close()
                return [ToolResult(
                    tool=ToolName.SPLIT,
                    input_paths=[input_path],
                    success=False,
                    message="No top-level bookmarks found. Cannot split by bookmarks.",
                )]

            # Build page ranges from bookmark start pages
            bookmark_starts = [entry[2] - 1 for entry in top_level]  # 1-based → 0-based
            bookmark_starts = [max(0, min(p, page_count - 1)) for p in bookmark_starts]

            for i, start in enumerate(bookmark_starts):
                end = bookmark_starts[i + 1] if i + 1 < len(bookmark_starts) else page_count
                if start < end:
                    chunks.append(list(range(start, end)))

            if not chunks:
                src.close()
                return [ToolResult(
                    tool=ToolName.SPLIT,
                    input_paths=[input_path],
                    success=False,
                    message="Bookmark ranges produced no valid chunks.",
                )]

        elif mode == SplitMode.BY_SIZE:
            target_mb = max(0.001, options.get("target_mb", 1.0))
            target_bytes = target_mb * 1024 * 1024
            file_size = input_path.stat().st_size
            # Proportional estimate: assume pages have roughly equal size
            size_per_page = max(1, file_size / page_count)
            pages_per_chunk = max(1, int(target_bytes / size_per_page))
            chunks = [
                list(range(start, min(start + pages_per_chunk, page_count)))
                for start in range(0, page_count, pages_per_chunk)
            ]

        else:
            src.close()
            return [ToolResult(
                tool=ToolName.SPLIT,
                input_paths=[input_path],
                success=False,
                message=f"Unknown split mode: {mode}",
            )]

        if not chunks:
            src.close()
            return [ToolResult(
                tool=ToolName.SPLIT,
                input_paths=[input_path],
                success=False,
                message="No chunks produced with the given settings.",
            )]

        _check_cancel()
        total = len(chunks)
        results = _split_by_chunks(
            source=src,
            chunks=chunks,
            original=input_path,
            suffix=suffix,
            tool_results_so_far=[],
            progress_cb=progress_cb,
            cancel=cancel,
            total_chunks=total,
        )
        src.close()

        _progress("Done.", 100)
        return results

    except CancellationError:
        return [ToolResult(
            tool=ToolName.SPLIT,
            input_paths=[input_path],
            success=False,
            message="Operation cancelled.",
        )]
    except Exception as exc:
        logger.exception("Unexpected error during split of %s", input_path)
        return [ToolResult(
            tool=ToolName.SPLIT,
            input_paths=[input_path],
            success=False,
            message=f"Unexpected error: {exc}",
        )]


def split_batch(
    files: list[Path],
    mode: SplitMode,
    options: dict,
    suffix: str = "parte",
    progress_cb: ProgressCallback | None = None,
    cancel: CancellationToken | None = None,
) -> list[ToolResult]:
    """Split each file in *files* and return the combined results.

    Progress is reported as a fraction of total files processed.
    """
    all_results: list[ToolResult] = []
    total = len(files)

    for file_idx, path in enumerate(files):
        if cancel is not None and cancel.is_set():
            all_results.append(ToolResult(
                tool=ToolName.SPLIT,
                input_paths=[path],
                success=False,
                message="Operation cancelled.",
            ))
            continue

        def _file_progress(info: ProgressInfo, _idx: int = file_idx) -> None:
            if progress_cb is not None:
                # Re-scale per-file 0-100 into overall fraction
                overall_pct = (_idx / total) * 100 + (info.percent / total)
                progress_cb(ProgressInfo(
                    stage=info.stage,
                    message=info.message,
                    percent=overall_pct,
                    file_index=_idx + 1,
                    file_total=total,
                ))

        results = split(
            input_path=path,
            mode=mode,
            options=options,
            suffix=suffix,
            progress_cb=_file_progress,
            cancel=cancel,
        )
        all_results.extend(results)

    return all_results
