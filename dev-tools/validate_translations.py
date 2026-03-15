#!/usr/bin/env python3
# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Validate translation files — check for missing keys, extras, and placeholders.

Usage::

    python dev-tools/validate_translations.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

I18N_DIR = Path(__file__).resolve().parent.parent / "i18n" / "translations"
BASE_LANG = "es"

# ── Helpers ──────────────────────────────────────────────────────────


def flatten(d: dict, prefix: str = "") -> dict[str, str]:
    """Flatten nested dict to dotted-key → value."""
    result: dict[str, str] = {}
    for k, v in d.items():
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            result.update(flatten(v, full))
        else:
            result[full] = str(v)
    return result


def extract_placeholders(s: str) -> set[str]:
    """Extract {placeholder} names from a string."""
    return set(re.findall(r"\{(\w+)\}", s))


# ── Main ─────────────────────────────────────────────────────────────


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    # Load base
    base_path = I18N_DIR / f"{BASE_LANG}.json"
    if not base_path.exists():
        print(f"ERROR: Base translation file not found: {base_path}")
        return 1

    with open(base_path, encoding="utf-8") as f:
        base_data = json.load(f)
    base_flat = flatten(base_data)

    print(f"Base language ({BASE_LANG}): {len(base_flat)} keys\n")

    # Check base for empty values
    for key, val in base_flat.items():
        if not val.strip():
            warnings.append(f"  [{BASE_LANG}] Empty value: {key}")

    # Validate each other language file
    for path in sorted(I18N_DIR.glob("*.json")):
        lang = path.stem
        if lang == BASE_LANG:
            continue

        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        flat = flatten(data)

        print(f"Language '{lang}': {len(flat)} keys")

        # Missing keys
        missing = set(base_flat.keys()) - set(flat.keys())
        if missing:
            for k in sorted(missing):
                errors.append(f"  [{lang}] MISSING key: {k}")

        # Extra keys
        extra = set(flat.keys()) - set(base_flat.keys())
        if extra:
            for k in sorted(extra):
                warnings.append(f"  [{lang}] EXTRA key (not in base): {k}")

        # Placeholder mismatches
        for key in sorted(set(base_flat.keys()) & set(flat.keys())):
            base_ph = extract_placeholders(base_flat[key])
            lang_ph = extract_placeholders(flat[key])
            if base_ph != lang_ph:
                errors.append(
                    f"  [{lang}] Placeholder mismatch in '{key}': "
                    f"base={base_ph}, {lang}={lang_ph}"
                )

        # Empty values
        for key, val in flat.items():
            if not val.strip():
                warnings.append(f"  [{lang}] Empty value: {key}")

    # Report
    print()
    if warnings:
        print(f"⚠ {len(warnings)} warning(s):")
        for w in warnings:
            print(w)
        print()

    if errors:
        print(f"✗ {len(errors)} error(s):")
        for e in errors:
            print(e)
        print()
        return 1

    print("✓ All translation files are valid!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
