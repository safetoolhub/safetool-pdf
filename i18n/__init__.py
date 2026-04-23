# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Internationalization (i18n) package for SafeTool PDF."""

from __future__ import annotations

from i18n.core import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    get_current_language,
    init_i18n,
    set_language,
    tr,
)

__all__ = [
    "init_i18n",
    "tr",
    "get_current_language",
    "set_language",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
]
