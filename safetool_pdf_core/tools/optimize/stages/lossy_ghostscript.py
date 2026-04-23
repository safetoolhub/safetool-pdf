# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Lossy optimization via Ghostscript subprocess (font subsetting, full rewrite)."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from safetool_pdf_core.constants import GS_TIMEOUT_SECONDS
from safetool_pdf_core.exceptions import (
    CancellationError,
    GhostscriptError,
    GhostscriptNotFoundError,
    OptimizationError,
)
from safetool_pdf_core.gs_detect import find_gs
from safetool_pdf_core.models import GhostscriptOptions, ProgressInfo

if TYPE_CHECKING:
    from safetool_pdf_core.progress import CancellationToken, ProgressCallback

logger = logging.getLogger(__name__)

def run_ghostscript(
    input_path: Path,
    output_path: Path,
    options: GhostscriptOptions,
    password: str | None = None,
    progress_cb: ProgressCallback | None = None,
    cancel: CancellationToken | None = None,
) -> list[str]:
    """Run Ghostscript for font subsetting / full rewrite.

    Returns a list of warnings (may be empty).

    Raises
    ------
    GhostscriptNotFoundError
        If no usable Ghostscript binary is found.
    GhostscriptError
        If the subprocess exits with an error.
    """
    warnings: list[str] = []

    if not options.enabled:
        import shutil

        shutil.copy2(str(input_path), str(output_path))
        return warnings

    def _progress(msg: str, pct: float) -> None:
        if progress_cb is not None:
            progress_cb(ProgressInfo(stage="ghostscript", message=msg, percent=pct))

    def _check_cancel() -> None:
        if cancel is not None and cancel.is_set():
            raise CancellationError("Operation cancelled during Ghostscript stage.")

    _check_cancel()

    gs_path = find_gs()
    if gs_path is None:
        raise GhostscriptNotFoundError(
            "Ghostscript binary not found. Font subsetting and full rewrite "
            "require Ghostscript to be installed or bundled."
        )

    _progress("Running Ghostscript…", 10)

    # Build argument list
    args: list[str] = [
        str(gs_path),
        "-dSAFER",
        "-dBATCH",
        "-dNOPAUSE",
        "-dQUIET",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.5",
    ]

    # PDF settings preset
    if options.full_rewrite:
        args.append(f"-dPDFSETTINGS={options.gs_settings}")

    # Font subsetting
    if options.font_subsetting:
        args.extend([
            "-dSubsetFonts=true",
            "-dEmbedAllFonts=true",
        ])

    # Password
    if password:
        args.append(f"-sPDFPassword={password}")

    args.extend([
        f"-sOutputFile={output_path}",
        str(input_path),
    ])

    _check_cancel()
    _progress("Ghostscript processing…", 30)

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=GS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise GhostscriptError(
            f"Ghostscript timed out after {GS_TIMEOUT_SECONDS}s"
        ) from exc
    except FileNotFoundError as exc:
        raise GhostscriptNotFoundError(f"Cannot execute GS: {exc}") from exc
    except Exception as exc:
        raise OptimizationError(f"Ghostscript subprocess error: {exc}") from exc

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise GhostscriptError(f"Ghostscript exited with code {result.returncode}: {stderr}")

    # Check output was actually created
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise GhostscriptError("Ghostscript produced no output or an empty file.")

    _progress("Ghostscript stage complete.", 100)
    return warnings
