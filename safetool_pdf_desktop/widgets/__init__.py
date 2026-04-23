# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""safetool_pdf_desktop.widgets package — backward-compat redirects.

All classes have been moved to ``screens/`` and ``dialogs/`` packages.
These re-exports keep existing imports working.
"""

from __future__ import annotations

from safetool_pdf_desktop.dialogs.about_dialog import AboutDialog
from safetool_pdf_desktop.dialogs.details_dialog import DetailsDialog
from safetool_pdf_desktop.dialogs.settings_dialog import SettingsDialog
from safetool_pdf_desktop.screens.file_selection_screen import FileSelectionScreen
from safetool_pdf_desktop.screens.strategy_screen import StrategyScreen

__all__ = [
    "AboutDialog",
    "DetailsDialog",
    "FileSelectionScreen",
    "SettingsDialog",
    "StrategyScreen",
]
