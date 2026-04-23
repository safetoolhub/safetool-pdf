# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Metadata removal tool — strip all metadata from PDFs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pikepdf

from safetool_pdf_core.exceptions import CancellationError
from safetool_pdf_core.models import ProgressInfo, ToolName, ToolResult
from safetool_pdf_core.naming import output_path_for

if TYPE_CHECKING:
    from safetool_pdf_core.progress import CancellationToken, ProgressCallback

logger = logging.getLogger(__name__)

_STAGE = "strip_metadata"


def execute(
    input_paths: list[Path],
    output_dir: Path | None = None,
    output_suffix: str = "",
    progress_cb: ProgressCallback | None = None,
    cancel: CancellationToken | None = None,
) -> list[ToolResult]:
    """Remove all metadata from each input PDF.

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
                tool=ToolName.STRIP_METADATA,
                input_paths=[path],
                success=False,
                message="Operation cancelled.",
            ))
            break

        pct = (idx / total) * 100
        _progress(f"Stripping metadata from {path.name}", pct, idx + 1)

        if not path.is_file():
            results.append(ToolResult(
                tool=ToolName.STRIP_METADATA,
                input_paths=[path],
                success=False,
                message=f"File not found: {path}",
            ))
            continue

        try:
            pdf = pikepdf.open(str(path))

            # Clear DocInfo dictionary
            if "/Info" in pdf.trailer:
                del pdf.trailer["/Info"]

            # Remove XMP metadata stream
            root = pdf.Root
            if "/Metadata" in root:
                del root["/Metadata"]

            # Save output
            if output_dir is None:
                out_dir = path.parent
            else:
                out_dir = output_dir
            out_dir.mkdir(parents=True, exist_ok=True)

            out_path = output_path_for(path, output_dir=out_dir, suffix=output_suffix)
            pdf.save(str(out_path), compress_streams=True)
            output_size = out_path.stat().st_size
            page_count = len(pdf.pages)
            pdf.close()

            results.append(ToolResult(
                tool=ToolName.STRIP_METADATA,
                input_paths=[path],
                output_path=out_path,
                success=True,
                message=f"Metadata removed from {path.name}",
                original_size=path.stat().st_size,
                output_size=output_size,
                page_count=page_count,
            ))

        except CancellationError:
            results.append(ToolResult(
                tool=ToolName.STRIP_METADATA,
                input_paths=[path],
                success=False,
                message="Operation cancelled.",
            ))
            break
        except Exception as exc:
            logger.exception("Metadata removal failed for %s", path)
            results.append(ToolResult(
                tool=ToolName.STRIP_METADATA,
                input_paths=[path],
                success=False,
                message=f"Failed: {exc}",
            ))

    _progress("Metadata removal complete.", 100, total)
    return results
