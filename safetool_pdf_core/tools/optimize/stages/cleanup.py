# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Selective cleanup — metadata, attachments, JS, thumbnails, forms, etc."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import fitz  # PyMuPDF
import pikepdf

from safetool_pdf_core.exceptions import CancellationError, OptimizationError
from safetool_pdf_core.models import CleanupOptions, ProgressInfo

if TYPE_CHECKING:
    from safetool_pdf_core.progress import CancellationToken, ProgressCallback

logger = logging.getLogger(__name__)

def run_cleanup(
    input_path: Path,
    output_path: Path,
    options: CleanupOptions,
    password: str | None = None,
    progress_cb: ProgressCallback | None = None,
    cancel: CancellationToken | None = None,
) -> list[str]:
    """Apply selective cleanup operations.

    Returns a list of warnings (may be empty).
    """
    warnings: list[str] = []

    # Quick check: anything to do?
    if not _any_cleanup_needed(options):
        import shutil

        shutil.copy2(str(input_path), str(output_path))
        return warnings

    def _progress(msg: str, pct: float) -> None:
        if progress_cb is not None:
            progress_cb(ProgressInfo(stage="cleanup", message=msg, percent=pct))

    def _check_cancel() -> None:
        if cancel is not None and cancel.is_set():
            raise CancellationError("Operation cancelled during cleanup stage.")

    # ------------------------------------------------------------------
    # Phase A: pikepdf-based structural cleanup
    # ------------------------------------------------------------------
    _check_cancel()
    _progress("Opening PDF for cleanup…", 0)

    open_kwargs: dict = {}
    if password:
        open_kwargs["password"] = password

    try:
        pdf = pikepdf.open(str(input_path), **open_kwargs)
    except Exception as exc:
        raise OptimizationError(f"Failed to open PDF for cleanup: {exc}") from exc

    try:
        root = pdf.Root

        # Metadata
        if options.remove_metadata:
            _check_cancel()
            _progress("Removing metadata…", 10)
            _remove_metadata(pdf, root, warnings)

        # Attachments
        if options.remove_attachments:
            _check_cancel()
            _progress("Removing attachments…", 20)
            _remove_attachments(root, warnings)

        # JavaScript
        if options.remove_javascript:
            _check_cancel()
            _progress("Removing JavaScript…", 30)
            _remove_javascript(root, warnings)

        # Thumbnails
        if options.remove_thumbnails:
            _check_cancel()
            _progress("Removing thumbnails…", 40)
            _remove_thumbnails(pdf, warnings)

        # Bookmarks
        if options.remove_bookmarks:
            _check_cancel()
            _progress("Removing bookmarks…", 50)
            _remove_bookmarks(root, warnings)

        # Layers (OCG)
        if options.flatten_layers:
            _check_cancel()
            _progress("Removing layer definitions…", 55)
            _remove_layers(root, warnings)

        # Accessibility tags
        if options.remove_accessibility_tags:
            _check_cancel()
            _progress("Removing accessibility tags…", 60)
            _remove_accessibility(root, warnings)

        # Links
        if options.remove_links:
            _check_cancel()
            _progress("Removing links…", 65)
            # Links are annotation subtypes — handled in PyMuPDF phase below
            pass

        _check_cancel()
        _progress("Saving after pikepdf cleanup…", 70)

        # Save intermediate
        intermediate = output_path.with_suffix(".cleanup_tmp.pdf")
        pdf.save(str(intermediate), compress_streams=True)

    except CancellationError:
        raise
    except Exception as exc:
        raise OptimizationError(f"Cleanup (pikepdf) failed: {exc}") from exc
    finally:
        pdf.close()

    # ------------------------------------------------------------------
    # Phase B: PyMuPDF-based cleanup (forms, annotations)
    # ------------------------------------------------------------------
    needs_pymupdf = (
        options.flatten_forms
        or options.flatten_annotations
        or options.remove_links
    )

    if needs_pymupdf:
        _check_cancel()
        _progress("Flattening forms/annotations…", 75)

        try:
            doc = fitz.open(str(intermediate))
        except Exception as exc:
            # Fall back — just rename intermediate
            intermediate.rename(output_path)
            warnings.append(f"PyMuPDF cleanup failed: {exc}")
            return warnings

        try:
            for page in doc:
                annots_to_delete: list = []
                for annot in page.annots() or []:
                    subtype = annot.type[1] if annot.type else ""

                    # Flatten forms (Widget annotations)
                    if options.flatten_forms and subtype == "Widget":
                        annots_to_delete.append(annot)
                        continue

                    # Remove links
                    if options.remove_links and subtype == "Link":
                        annots_to_delete.append(annot)
                        continue

                    # Flatten all other annotations
                    if options.flatten_annotations and subtype not in ("Widget", "Link"):
                        annots_to_delete.append(annot)
                        continue

                # Delete collected annotations
                for annot in reversed(annots_to_delete):
                    page.delete_annot(annot)

            doc.save(str(output_path), deflate=True, garbage=3)
        except Exception as exc:
            warnings.append(f"Annotation cleanup failed: {exc}")
            # Use intermediate output
            if not output_path.is_file():
                intermediate.rename(output_path)
        finally:
            doc.close()

        # Clean up intermediate
        if intermediate.is_file():
            intermediate.unlink(missing_ok=True)
    else:
        # No PyMuPDF phase needed — rename intermediate to output
        intermediate.rename(output_path)

    _progress("Cleanup stage complete.", 100)
    return warnings

# ---------------------------------------------------------------------------
# pikepdf cleanup helpers
# ---------------------------------------------------------------------------

def _remove_metadata(pdf: pikepdf.Pdf, root: pikepdf.Dictionary, warnings: list[str]) -> None:
    """Remove XMP metadata and DocInfo (preserve title)."""
    try:
        # Preserve title from DocInfo if present
        title = ""
        if pdf.docinfo and "/Title" in pdf.docinfo:
            title = str(pdf.docinfo["/Title"])

        # Clear DocInfo
        pdf.docinfo.clear()
        if title:
            pdf.docinfo["/Title"] = title

        # Remove XMP metadata stream
        if "/Metadata" in root:
            del root["/Metadata"]

    except Exception as exc:
        logger.debug("Metadata removal: %s", exc)
        warnings.append(f"Partial metadata removal: {exc}")

def _remove_attachments(root: pikepdf.Dictionary, warnings: list[str]) -> None:
    """Remove embedded files."""
    try:
        if "/Names" in root:
            names = root["/Names"]
            if "/EmbeddedFiles" in names:
                del names["/EmbeddedFiles"]
    except Exception as exc:
        warnings.append(f"Attachment removal failed: {exc}")

def _remove_javascript(root: pikepdf.Dictionary, warnings: list[str]) -> None:
    """Remove JavaScript from /Names and /OpenAction."""
    try:
        if "/Names" in root:
            names = root["/Names"]
            if "/JavaScript" in names:
                del names["/JavaScript"]
        if "/OpenAction" in root:
            oa = root["/OpenAction"]
            if isinstance(oa, pikepdf.Dictionary) and "/S" in oa:
                if str(oa["/S"]) == "/JavaScript":
                    del root["/OpenAction"]
    except Exception as exc:
        warnings.append(f"JavaScript removal failed: {exc}")

def _remove_thumbnails(pdf: pikepdf.Pdf, warnings: list[str]) -> None:
    """Remove embedded page thumbnails."""
    try:
        for page in pdf.pages:
            if "/Thumb" in page:
                del page["/Thumb"]
    except Exception as exc:
        warnings.append(f"Thumbnail removal failed: {exc}")

def _remove_bookmarks(root: pikepdf.Dictionary, warnings: list[str]) -> None:
    """Remove the document outline (bookmarks/TOC)."""
    try:
        if "/Outlines" in root:
            del root["/Outlines"]
    except Exception as exc:
        warnings.append(f"Bookmark removal failed: {exc}")

def _remove_layers(root: pikepdf.Dictionary, warnings: list[str]) -> None:
    """Remove OCG (layer) definitions."""
    try:
        if "/OCProperties" in root:
            del root["/OCProperties"]
    except Exception as exc:
        warnings.append(f"Layer removal failed: {exc}")

def _remove_accessibility(root: pikepdf.Dictionary, warnings: list[str]) -> None:
    """Remove structural accessibility tags."""
    try:
        if "/StructTreeRoot" in root:
            del root["/StructTreeRoot"]
        if "/MarkInfo" in root:
            del root["/MarkInfo"]
    except Exception as exc:
        warnings.append(f"Accessibility removal failed: {exc}")

def _any_cleanup_needed(options: CleanupOptions) -> bool:
    """Return True if at least one cleanup toggle is active."""
    return any(
        [
            options.remove_metadata,
            options.remove_attachments,
            options.remove_javascript,
            options.remove_thumbnails,
            options.flatten_forms,
            options.flatten_layers,
            options.remove_accessibility_tags,
            options.remove_bookmarks,
            options.remove_links,
            options.flatten_annotations,
        ]
    )
