# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""PDF analysis using PyMuPDF (fitz) and pikepdf."""

from __future__ import annotations

import logging
from pathlib import Path

import fitz  # PyMuPDF
import pikepdf

from safetool_pdf_core.exceptions import AnalysisError, InvalidPDFError
from safetool_pdf_core.models import AnalysisResult, FontInfo, ImageInfo

logger = logging.getLogger(__name__)

def analyze(path: Path | str, password: str | None = None) -> AnalysisResult:
    """Perform a full analysis of a PDF file.

    Parameters
    ----------
    path:
        Path to the PDF file.
    password:
        Optional password if the PDF is encrypted.

    Returns
    -------
    AnalysisResult
        Comprehensive analysis of the PDF contents and structure.

    Raises
    ------
    InvalidPDFError
        If the file is not a valid PDF or cannot be read.
    AnalysisError
        On any other analysis failure.
    """
    path = Path(path)
    if not path.is_file():
        raise InvalidPDFError(f"File not found: {path}")

    result = AnalysisResult(path=path, file_size=path.stat().st_size)

    try:
        _analyze_with_pymupdf(result, password)
    except InvalidPDFError:
        # Re-raise InvalidPDFError as-is
        raise
    except PermissionError as exc:
        raise InvalidPDFError(f"Permission denied reading file: {path}") from exc
    except OSError as exc:
        raise InvalidPDFError(f"Cannot read file: {path} - {exc}") from exc
    except Exception as exc:
        # Check if it's a PyMuPDF error indicating invalid PDF
        exc_str = str(exc).lower()
        if any(keyword in exc_str for keyword in ["not a pdf", "invalid pdf", "cannot open", "damaged", "corrupted", "failed to open"]):
            raise InvalidPDFError(f"Invalid or corrupted PDF file: {path}") from exc
        raise AnalysisError(f"PyMuPDF analysis failed: {exc}") from exc

    try:
        _analyze_with_pikepdf(result, password)
    except Exception as exc:
        # Non-fatal — pikepdf analysis adds supplementary data
        logger.warning("pikepdf analysis failed: %s", exc)
        result.warnings.append(f"pikepdf analysis incomplete: {exc}")

    _estimate_optimization_potential(result)
    return result

# ---------------------------------------------------------------------------
# PyMuPDF analysis
# ---------------------------------------------------------------------------

def _analyze_with_pymupdf(result: AnalysisResult, password: str | None) -> None:
    """Extract content information using PyMuPDF.
    
    Raises
    ------
    InvalidPDFError
        If the file is not a valid PDF or is corrupted.
    """
    try:
        doc: fitz.Document = fitz.open(str(result.path))
    except RuntimeError as exc:
        # PyMuPDF raises RuntimeError for invalid/corrupted PDFs
        exc_str = str(exc).lower()
        if any(keyword in exc_str for keyword in ["not a pdf", "cannot open", "damaged", "corrupted", "invalid"]):
            raise InvalidPDFError(f"Invalid or corrupted PDF: {exc}") from exc
        raise
    except Exception as exc:
        # Other errors during opening
        raise InvalidPDFError(f"Cannot open file as PDF: {exc}") from exc
    
    try:
        # Verify it's actually a PDF by checking basic properties
        if not doc.is_pdf:
            raise InvalidPDFError(f"File is not a PDF document: {result.path}")
        
        # Try to access page_count to verify the document is readable
        try:
            page_count = doc.page_count
            if page_count < 0:
                raise InvalidPDFError(f"Invalid PDF: negative page count")
        except Exception as exc:
            raise InvalidPDFError(f"Cannot read PDF structure: {exc}") from exc
        # Check if document needs password
        if doc.needs_pass:
            if password:
                if not doc.authenticate(password):
                    result.is_encrypted = True
                    result.encryption_method = "unknown"
                    result.warnings.append("PDF is encrypted; wrong password.")
                    # Can't analyze further without correct password
                    return
            else:
                result.is_encrypted = True
                result.encryption_method = "unknown"
                result.warnings.append("PDF is encrypted; some analysis may be incomplete.")
                # Try to get basic info but skip operations that require decryption
                try:
                    result.page_count = doc.page_count
                except Exception:
                    result.page_count = 0
                return
        elif doc.is_encrypted and password:
            if not doc.authenticate(password):
                result.is_encrypted = True
                result.encryption_method = "unknown"
                result.warnings.append("PDF is encrypted; wrong password.")
                return

        result.page_count = doc.page_count
        # Only update is_encrypted if it wasn't already set to True
        if not result.is_encrypted:
            result.is_encrypted = doc.is_encrypted
        result.has_metadata = bool(doc.metadata and any(doc.metadata.values()))

        # TOC / bookmarks
        try:
            toc = doc.get_toc()
            result.has_bookmarks = len(toc) > 0
        except Exception as exc:
            logger.debug(f"Could not get TOC: {exc}")
            result.has_bookmarks = False

        # Images
        images: list[ImageInfo] = []
        total_image_bytes = 0
        try:
            for page_index in range(doc.page_count):
                page = doc.load_page(page_index)
                for img_index, img in enumerate(page.get_images(full=True)):
                    xref = img[0]
                    try:
                        pix = fitz.Pixmap(doc, xref)
                        img_bytes = len(pix.samples)
                        dpi = _estimate_dpi(page, pix.width, pix.height)
                        images.append(
                            ImageInfo(
                                index=xref,
                                width=pix.width,
                                height=pix.height,
                                dpi=dpi,
                                colorspace=pix.colorspace.name if pix.colorspace else "unknown",
                                bpc=8,  # PyMuPDF normalises to 8bpc pixmaps
                                filter=img[9] if len(img) > 9 else "unknown",
                                size_bytes=img_bytes,
                            )
                        )
                        total_image_bytes += img_bytes
                        pix = None  # release
                    except Exception:
                        pass  # skip unreadable images
        except Exception as exc:
            logger.debug(f"Could not analyze images: {exc}")

        result.images = images
        result.has_images = len(images) > 0
        result.total_image_bytes = total_image_bytes

        # Fonts
        fonts: list[FontInfo] = []
        seen_fonts: set[str] = set()
        try:
            for page_index in range(doc.page_count):
                page = doc.load_page(page_index)
                for f in page.get_fonts(full=True):
                    name = f[3]  # basefont name
                    if name in seen_fonts:
                        continue
                    seen_fonts.add(name)
                    fonts.append(
                        FontInfo(
                            name=name,
                            type=f[2],
                            embedded=bool(f[1]),
                            subset="+" in name,
                        )
                    )
        except Exception as exc:
            logger.debug(f"Could not analyze fonts: {exc}")
            
        result.fonts = fonts
        result.has_fonts = len(fonts) > 0

        # Links
        try:
            for page_index in range(doc.page_count):
                page = doc.load_page(page_index)
                links = page.get_links()
                if links:
                    result.has_links = True
                    break
        except Exception as exc:
            logger.debug(f"Could not analyze links: {exc}")

        # Annotations
        try:
            for page_index in range(doc.page_count):
                page = doc.load_page(page_index)
                annots = list(page.annots() or [])
                if annots:
                    result.has_annotations = True
                    break
        except Exception as exc:
            logger.debug(f"Could not analyze annotations: {exc}")

    finally:
        doc.close()

def _estimate_dpi(page: fitz.Page, img_w: int, img_h: int) -> float:
    """Rough DPI estimate based on page dimensions and image pixel size."""
    rect = page.rect
    if rect.width <= 0 or rect.height <= 0:
        return 0.0
    # fitz rect is in points (1/72 inch)
    page_w_inches = rect.width / 72.0
    page_h_inches = rect.height / 72.0
    dpi_w = img_w / page_w_inches if page_w_inches > 0 else 0
    dpi_h = img_h / page_h_inches if page_h_inches > 0 else 0
    return round(max(dpi_w, dpi_h), 1)

# ---------------------------------------------------------------------------
# pikepdf analysis
# ---------------------------------------------------------------------------

def _analyze_with_pikepdf(result: AnalysisResult, password: str | None) -> None:
    """Supplement analysis with pikepdf for structural details."""
    open_kwargs: dict = {}
    if password:
        open_kwargs["password"] = password

    try:
        pdf = pikepdf.open(str(result.path), **open_kwargs)
    except pikepdf.PasswordError:
        result.is_encrypted = True
        result.warnings.append("PDF is encrypted — pikepdf could not open it.")
        return

    try:
        root = pdf.Root

        # PDF version
        if hasattr(pdf, "pdf_version"):
            result.pdf_version = pdf.pdf_version

        # Forms (AcroForm)
        if "/AcroForm" in root:
            acroform = root["/AcroForm"]
            if "/Fields" in acroform and len(acroform["/Fields"]) > 0:
                result.has_forms = True

        # JavaScript
        if "/Names" in root:
            names = root["/Names"]
            if "/JavaScript" in names:
                result.has_javascript = True
        if "/OpenAction" in root:
            oa = root["/OpenAction"]
            if isinstance(oa, pikepdf.Dictionary) and "/S" in oa:
                if str(oa["/S"]) == "/JavaScript":
                    result.has_javascript = True

        # Attachments (EmbeddedFiles)
        if "/Names" in root:
            names = root["/Names"]
            if "/EmbeddedFiles" in names:
                result.has_attachments = True

        # Layers (OCProperties)
        if "/OCProperties" in root:
            result.has_layers = True

        # Accessibility tags (MarkInfo / StructTreeRoot)
        if "/MarkInfo" in root or "/StructTreeRoot" in root:
            result.has_accessibility_tags = True

        # Signatures
        _check_signatures(pdf, result)

        # Linearization
        result.is_linearized = pdf.is_linearized

        # PDF/A (check metadata for pdfaid namespace)
        _check_pdfa(pdf, result)

        # Thumbnails
        for page in pdf.pages:
            if "/Thumb" in page:
                result.has_thumbnails = True
                break

        # Encryption method
        if result.is_encrypted and hasattr(pdf, "encryption"):
            enc = pdf.encryption
            if enc:
                result.encryption_method = str(getattr(enc, "string_method", "unknown"))

    finally:
        pdf.close()

def _check_signatures(pdf: pikepdf.Pdf, result: AnalysisResult) -> None:
    """Check if the PDF contains digital signatures."""
    root = pdf.Root
    if "/AcroForm" not in root:
        return
    acroform = root["/AcroForm"]
    if "/SigFlags" in acroform:
        sig_flags = int(acroform["/SigFlags"])
        if sig_flags & 1:
            result.has_signatures = True
            return
    # Fallback: check fields for /Sig type
    if "/Fields" in acroform:
        for field in acroform["/Fields"]:
            try:
                field_obj = field if isinstance(field, pikepdf.Dictionary) else pdf.get_object(field)
                if "/FT" in field_obj and str(field_obj["/FT"]) == "/Sig":
                    result.has_signatures = True
                    return
            except Exception:
                pass

def _check_pdfa(pdf: pikepdf.Pdf, result: AnalysisResult) -> None:
    """Detect PDF/A conformance via XMP metadata."""
    try:
        with pdf.open_metadata() as meta:
            raw = str(meta)
            if "pdfaid" in raw.lower() or "pdfa" in raw.lower():
                result.is_pdfa = True
                # Try to extract conformance level
                for level in ("1a", "1b", "2a", "2b", "2u", "3a", "3b", "3u"):
                    if level in raw.lower():
                        result.pdfa_level = level.upper()
                        break
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Optimization estimate
# ---------------------------------------------------------------------------

def _estimate_optimization_potential(result: AnalysisResult) -> None:
    """Heuristic estimate of how much the file can be reduced."""
    score = 0.0

    # Large images are the biggest opportunity
    if result.has_images:
        high_dpi_images = [img for img in result.images if img.dpi > 200]
        if high_dpi_images:
            score += 30.0
        else:
            score += 5.0

    # Uncompressed streams
    if not result.is_linearized:
        score += 5.0

    # Fonts with full embedding
    full_fonts = [f for f in result.fonts if f.embedded and not f.subset]
    if full_fonts:
        score += 10.0 * min(len(full_fonts), 3)

    # Thumbnails
    if result.has_thumbnails:
        score += 3.0

    # Attachments
    if result.has_attachments:
        score += 5.0

    # Cap at 80 — we can never guarantee more
    score = min(score, 80.0)

    result.estimated_reduction_pct = round(score, 1)
    result.already_optimized = score < 5.0
