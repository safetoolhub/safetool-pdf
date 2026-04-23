#!/usr/bin/env bash
# Build SafeTool PDF with Nuitka
# SafeTool PDF Packaging
# Copyright (C) 2026 safetoolhub.org
# License: GPL-3.0-or-later

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENDOR_GS="$PROJECT_ROOT/packaging/vendor/gs"

echo "=== Building SafeTool PDF with Nuitka ==="
echo "Project root: $PROJECT_ROOT"

# Ensure Nuitka is installed
if ! command -v python3 -m nuitka &>/dev/null && ! python3 -c "import nuitka" 2>/dev/null; then
    echo "Error: Nuitka is not installed. Install with: pip install nuitka"
    exit 1
fi

# Base Nuitka flags
NUITKA_FLAGS=(
    --standalone
    --onefile
    --enable-plugin=pyside6
    --include-package=safetool_pdf_core
    --include-package=safetool_pdf_cli
    --include-package=safetool_pdf_desktop
    --output-dir="$PROJECT_ROOT/dist/nuitka"
    --output-filename=safetool-pdf-desktop
    --remove-output
    --assume-yes-for-downloads
    --python-flag=no_site
    --nofollow-import-to=tkinter
    --nofollow-import-to=unittest
    --nofollow-import-to=tests
)

# Bundle vendored Ghostscript if present
if [ -d "$VENDOR_GS/bin" ]; then
    echo "Including vendored Ghostscript from $VENDOR_GS"
    NUITKA_FLAGS+=(--include-data-dir="$VENDOR_GS=gs")
fi

echo "Running Nuitka..."
cd "$PROJECT_ROOT"

python3 -m nuitka "${NUITKA_FLAGS[@]}" safetool_pdf_desktop/app.py

echo ""
echo "=== Build complete ==="
echo "Output: $PROJECT_ROOT/dist/nuitka/"
ls -lh "$PROJECT_ROOT/dist/nuitka/safetool-pdf-desktop" 2>/dev/null || echo "(check dist/nuitka/ for output)"
