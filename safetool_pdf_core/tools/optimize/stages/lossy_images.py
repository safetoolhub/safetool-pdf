# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Lossy image optimization stage using PyMuPDF ``rewrite_images()``."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import fitz  # PyMuPDF

from safetool_pdf_core.exceptions import CancellationError, OptimizationError
from safetool_pdf_core.models import LossyImageOptions, ProgressInfo

if TYPE_CHECKING:
    from safetool_pdf_core.progress import CancellationToken, ProgressCallback

logger = logging.getLogger(__name__)

def run_lossy_images(
    input_path: Path,
    output_path: Path,
    options: LossyImageOptions,
    password: str | None = None,
    progress_cb: ProgressCallback | None = None,
    cancel: CancellationToken | None = None,
) -> list[str]:
    """Down-sample and recompress images via PyMuPDF.

    The function opens *input_path*, rewrites images according to *options*,
    and saves the result to *output_path*.

    Returns a list of warnings (may be empty).
    """
    warnings: list[str] = []

    if not options.enabled:
        # Nothing to do — just copy the file
        import shutil

        shutil.copy2(str(input_path), str(output_path))
        return warnings

    def _progress(msg: str, pct: float) -> None:
        if progress_cb is not None:
            progress_cb(ProgressInfo(stage="lossy_images", message=msg, percent=pct))

    def _check_cancel() -> None:
        if cancel is not None and cancel.is_set():
            raise CancellationError("Operation cancelled during lossy images stage.")

    _progress("Opening PDF for image rewrite…", 0)
    _check_cancel()

    try:
        doc: fitz.Document = fitz.open(str(input_path))
        if doc.needs_pass and password:
            doc.authenticate(password)
    except Exception as exc:
        raise OptimizationError(f"Failed to open PDF for image rewrite: {exc}") from exc

    try:
        _check_cancel()
        _progress("Rewriting images…", 20)

        # Build rewrite_images kwargs based on options
        rewrite_kwargs: dict = {}

        # DPI settings: dpi_target is the output DPI; dpi_threshold is the
        # minimum current DPI that triggers resampling.  PyMuPDF requires
        # dpi_target < dpi_threshold, so we set threshold = target + 1 which
        # means "downsample any image above target_dpi down to target_dpi".
        if options.target_dpi > 0:
            rewrite_kwargs["dpi_target"] = options.target_dpi
            rewrite_kwargs["dpi_threshold"] = options.target_dpi + 1

        # JPEG quality (1–100)
        if options.jpeg_quality > 0:
            rewrite_kwargs["quality"] = options.jpeg_quality

        # Bitonal handling (CCITT Group 4 for mono images)
        if options.ccitt_bitonal:
            rewrite_kwargs["bitonal"] = True

        _check_cancel()
        _progress("Applying image rewrite…", 40)

        try:
            doc.rewrite_images(**rewrite_kwargs)
        except AttributeError:
            # Fallback for older PyMuPDF versions without rewrite_images
            warnings.append(
                "PyMuPDF version does not support rewrite_images(); "
                "lossy image optimization skipped."
            )
            logger.warning("rewrite_images() not available — skipping.")
            doc.save(str(output_path), deflate=True, garbage=3)
            return warnings
        except Exception as exc:
            warnings.append(f"Image rewrite encountered an error: {exc}")
            logger.warning("rewrite_images() failed: %s", exc)

        _check_cancel()
        _progress("Saving rewritten PDF…", 80)

        doc.save(
            str(output_path),
            deflate=True,
            garbage=3,
            clean=True,
        )

        _progress("Lossy images stage complete.", 100)

    except CancellationError:
        raise
    except Exception as exc:
        raise OptimizationError(f"Lossy image optimization failed: {exc}") from exc
    finally:
        doc.close()

    return warnings
