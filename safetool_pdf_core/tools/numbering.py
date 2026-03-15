# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Numbering tool — stamp a correlative number on page 1 of each PDF."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import fitz  # PyMuPDF

from safetool_pdf_core.exceptions import CancellationError
from safetool_pdf_core.models import ProgressInfo, ToolName, ToolResult
from safetool_pdf_core.naming import output_path_for

if TYPE_CHECKING:
    from safetool_pdf_core.progress import CancellationToken, ProgressCallback

logger = logging.getLogger(__name__)

_STAGE = "numbering"

# Visual defaults
_FONT_SIZE = 24
_FONT_NAME = "helv"  # Helvetica (built-in PDF font)
_COLOR = (1, 0, 0)  # Red
_MARGIN_X = 30  # pts from right edge
_MARGIN_Y = 30  # pts from top edge


def execute(
    input_paths: list[Path],
    output_dir: Path | None = None,
    output_suffix: str = "",
    start_number: int = 1,
    progress_cb: ProgressCallback | None = None,
    cancel: CancellationToken | None = None,
) -> list[ToolResult]:
    """Add a correlative number to the top-right of page 1 of each PDF.

    File *i* receives number ``start_number + i``.
    Returns one ``ToolResult`` per input file.
    """
    results: list[ToolResult] = []
    total = len(input_paths)

    def _progress(msg: str, pct: float, fi: int = 0) -> None:
        if progress_cb is not None:
            progress_cb(ProgressInfo(
                stage=_STAGE, message=msg, percent=pct,
                file_index=fi, file_total=total,
            ))

    for idx, path in enumerate(input_paths):
        if cancel is not None and cancel.is_set():
            results.append(ToolResult(
                tool=ToolName.NUMBER,
                input_paths=[path],
                success=False,
                message="Operation cancelled.",
            ))
            break

        number = start_number + idx
        pct = (idx / total) * 100
        _progress(f"Numbering {path.name} → #{number}", pct, idx + 1)

        if not path.is_file():
            results.append(ToolResult(
                tool=ToolName.NUMBER,
                input_paths=[path],
                success=False,
                message=f"File not found: {path}",
            ))
            continue

        try:
            doc = fitz.open(str(path))
            page = doc[0]  # first page

            # Position: top-right corner
            rect = page.rect
            text = str(number)
            # Measure text width to position from right edge
            text_width = fitz.get_text_length(text, fontname=_FONT_NAME, fontsize=_FONT_SIZE)
            x = rect.width - _MARGIN_X - text_width
            y = _MARGIN_Y + _FONT_SIZE  # baseline position

            page.insert_text(
                (x, y),
                text,
                fontname=_FONT_NAME,
                fontsize=_FONT_SIZE,
                color=_COLOR,
            )

            # Save output
            if output_dir is None:
                out_dir = path.parent
            else:
                out_dir = output_dir
            out_dir.mkdir(parents=True, exist_ok=True)

            out_path = output_path_for(path, output_dir=out_dir, suffix=output_suffix)
            doc.save(str(out_path), deflate=True, garbage=3)
            output_size = out_path.stat().st_size
            page_count = len(doc)
            doc.close()

            results.append(ToolResult(
                tool=ToolName.NUMBER,
                input_paths=[path],
                output_path=out_path,
                success=True,
                message=f"Numbered #{number}",
                original_size=path.stat().st_size,
                output_size=output_size,
                page_count=page_count,
            ))

        except CancellationError:
            results.append(ToolResult(
                tool=ToolName.NUMBER,
                input_paths=[path],
                success=False,
                message="Operation cancelled.",
            ))
            break
        except Exception as exc:
            logger.exception("Numbering failed for %s", path)
            results.append(ToolResult(
                tool=ToolName.NUMBER,
                input_paths=[path],
                success=False,
                message=f"Failed: {exc}",
            ))

    _progress("Numbering complete.", 100, total)
    return results
