# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Persistent user preferences via QSettings."""

from __future__ import annotations

from PySide6.QtCore import QSettings

from safetool_pdf_core.constants import APP_NAME, AUTHOR

_ORG = AUTHOR  # "safetoolhub.org"
_APP = APP_NAME  # "SafeTool PDF"

def get_settings() -> QSettings:
    """Return the application QSettings instance."""
    return QSettings(_ORG, _APP)

def save_setting(key: str, value: object) -> None:
    s = get_settings()
    s.setValue(key, value)

def load_setting(key: str, default: object = None) -> object:
    s = get_settings()
    return s.value(key, default)

# Convenience keys
LAST_PRESET = "last_preset"
LAST_OUTPUT_DIR = "last_output_dir"
THEME = "theme"  # "light" | "dark" | "system"
DETAILS_EXPANDED = "details_expanded"
OUTPUT_SUFFIX = "output_suffix"  # configurable file suffix
LANGUAGE = "language"  # "es" | "en"
ENABLE_LOGGING = "enable_logging"  # bool: save logs to user folder


def get_language() -> str:
    """Return the persisted language code (default: 'es')."""
    return str(load_setting(LANGUAGE, "es"))


def set_language(lang: str) -> None:
    """Persist the chosen language code."""
    save_setting(LANGUAGE, lang)
