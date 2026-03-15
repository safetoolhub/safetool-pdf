#!/usr/bin/env bash
# Build AppImage from PyInstaller output
# SafeTool PDF Packaging
# Copyright (C) 2026 safetoolhub.org
# License: GPL-3.0-or-later

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PYINSTALLER_DIST="$PROJECT_ROOT/dist/safetool-pdf"
APPDIR="$PROJECT_ROOT/dist/AppDir"
DESKTOP_ID="org.safetoolhub.safetoolpdf"
APP_NAME="safetool-pdf"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
APPIMAGETOOL="$PROJECT_ROOT/dist/appimagetool-x86_64.AppImage"

echo "=== Building SafeTool PDF AppImage ==="

# -----------------------------------------------------------------------
# Step 1: Verify PyInstaller output exists
# -----------------------------------------------------------------------
if [ ! -d "$PYINSTALLER_DIST" ]; then
    echo "Error: PyInstaller dist not found at $PYINSTALLER_DIST"
    echo "Run PyInstaller first:  python dev-tools/build.py --skip-installer"
    exit 1
fi

# -----------------------------------------------------------------------
# Step 2: Create AppDir structure
# -----------------------------------------------------------------------
echo "Creating AppDir layout..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/opt/$APP_NAME"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/512x512/apps"
mkdir -p "$APPDIR/usr/share/metainfo"

# Copy PyInstaller output
cp -a "$PYINSTALLER_DIST"/. "$APPDIR/opt/$APP_NAME/"

# Install desktop file
cp "$SCRIPT_DIR/safetool-pdf.desktop" "$APPDIR/$DESKTOP_ID.desktop"
cp "$SCRIPT_DIR/safetool-pdf.desktop" "$APPDIR/usr/share/applications/$DESKTOP_ID.desktop"

# Icon - copy with both names for compatibility
ICON_SRC="$PROJECT_ROOT/assets/icon.png"
if [ -f "$ICON_SRC" ]; then
    # Copy with desktop ID for system integration
    cp "$ICON_SRC" "$APPDIR/$DESKTOP_ID.png"
    cp "$ICON_SRC" "$APPDIR/usr/share/icons/hicolor/512x512/apps/$DESKTOP_ID.png"
    # Copy with app name for desktop file reference
    cp "$ICON_SRC" "$APPDIR/$APP_NAME.png"
else
    echo "Warning: No icon found at $ICON_SRC"
fi

# AppStream metainfo
METAINFO_SRC="$PROJECT_ROOT/packaging/linux/flatpak/$DESKTOP_ID.metainfo.xml"
if [ -f "$METAINFO_SRC" ]; then
    cp "$METAINFO_SRC" "$APPDIR/usr/share/metainfo/$DESKTOP_ID.metainfo.xml"
    cp "$METAINFO_SRC" "$APPDIR/usr/share/metainfo/$DESKTOP_ID.appdata.xml"
fi

# Install AppRun
cp "$SCRIPT_DIR/AppRun" "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"

# -----------------------------------------------------------------------
# Step 3: Download appimagetool if needed
# -----------------------------------------------------------------------
if [ ! -x "$APPIMAGETOOL" ]; then
    echo "Downloading appimagetool..."
    curl -fSL "$APPIMAGETOOL_URL" -o "$APPIMAGETOOL"
    chmod +x "$APPIMAGETOOL"
fi

# -----------------------------------------------------------------------
# Step 4: Build the AppImage
# -----------------------------------------------------------------------
echo "Running appimagetool..."
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$PROJECT_ROOT/dist/SafeToolPDF-x86_64.AppImage"

echo ""
echo "=== AppImage created ==="
ls -lh "$PROJECT_ROOT/dist/SafeToolPDF-x86_64.AppImage"
