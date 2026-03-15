# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Lossless PDF optimization using pikepdf (QPDF wrapper)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pikepdf

from safetool_pdf_core.exceptions import CancellationError, OptimizationError
from safetool_pdf_core.models import LosslessOptions, ProgressInfo

if TYPE_CHECKING:
    from safetool_pdf_core.progress import CancellationToken, ProgressCallback

logger = logging.getLogger(__name__)

def run_lossless(
    input_path: Path,
    output_path: Path,
    options: LosslessOptions,
    password: str | None = None,
    progress_cb: ProgressCallback | None = None,
    cancel: CancellationToken | None = None,
) -> list[str]:
    """Apply lossless optimizations via pikepdf and write to *output_path*.

    Returns a list of warnings (may be empty).
    """
    warnings: list[str] = []

    def _progress(msg: str, pct: float) -> None:
        if progress_cb is not None:
            progress_cb(ProgressInfo(stage="lossless", message=msg, percent=pct))

    def _check_cancel() -> None:
        if cancel is not None and cancel.is_set():
            raise CancellationError("Operation cancelled during lossless stage.")

    _progress("Opening PDF…", 0)
    _check_cancel()

    open_kwargs: dict = {}
    if password:
        open_kwargs["password"] = password

    try:
        pdf = pikepdf.open(str(input_path), **open_kwargs)
    except pikepdf.PasswordError as exc:
        raise OptimizationError(f"Cannot open encrypted PDF: {exc}") from exc
    except Exception as exc:
        raise OptimizationError(f"Failed to open PDF: {exc}") from exc

    try:
        # ---- Remove unreferenced resources --------------------------------
        _check_cancel()
        if options.remove_unreferenced:
            _progress("Removing unreferenced resources…", 10)
            try:
                pdf.remove_unreferenced_resources()
            except Exception as exc:
                logger.warning("remove_unreferenced_resources failed: %s", exc)
                warnings.append(f"Could not remove unreferenced resources: {exc}")

        # ---- Coalesce content streams -------------------------------------
        _check_cancel()
        if options.coalesce_streams:
            _progress("Coalescing page content streams…", 20)
            for page in pdf.pages:
                try:
                    if "/Contents" in page:
                        page.contents_coalesce()
                except Exception as exc:
                    logger.debug("contents_coalesce failed on a page: %s", exc)

        # ---- Externalize inline images ------------------------------------
        _check_cancel()
        if options.externalize_inline_images:
            _progress("Externalizing inline images…", 30)
            for page in pdf.pages:
                try:
                    page.externalize_inline_images()
                except Exception as exc:
                    logger.debug("externalize_inline_images failed on a page: %s", exc)

        # ---- Build save kwargs -------------------------------------------
        _check_cancel()
        _progress("Preparing to write optimized PDF…", 50)

        save_kwargs: dict = {
            "compress_streams": True,
            "preserve_pdfa": True,
        }

        if options.object_stream_mode:
            save_kwargs["object_stream_mode"] = pikepdf.ObjectStreamMode.generate

        if options.recompress_flate:
            save_kwargs["recompress_flate"] = True

        if options.decode_streams:
            # pikepdf decodes and re-encodes automatically with compress_streams
            save_kwargs["stream_decode_level"] = pikepdf.StreamDecodeLevel.generalized

        if options.linearize:
            save_kwargs["linearize"] = True

        # ---- Write -------------------------------------------------------
        _check_cancel()
        _progress("Writing optimized PDF…", 70)
        pdf.save(str(output_path), **save_kwargs)
        _progress("Lossless stage complete.", 100)

    except CancellationError:
        raise
    except Exception as exc:
        raise OptimizationError(f"Lossless optimization failed: {exc}") from exc
    finally:
        pdf.close()

    return warnings
