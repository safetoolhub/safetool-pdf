# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Typed exceptions for safetool_pdf_core."""

from __future__ import annotations

class SafeToolPDFError(Exception):
    """Base exception for all SafeTool PDF errors."""

class AnalysisError(SafeToolPDFError):
    """Raised when PDF analysis fails."""

class OptimizationError(SafeToolPDFError):
    """Raised when the optimization pipeline fails."""

class EncryptedPDFError(SafeToolPDFError):
    """Raised when a PDF is encrypted and no password was provided."""

class InvalidPDFError(SafeToolPDFError):
    """Raised when the input file is not a valid PDF."""

class VerificationError(SafeToolPDFError):
    """Raised when post-optimization verification fails."""

class GhostscriptNotFoundError(SafeToolPDFError):
    """Raised when Ghostscript binary cannot be located."""

class GhostscriptError(SafeToolPDFError):
    """Raised when the Ghostscript subprocess fails."""

class CancellationError(SafeToolPDFError):
    """Raised when the user cancels the operation."""

class SignedPDFError(SafeToolPDFError):
    """Raised when destructive operations are attempted on a signed PDF."""
