# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Centralised application metadata.

Every module that needs the application name, version, author, etc.
should import from this file.  The values here are the single source
of truth; ``safetool_pdf_core.constants`` re-exports the subset it needs.
"""

from __future__ import annotations

# ── Identity ─────────────────────────────────────────────────────────
APP_NAME: str = "SafeTool PDF"
APP_VERSION: str = "0.2.0"
APP_VERSION_SUFFIX: str = "beta"

# ── Author / Organisation ────────────────────────────────────────────
APP_AUTHOR: str = "SafeToolHub"
APP_CONTACT: str = "safetoolhub@protonmail.com"
APP_WEBSITE: str = "https://safetoolhub.org"
APP_REPO: str = "https://github.com/safetoolhub/safetool-pdf"

# ── Description ──────────────────────────────────────────────────────
APP_DESCRIPTION: str = "Privacy-first pdf optimizer."

# ── Computed version ──────────────────────────────────────────────────
def get_full_version() -> str:
    """Return e.g. ``'0.1.0-beta'`` or ``'0.1.0'``."""
    if APP_VERSION_SUFFIX:
        return f"{APP_VERSION}-{APP_VERSION_SUFFIX}"
    return APP_VERSION


# ── Legal ────────────────────────────────────────────────────────────
APP_LICENSE: str = "GPLv3"
APP_ATTRIBUTION_REQUIREMENT: str = (
    "Mandatory attribution to SafeToolHub and safetoolhub.org"
)

# ── Tool Availability ────────────────────────────────────────────────
# Control which tools are enabled in the UI
TOOL_OPTIMIZE_ENABLED: bool = True
TOOL_COMBINE_ENABLED: bool = True
TOOL_NUMBERING_ENABLED: bool = True
TOOL_METADATA_ENABLED: bool = True
TOOL_UNLOCK_ENABLED: bool = True
