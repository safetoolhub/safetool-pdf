# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Application-wide constants.

Identity fields are imported from the top-level ``config`` module so that
there is a single source of truth.  This module re-exports them for
backward compatibility and adds technical constants used by the engine.
"""

from __future__ import annotations

from config import (
    APP_AUTHOR,
    APP_CONTACT,
    APP_DESCRIPTION,
    APP_LICENSE,
    APP_NAME,
    APP_REPO,
    APP_VERSION,
    APP_VERSION_SUFFIX,
    APP_WEBSITE,
)

# Re-export under the old names so existing imports keep working.
VERSION: str = APP_VERSION
AUTHOR: str = APP_AUTHOR
WEBSITE: str = APP_WEBSITE
EMAIL: str = APP_CONTACT
LICENSE_SPDX: str = "GPL-3.0-or-later"

# ── Technical constants ──────────────────────────────────────────────
OUTPUT_SUFFIX: str = "_safetoolpdf"
GS_MIN_VERSION: tuple[int, int] = (9, 50)
GS_TIMEOUT_SECONDS: int = 300

LICENSE_TEXT: str = (
    f"{APP_NAME} {APP_VERSION}\n"
    f"Copyright (C) 2026 {APP_AUTHOR}\n"
    "\n"
    "This program is free software: you can redistribute it and/or modify\n"
    "it under the terms of the GNU General Public License as published by\n"
    "the Free Software Foundation, either version 3 of the License, or\n"
    "(at your option) any later version.\n"
    "\n"
    "This program is distributed in the hope that it will be useful,\n"
    "but WITHOUT ANY WARRANTY; without even the implied warranty of\n"
    "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n"
    "GNU General Public License for more details.\n"
    "\n"
    "You should have received a copy of the GNU General Public License\n"
    "along with this program.  If not, see <https://www.gnu.org/licenses/>."
)
