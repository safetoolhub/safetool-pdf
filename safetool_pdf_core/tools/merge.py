# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Merge tool — combine multiple PDFs into a single file."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pikepdf

from safetool_pdf_core.exceptions import CancellationError, InvalidPDFError
from safetool_pdf_core.models import ProgressInfo, ToolName, ToolResult
from safetool_pdf_core.naming import output_path_for

if TYPE_CHECKING:
    from safetool_pdf_core.progress import CancellationToken, ProgressCallback

logger = logging.getLogger(__name__)

_STAGE = "merge"


def execute(
    input_paths: list[Path],
    output_dir: Path | None = None,
    output_suffix: str = "",
    output_filename: str = "merged",
    progress_cb: ProgressCallback | None = None,
    cancel: CancellationToken | None = None,
) -> list[ToolResult]:
    """Merge *input_paths* (in order) into a single PDF.

    Returns a list containing one ``ToolResult``.
    """
    if len(input_paths) < 2:
        return [ToolResult(
            tool=ToolName.MERGE,
            input_paths=list(input_paths),
            success=False,
            message="At least 2 PDF files are required for merging.",
        )]

    def _progress(msg: str, pct: float) -> None:
        if progress_cb is not None:
            progress_cb(ProgressInfo(stage=_STAGE, message=msg, percent=pct))

    def _check_cancel() -> None:
        if cancel is not None and cancel.is_set():
            raise CancellationError("Operation cancelled during merge.")

    warnings: list[str] = []
    total_original_size = 0

    try:
        _check_cancel()
        _progress("Opening target PDF…", 0)
        merged = pikepdf.Pdf.new()
        total = len(input_paths)

        for idx, path in enumerate(input_paths):
            _check_cancel()
            pct = (idx / total) * 90
            _progress(f"Adding {path.name} ({idx + 1}/{total})…", pct)

            if not path.is_file():
                warnings.append(f"File not found, skipped: {path}")
                continue
            try:
                total_original_size += path.stat().st_size
                src = pikepdf.open(str(path))
                merged.pages.extend(src.pages)
            except Exception as exc:
                warnings.append(f"Could not read {path.name}: {exc}")

        if len(merged.pages) == 0:
            return [ToolResult(
                tool=ToolName.MERGE,
                input_paths=list(input_paths),
                success=False,
                message="No pages could be read from the input files.",
                warnings=warnings,
            )]

        _check_cancel()
        _progress("Saving merged PDF…", 90)

        # Determine output path
        if output_dir is None:
            output_dir = input_paths[0].parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # Ensure filename has .pdf extension
        if not output_filename.endswith('.pdf'):
            output_filename = f"{output_filename}.pdf"

        out_path = output_path_for(
            Path(output_dir / output_filename),
            output_dir=output_dir,
            suffix=output_suffix,
        )
        merged.save(str(out_path))
        page_count = len(merged.pages)
        merged.close()

        output_size = out_path.stat().st_size

        _progress("Merge complete.", 100)

        return [ToolResult(
            tool=ToolName.MERGE,
            input_paths=list(input_paths),
            output_path=out_path,
            success=True,
            message=f"Merged {total} files into {out_path.name}",
            warnings=warnings,
            original_size=total_original_size,
            output_size=output_size,
            page_count=page_count,
        )]

    except CancellationError:
        return [ToolResult(
            tool=ToolName.MERGE,
            input_paths=list(input_paths),
            success=False,
            message="Operation cancelled.",
            warnings=warnings,
        )]
    except Exception as exc:
        logger.exception("Merge failed")
        return [ToolResult(
            tool=ToolName.MERGE,
            input_paths=list(input_paths),
            success=False,
            message=f"Merge failed: {exc}",
            warnings=warnings,
        )]
