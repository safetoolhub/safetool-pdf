# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Ghostscript binary detection — bundled first, then system PATH."""

from __future__ import annotations

import logging
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from safetool_pdf_core.constants import GS_MIN_VERSION

logger = logging.getLogger(__name__)

# Platform-specific binary name
_GS_BIN_NAME: str = "gswin64c.exe" if platform.system() == "Windows" else "gs"

def find_gs() -> Path | None:
    """Return the path to a usable Ghostscript binary, or ``None``.

    Search order:
    1. ``<app_dir>/vendor/gs/bin/<gs_binary>``
    2. System ``PATH``
    """
    # 1. Bundled path
    bundled = _bundled_gs_path()
    if bundled and bundled.is_file():
        if _verify_version(bundled):
            logger.info("Using bundled Ghostscript: %s", bundled)
            return bundled
        logger.warning("Bundled GS found but version too old: %s", bundled)

    # 2. System PATH
    system = shutil.which(_GS_BIN_NAME)
    if system:
        system_path = Path(system)
        if _verify_version(system_path):
            logger.info("Using system Ghostscript: %s", system_path)
            return system_path
        logger.warning("System GS found but version too old: %s", system_path)

    logger.info("Ghostscript not found.")
    return None

def gs_available() -> bool:
    """Return ``True`` if a usable Ghostscript binary exists."""
    return find_gs() is not None

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _bundled_gs_path() -> Path | None:
    """Return the expected bundled GS path, or None if structure is wrong."""
    # <app_dir> is the directory containing the running script / frozen exe
    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).parent
    else:
        # In development: look relative to this file's package root
        app_dir = Path(__file__).resolve().parent.parent

    # Search order: frozen layout first, then dev layout
    candidates = [
        app_dir / "vendor" / "gs" / "bin" / _GS_BIN_NAME,           # frozen (PyInstaller)
        app_dir / "packaging" / "vendor" / "gs" / "bin" / _GS_BIN_NAME,  # dev
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None

def _verify_version(gs_path: Path) -> bool:
    """Verify that *gs_path* meets the minimum version requirement."""
    try:
        result = subprocess.run(
            [str(gs_path), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version_str = result.stdout.strip()
        match = re.match(r"(\d+)\.(\d+)", version_str)
        if not match:
            return False
        major, minor = int(match.group(1)), int(match.group(2))
        ok = (major, minor) >= GS_MIN_VERSION
        if ok:
            logger.debug("GS version %s meets minimum %s", version_str, GS_MIN_VERSION)
        return ok
    except Exception as exc:
        logger.debug("GS version check failed: %s", exc)
        return False
