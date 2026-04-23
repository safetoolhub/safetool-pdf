# -*- mode: python ; coding: utf-8 -*-
# SafeTool PDF Packaging
# Copyright (C) 2026 safetoolhub.org
# License: GPL-3.0-or-later
#
# PyInstaller spec file for SafeTool PDF desktop application.
# Supports Linux, Windows and macOS from a single spec file.

import os
import sys
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(SPECPATH).parent.parent          # repo root (two levels up)
VERSION = os.environ.get("APP_VERSION", "0.1.0")
VENDOR_GS = ROOT / "packaging" / "vendor" / "gs"

# ── Data files ───────────────────────────────────────────────────────────────
datas = [
    (str(ROOT / "i18n"),    "i18n"),
    (str(ROOT / "assets"),  "assets"),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "config.py"), "."),
]

# ── Binaries — vendored Ghostscript ─────────────────────────────────────────
binaries = []
if VENDOR_GS.exists() and any(VENDOR_GS.rglob("*")):
    for f in VENDOR_GS.rglob("*"):
        if f.is_file():
            rel = f.relative_to(VENDOR_GS)
            binaries.append((str(f), str(Path("vendor") / "gs" / rel.parent)))

# ── Hidden imports ───────────────────────────────────────────────────────────
hidden_imports = [
    # PySide6
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    # PDF engines
    "pikepdf",
    "fitz",
    # Image processing
    "PIL",
    "PIL.Image",
    "PIL.JpegImagePlugin",
    "PIL.PngImagePlugin",
    # Icons
    "qtawesome",
    # Top-level modules
    "config",
    "i18n",
    "i18n.core",
    # Core package
    "safetool_pdf_core",
    "safetool_pdf_core.analyzer",
    "safetool_pdf_core.constants",
    "safetool_pdf_core.exceptions",
    "safetool_pdf_core.gs_detect",
    "safetool_pdf_core.models",
    "safetool_pdf_core.naming",
    "safetool_pdf_core.optimizer",
    "safetool_pdf_core.presets",
    "safetool_pdf_core.progress",
    "safetool_pdf_core.verifier",
    "safetool_pdf_core.stages",
    "safetool_pdf_core.stages.cleanup",
    "safetool_pdf_core.stages.lossless",
    "safetool_pdf_core.stages.lossy_ghostscript",
    "safetool_pdf_core.stages.lossy_images",
    # CLI
    "safetool_pdf_cli",
    "safetool_pdf_cli.main",
    # Desktop
    "safetool_pdf_desktop",
    "safetool_pdf_desktop.app",
    "safetool_pdf_desktop.main_window",
    "safetool_pdf_desktop.settings",
    # Standard library extras
    "json",
    "logging.handlers",
]

# ── Excludes ─────────────────────────────────────────────────────────────────
excludes = [
    "tkinter",
    "test",
    "tests",
]

# ── Analysis ─────────────────────────────────────────────────────────────────
a = Analysis(
    [str(ROOT / "safetool_pdf_desktop" / "app.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# ── Platform-specific output ─────────────────────────────────────────────────
if sys.platform == "darwin":
    # ── macOS: .app bundle ───────────────────────────────────────────────────
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="SafeToolPDF",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(ROOT / "assets" / "icon.icns") if (ROOT / "assets" / "icon.icns").exists() else None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="SafeToolPDF",
    )
    app = BUNDLE(
        coll,
        name="SafeToolPDF.app",
        icon=str(ROOT / "assets" / "icon.icns") if (ROOT / "assets" / "icon.icns").exists() else None,
        bundle_identifier="org.safetoolhub.safetoolpdf",
        version=VERSION,
        info_plist={
            "NSHighResolutionCapable": True,
            "NSPrincipalClass": "NSApplication",
            "CFBundleShortVersionString": VERSION,
        },
    )

elif sys.platform == "win32":
    # ── Windows: directory build (Inno Setup wraps it) ───────────────────────
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="safetool-pdf-desktop",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(ROOT / "assets" / "icon.ico"),
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="safetool-pdf",
    )

else:
    # ── Linux: directory build (dpkg/rpm/AppImage wrap it) ───────────────────
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="safetool-pdf-desktop",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(ROOT / "assets" / "icon.png"),
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="safetool-pdf",
    )
