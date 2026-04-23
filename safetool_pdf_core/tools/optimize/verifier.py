# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Post-optimization verification."""

from __future__ import annotations

import logging
from pathlib import Path

import fitz  # PyMuPDF

from safetool_pdf_core.exceptions import VerificationError

logger = logging.getLogger(__name__)

def verify(
    output_path: Path,
    expected_page_count: int,
    original_size: int,
) -> list[str]:
    """Verify the optimized PDF.

    Checks:
    1. File exists and is non-empty.
    2. Can be opened by PyMuPDF.
    3. Page count matches the original.
    4. File size ≤ original (warn if larger).

    Returns a list of warnings.  Raises ``VerificationError`` on hard failure.
    """
    warnings: list[str] = []

    # 1. Existence
    if not output_path.is_file():
        raise VerificationError(f"Output file does not exist: {output_path}")

    optimized_size = output_path.stat().st_size
    if optimized_size == 0:
        raise VerificationError("Output file is empty.")

    # 2. Open and read page count
    try:
        doc = fitz.open(str(output_path))
    except Exception as exc:
        raise VerificationError(f"Cannot open optimized PDF: {exc}") from exc

    try:
        actual_pages = doc.page_count
    finally:
        doc.close()

    # 3. Page count
    if actual_pages != expected_page_count:
        raise VerificationError(
            f"Page count mismatch: expected {expected_page_count}, got {actual_pages}"
        )

    # 4. Size comparison
    if optimized_size > original_size:
        pct = ((optimized_size - original_size) / original_size) * 100
        warnings.append(
            f"Optimized file is {pct:.1f}% larger than the original "
            f"({optimized_size:,} > {original_size:,} bytes)."
        )

    return warnings
