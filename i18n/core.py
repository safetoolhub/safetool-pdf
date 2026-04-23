# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Internationalization (i18n) module — JSON-based translation system.

Architecture:
    - JSON files in ``i18n/`` directory (``es.json``, ``en.json``).
    - Nested key structure accessed via dotted paths: ``tr("screen.label")``.
    - Placeholder interpolation: ``tr("msg.saved", size="1.2 MB")``.
    - Fallback chain: current language → Spanish (base) → key itself.

Usage::

    from i18n import init_i18n, tr

    init_i18n("es")  # call once at startup
    label = tr("header.settings")
    msg = tr("results.saved", size="1.2 MB", pct="42.3")
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

# ── Public constants ─────────────────────────────────────────────────

SUPPORTED_LANGUAGES: dict[str, str] = {
    "es": "Español",
    "en": "English",
}

DEFAULT_LANGUAGE: str = "es"

# ── Module state ─────────────────────────────────────────────────────

_current_lang: str = DEFAULT_LANGUAGE
_translations: dict[str, dict[str, Any]] = {}   # lang → nested dict
_flat_cache: dict[str, dict[str, str]] = {}      # lang → flat dotted-key dict

_I18N_DIR: Path = Path(__file__).resolve().parent / "translations"


# ── Initialisation ───────────────────────────────────────────────────

def init_i18n(lang: str | None = None) -> None:
    """Initialise the translation system.

    Must be called **once** before any UI is created.

    Parameters
    ----------
    lang:
        Language code (``"es"`` or ``"en"``).  Falls back to
        :data:`DEFAULT_LANGUAGE` if *None* or unsupported.
    """
    global _current_lang

    if lang not in SUPPORTED_LANGUAGES:
        _logger.warning("Unsupported language '%s', falling back to '%s'", lang, DEFAULT_LANGUAGE)
        lang = DEFAULT_LANGUAGE

    _current_lang = lang

    # Always load base language (Spanish) for fallback
    _load_language(DEFAULT_LANGUAGE)

    # Load requested language if different from base
    if lang != DEFAULT_LANGUAGE:
        _load_language(lang)

    _logger.info("i18n initialised — language: %s", lang)


def get_current_language() -> str:
    """Return the current language code."""
    return _current_lang


def set_language(lang: str) -> None:
    """Change the current language (requires app restart for full effect)."""
    global _current_lang
    if lang in SUPPORTED_LANGUAGES:
        _current_lang = lang
        if lang not in _translations:
            _load_language(lang)


# ── Translation function ────────────────────────────────────────────

def tr(key: str, **kwargs: Any) -> str:
    """Translate a dotted key to the current language.

    Parameters
    ----------
    key:
        Dotted path into the JSON structure, e.g. ``"header.settings"``.
    **kwargs:
        Placeholder values, e.g. ``tr("msg", count=5)``.

    Returns
    -------
    str
        Translated string with placeholders resolved.

    Fallback chain:
        1. Current language
        2. Spanish base (``es.json``)
        3. The key itself
    """
    # Try current language
    value = _lookup(key, _current_lang)

    # Fallback to base language
    if value is None and _current_lang != DEFAULT_LANGUAGE:
        value = _lookup(key, DEFAULT_LANGUAGE)

    # Final fallback: the key itself
    if value is None:
        _logger.warning("Translation key not found: '%s'", key)
        return key

    # Interpolate placeholders
    if kwargs:
        try:
            value = value.format(**kwargs)
        except (KeyError, IndexError, ValueError) as exc:
            _logger.warning("Placeholder error in '%s': %s", key, exc)

    return value


# ── Internal helpers ─────────────────────────────────────────────────

def _load_language(lang: str) -> None:
    """Load a JSON translation file and build its flat cache."""
    path = _I18N_DIR / f"{lang}.json"
    if not path.exists():
        _logger.error("Translation file not found: %s", path)
        return

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        _logger.error("Failed to load translation file %s: %s", path, exc)
        return

    _translations[lang] = data
    _flat_cache[lang] = _flatten(data)
    _logger.debug("Loaded %d keys for language '%s'", len(_flat_cache[lang]), lang)


def _flatten(d: dict[str, Any], prefix: str = "") -> dict[str, str]:
    """Flatten a nested dict into dotted-key → string pairs."""
    result: dict[str, str] = {}
    for k, v in d.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            result.update(_flatten(v, full_key))
        else:
            result[full_key] = str(v)
    return result


def _lookup(key: str, lang: str) -> str | None:
    """Lookup a key in the flat cache for a specific language."""
    flat = _flat_cache.get(lang)
    if flat is None:
        return None
    return flat.get(key)
