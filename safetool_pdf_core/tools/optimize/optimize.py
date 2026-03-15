# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Main optimization pipeline — orchestrates analysis → stages → verification."""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from safetool_pdf_core.analyzer import analyze
from safetool_pdf_core.exceptions import (
    CancellationError,
    InvalidPDFError,
    OptimizationError,
    SignedPDFError,
)
from safetool_pdf_core.gs_detect import gs_available
from safetool_pdf_core.models import (
    AnalysisResult,
    OptimizeOptions,
    OptimizeResult,
    PreservationMode,
    ProgressInfo,
)
from safetool_pdf_core.naming import output_path_for

from .stages.cleanup import run_cleanup
from .stages.lossless import run_lossless
from .stages.lossy_ghostscript import run_ghostscript
from .stages.lossy_images import run_lossy_images
from .verifier import verify

if TYPE_CHECKING:
    from safetool_pdf_core.progress import CancellationToken, ProgressCallback

logger = logging.getLogger(__name__)

def optimize(
    input_path: Path | str,
    options: OptimizeOptions | None = None,
    output_dir: Path | str | None = None,
    progress_cb: ProgressCallback | None = None,
    cancel: CancellationToken | None = None,
) -> OptimizeResult:
    """Optimize a single PDF file.

    Pipeline:
    1. Validate input.
    2. Analyse.
    3. Pre-flight checks (signatures, encryption, already-optimized).
    4. Lossless stage (pikepdf).
    5. Lossy images stage (PyMuPDF).
    6. Ghostscript stage (font subsetting / full rewrite).
    7. Cleanup stage.
    8. Verify output.
    9. Move to final destination (atomic).

    Returns
    -------
    OptimizeResult
    """
    from .presets import lossless as lossless_preset

    input_path = Path(input_path)
    output_directory = Path(output_dir) if output_dir else None
    options = options or lossless_preset()
    all_warnings: list[str] = []

    def _emit(stage: str, msg: str, pct: float) -> None:
        if progress_cb:
            progress_cb(ProgressInfo(stage=stage, message=msg, percent=pct))

    def _check_cancel() -> None:
        if cancel and cancel.is_set():
            raise CancellationError("Operation cancelled.")

    # ---- 1. Validate input -----------------------------------------------
    if not input_path.is_file():
        raise InvalidPDFError(f"File not found: {input_path}")
    if input_path.suffix.lower() != ".pdf":
        raise InvalidPDFError(f"Not a PDF file: {input_path}")

    original_size = input_path.stat().st_size
    _emit("init", "Analyzing PDF…", 0)
    _check_cancel()

    # ---- 2. Analyse ------------------------------------------------------
    analysis: AnalysisResult = analyze(input_path, password=options.password)
    all_warnings.extend(analysis.warnings)

    # ---- 3. Pre-flight checks --------------------------------------------
    # Signatures
    if analysis.has_signatures and options.preservation == PreservationMode.SIMPLIFY:
        raise SignedPDFError(
            "This PDF contains digital signatures. Destructive optimizations "
            "would invalidate the signatures. Use 'Preserve' mode or remove "
            "the signatures first."
        )

    # Already optimized
    if analysis.already_optimized:
        all_warnings.append(
            "This PDF appears to be already well-optimized. "
            "Reduction potential is estimated at <5%."
        )

    # GS availability check
    if options.ghostscript.enabled and not gs_available():
        all_warnings.append(
            "Ghostscript not available — font subsetting and full rewrite "
            "will be skipped."
        )
        options.ghostscript.enabled = False

    # PDF/A warning
    if analysis.is_pdfa:
        all_warnings.append(
            f"This PDF claims PDF/A-{analysis.pdfa_level or '?'} conformance. "
            "Some optimizations may break PDF/A compliance."
        )

    # ---- Pipeline execution with temp dir --------------------------------
    _check_cancel()
    tmp_dir = Path(tempfile.mkdtemp(prefix="safetool_pdf_"))

    try:
        current = input_path
        stage_index = 0

        # ---- 4. Lossless -------------------------------------------------
        stage_index += 1
        _emit("lossless", "Running lossless optimization…", 10)
        lossless_out = tmp_dir / f"stage_{stage_index}_lossless.pdf"
        w = run_lossless(
            current, lossless_out, options.lossless,
            password=options.password, progress_cb=progress_cb, cancel=cancel,
        )
        all_warnings.extend(w)
        if lossless_out.is_file() and lossless_out.stat().st_size > 0:
            current = lossless_out

        # ---- 5. Lossy images ---------------------------------------------
        _check_cancel()
        if options.lossy_images.enabled:
            stage_index += 1
            _emit("lossy_images", "Rewriting images…", 35)
            lossy_out = tmp_dir / f"stage_{stage_index}_lossy_images.pdf"
            w = run_lossy_images(
                current, lossy_out, options.lossy_images,
                password=options.password, progress_cb=progress_cb, cancel=cancel,
            )
            all_warnings.extend(w)
            if lossy_out.is_file() and lossy_out.stat().st_size > 0:
                current = lossy_out

        # ---- 6. Ghostscript ----------------------------------------------
        _check_cancel()
        if options.ghostscript.enabled:
            stage_index += 1
            _emit("ghostscript", "Running Ghostscript…", 55)
            gs_out = tmp_dir / f"stage_{stage_index}_ghostscript.pdf"
            w = run_ghostscript(
                current, gs_out, options.ghostscript,
                password=options.password, progress_cb=progress_cb, cancel=cancel,
            )
            all_warnings.extend(w)
            if gs_out.is_file() and gs_out.stat().st_size > 0:
                current = gs_out

        # ---- 7. Cleanup --------------------------------------------------
        _check_cancel()
        stage_index += 1
        _emit("cleanup", "Running cleanup…", 75)
        cleanup_out = tmp_dir / f"stage_{stage_index}_cleanup.pdf"
        w = run_cleanup(
            current, cleanup_out, options.cleanup,
            password=options.password, progress_cb=progress_cb, cancel=cancel,
        )
        all_warnings.extend(w)
        if cleanup_out.is_file() and cleanup_out.stat().st_size > 0:
            current = cleanup_out

        # ---- 8. Verify ---------------------------------------------------
        _check_cancel()
        _emit("verify", "Verifying output…", 90)
        v_warnings = verify(current, analysis.page_count, original_size)
        all_warnings.extend(v_warnings)

        # ---- 9. Move to destination (atomic) -----------------------------
        _emit("finalize", "Moving output file…", 95)
        suffix_kwargs = {}
        if options.output_suffix:
            suffix_kwargs["suffix"] = options.output_suffix
        final_path = output_path_for(input_path, output_dir=output_directory, **suffix_kwargs)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(current), str(final_path))

        optimized_size = final_path.stat().st_size
        reduction = original_size - optimized_size

        result = OptimizeResult(
            input_path=input_path,
            output_path=final_path,
            original_size=original_size,
            optimized_size=optimized_size,
            reduction_bytes=reduction,
            reduction_pct=round((reduction / original_size) * 100, 2) if original_size > 0 else 0.0,
            page_count=analysis.page_count,
            preset=options.preset,
            warnings=all_warnings,
        )

        _emit("done", "Optimization complete.", 100)
        return result

    except CancellationError:
        raise
    except (InvalidPDFError, SignedPDFError, OptimizationError):
        raise
    except Exception as exc:
        raise OptimizationError(f"Optimization pipeline failed: {exc}") from exc
    finally:
        # Clean up temp directory
        shutil.rmtree(tmp_dir, ignore_errors=True)

def optimize_batch(
    input_paths: list[Path],
    options: OptimizeOptions | None = None,
    output_dir: Path | str | None = None,
    progress_cb: ProgressCallback | None = None,
    cancel: CancellationToken | None = None,
) -> list[OptimizeResult]:
    """Optimize multiple PDF files sequentially.

    Files are processed one at a time (no parallelism) for stability with
    large PDFs.
    """
    results: list[OptimizeResult] = []
    total = len(input_paths)

    for idx, path in enumerate(input_paths, 1):
        if cancel and cancel.is_set():
            break

        def _batch_progress(info: ProgressInfo) -> None:
            info.file_index = idx
            info.file_total = total
            if progress_cb:
                progress_cb(info)

        try:
            result = optimize(
                path,
                options=options,
                output_dir=output_dir,
                progress_cb=_batch_progress,
                cancel=cancel,
            )
            results.append(result)
        except CancellationError:
            break
        except Exception as exc:
            logger.error("Failed to optimize %s: %s", path, exc)
            results.append(
                OptimizeResult(
                    input_path=path,
                    output_path=path,
                    skipped=True,
                    skipped_reason=str(exc),
                    warnings=[str(exc)],
                )
            )

    return results
