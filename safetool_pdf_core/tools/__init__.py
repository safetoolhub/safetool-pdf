# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""PDF tools — merge, numbering, metadata removal, unlock."""

from __future__ import annotations

from safetool_pdf_core.tools.merge import execute as merge
from safetool_pdf_core.tools.metadata import execute as strip_metadata
from safetool_pdf_core.tools.numbering import execute as number
from safetool_pdf_core.tools.unlock import execute as unlock

__all__ = ["merge", "strip_metadata", "number", "unlock"]
