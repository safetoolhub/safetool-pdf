# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

#!/usr/bin/env python3
# SafeTool PDF Packaging
# Copyright (C) 2026 safetoolhub.org
# License: GPL-3.0-or-later

"""Download the official Ghostscript binary for Windows.

On Linux and macOS, Ghostscript should be installed by the user via
their system package manager (apt, brew, etc.).  The application works
without it but some presets are unavailable.

The binary is placed under  packaging/vendor/gs/bin/  so that
PyInstaller / Nuitka can bundle it alongside the Windows application.
"""

from __future__ import annotations

import hashlib
import platform
import shutil
import struct
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GS_VERSION = "10.06.0"
GS_VERSION_SHORT = GS_VERSION.replace(".", "")  # e.g. "10060"

# GitHub-hosted release artefact — Windows 64-bit installer only
_BASE = f"https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs{GS_VERSION_SHORT}"
_WINDOWS_URL = f"{_BASE}/gs{GS_VERSION_SHORT}w64.exe"

_SCRIPT_DIR = Path(__file__).resolve().parent
_VENDOR_DIR = _SCRIPT_DIR.parent / "vendor" / "gs"
_BIN_DIR = _VENDOR_DIR / "bin"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _download(url: str, dest: Path) -> Path:
    """Download *url* into *dest* directory and return the local path."""
    filename = url.rsplit("/", 1)[-1]
    local = dest / filename
    print(f"  Downloading {url} ...")
    urllib.request.urlretrieve(url, local)
    print(f"  Saved to {local}  ({local.stat().st_size:,} bytes)")
    return local

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

# ---------------------------------------------------------------------------
# Windows extraction
# ---------------------------------------------------------------------------

def _install_windows(exe: Path) -> None:
    """The Windows artefact is a self-extracting installer.

    We attempt to silently extract using 7z or fall back to placing the
    whole exe so the user can run it manually.
    """
    _BIN_DIR.mkdir(parents=True, exist_ok=True)
    sevenzip = shutil.which("7z")
    if sevenzip:
        tmpdir = Path(tempfile.mkdtemp(prefix="gs_win_"))
        try:
            subprocess.check_call(
                [sevenzip, "x", str(exe), f"-o{tmpdir}", "-y"],
                stdout=subprocess.DEVNULL,
            )
            candidates = list(tmpdir.rglob("gswin64c.exe"))
            if not candidates:
                candidates = list(tmpdir.rglob("gs*.exe"))
            if not candidates:
                sys.exit("Could not locate gswin64c.exe after extraction.")
            for c in candidates:
                shutil.copy2(c, _BIN_DIR / c.name)
            print(f"  Installed gs -> {_BIN_DIR}")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    else:
        # Fallback: copy the installer; user must extract manually
        dest = _BIN_DIR / exe.name
        shutil.copy2(exe, dest)
        print(f"  7z not found - copied installer to {dest}")
        print("  Please extract gswin64c.exe manually into packaging/vendor/gs/bin/")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    system = platform.system().lower()
    bits = struct.calcsize("P") * 8

    if system != "windows" or bits != 64:
        print(f"Platform: {system} {bits}-bit")
        print("Ghostscript download is only supported for Windows x64.")
        print("On Linux/macOS, install Ghostscript via your package manager:")
        print("  Linux : sudo apt install ghostscript")
        print("  macOS : brew install ghostscript")
        sys.exit(0)

    url = _WINDOWS_URL
    print(f"Platform : windows_x64")
    print(f"GS ver   : {GS_VERSION}")
    print(f"URL      : {url}")
    print()

    with tempfile.TemporaryDirectory(prefix="gs_dl_") as tmpdir:
        archive = _download(url, Path(tmpdir))
        digest = _sha256(archive)
        print(f"  SHA-256 : {digest}")
        print()
        _install_windows(archive)

    # Quick verification
    gs = _BIN_DIR / "gswin64c.exe"
    if gs.exists():
        print(f"[OK] Ghostscript binary available at {gs}")
    else:
        print("[WARNING] Binary not found - check the output above for errors.")
        sys.exit(1)

if __name__ == "__main__":
    main()
