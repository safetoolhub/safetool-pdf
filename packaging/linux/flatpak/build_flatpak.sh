#!/usr/bin/env bash
# Build Flatpak for SafeTool PDF
# SafeTool PDF Packaging
# Copyright (C) 2026 safetoolhub.org
# License: GPL-3.0-or-later

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
APP_ID="org.safetoolhub.safetoolpdf"
MANIFEST="$SCRIPT_DIR/$APP_ID.yml"
BUILD_DIR="$PROJECT_ROOT/dist/flatpak-build"
REPO_DIR="$PROJECT_ROOT/dist/flatpak-repo"
BUNDLE="$PROJECT_ROOT/dist/SafeToolPDF.flatpak"

echo "=== Building SafeTool PDF Flatpak ==="

# -----------------------------------------------------------------------
# Prerequisites
# -----------------------------------------------------------------------
if [ ! -d "$PROJECT_ROOT/dist/safetool-pdf" ]; then
    echo "Error: PyInstaller dist not found at $PROJECT_ROOT/dist/safetool-pdf"
    echo "Run PyInstaller first:  python dev-tools/build.py --skip-installer"
    exit 1
fi

for cmd in flatpak flatpak-builder; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: $cmd is not installed."
        exit 1
    fi
done

# Install SDK/runtime if not present
echo "Ensuring runtime & SDK are available..."
flatpak install --user --noninteractive flathub org.freedesktop.Platform//23.08 org.freedesktop.Sdk//23.08 || true

# -----------------------------------------------------------------------
# Build
# -----------------------------------------------------------------------
echo "Running flatpak-builder..."
rm -rf "$BUILD_DIR" "$REPO_DIR"

flatpak-builder \
    --force-clean \
    --user \
    --repo="$REPO_DIR" \
    "$BUILD_DIR" \
    "$MANIFEST"

# -----------------------------------------------------------------------
# Bundle into a single .flatpak file
# -----------------------------------------------------------------------
echo "Creating single-file bundle..."
flatpak build-bundle \
    "$REPO_DIR" \
    "$BUNDLE" \
    "$APP_ID"

echo ""
echo "=== Flatpak bundle created ==="
ls -lh "$BUNDLE"
echo ""
echo "Install with:  flatpak install --user $BUNDLE"
