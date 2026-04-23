#!/usr/bin/env bash
# Build macOS .app bundle and optional DMG for SafeTool PDF
# SafeTool PDF Packaging
# Copyright (C) 2026 safetoolhub.org
# License: GPL-3.0-or-later

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYINSTALLER_DIST="$PROJECT_ROOT/dist/safetool-pdf"
APP_BUNDLE="$PROJECT_ROOT/dist/SafeToolPDF.app"
DMG_OUTPUT="$PROJECT_ROOT/dist/SafeToolPDF.dmg"

echo "=== Building SafeTool PDF macOS bundle ==="

# -----------------------------------------------------------------------
# Step 1: Verify PyInstaller output
# -----------------------------------------------------------------------
if [ ! -d "$PYINSTALLER_DIST" ]; then
    echo "Error: PyInstaller dist not found at $PYINSTALLER_DIST"
    echo "Run PyInstaller first:  pyinstaller packaging/pyinstaller/safetool-pdf.spec"
    exit 1
fi

# -----------------------------------------------------------------------
# Step 2: Create .app bundle
# -----------------------------------------------------------------------
echo "Assembling .app bundle..."
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# Copy Info.plist
cp "$SCRIPT_DIR/Info.plist" "$APP_BUNDLE/Contents/"

# Copy PyInstaller output into MacOS/
cp -a "$PYINSTALLER_DIST"/. "$APP_BUNDLE/Contents/MacOS/"

# Copy icon if available
ICON_SRC="$PROJECT_ROOT/assets/icon.icns"
if [ ! -f "$ICON_SRC" ]; then
    ICON_SRC="$PROJECT_ROOT/assets/SafeToolPDF.icns"
fi
if [ -f "$ICON_SRC" ]; then
    cp "$ICON_SRC" "$APP_BUNDLE/Contents/Resources/SafeToolPDF.icns"
else
    echo "Warning: Icon not found — .app will use default icon."
fi

# -----------------------------------------------------------------------
# Step 3: Ad-hoc code sign
# -----------------------------------------------------------------------
echo "Ad-hoc signing..."
codesign --force --deep --sign - "$APP_BUNDLE" || {
    echo "Warning: codesign failed (non-fatal on CI / unsigned builds)."
}

# -----------------------------------------------------------------------
# Step 4: Create DMG
# -----------------------------------------------------------------------
echo "Creating DMG..."
if command -v create-dmg &>/dev/null; then
    create-dmg \
        --volname "SafeTool PDF" \
        --volicon "$APP_BUNDLE/Contents/Resources/SafeToolPDF.icns" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "SafeToolPDF.app" 150 190 \
        --app-drop-link 450 190 \
        "$DMG_OUTPUT" \
        "$APP_BUNDLE" || echo "create-dmg failed — falling back to hdiutil"
fi

if [ ! -f "$DMG_OUTPUT" ]; then
    # Fallback: plain hdiutil
    hdiutil create \
        -volname "SafeTool PDF" \
        -srcfolder "$APP_BUNDLE" \
        -ov -format UDZO \
        "$DMG_OUTPUT"
fi

echo ""
echo "=== macOS build complete ==="
ls -lh "$DMG_OUTPUT"
