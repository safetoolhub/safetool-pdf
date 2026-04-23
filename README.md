# SafeTool PDF

> **Privacy-first PDF toolkit — optimize, merge, edit metadata, unlock, and more.**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

SafeTool PDF is a desktop application that provides essential PDF tools with a focus on privacy and ease of use. Built with industry-proven engines: **QPDF** (via pikepdf), **MuPDF** (via PyMuPDF), and **Ghostscript**.

## Features

SafeTool PDF includes 5 powerful tools:

### 🗜️ Optimize
Compress PDF files with lossless and lossy techniques:
- **4 optimization presets**: Lossless, Balanced, Maximum, Custom
- **Lossless optimizations**: stream recompression, object streams, deduplication (pikepdf/QPDF)
- **Lossy optimizations**: image downsampling, JPEG recompression (PyMuPDF)
- **Advanced**: font subsetting, full PDF rewrite (Ghostscript)
- **Preservation modes**: keep or simplify interactive features (forms, links, bookmarks, layers)
- **Before/after preview**: visual comparison of page 1

### 🔗 Combine
Merge multiple PDF files into a single document:
- Drag-and-drop interface for file ordering
- Reorder files before merging
- Preserves document structure and quality

### 📝 Metadata
View and edit PDF metadata:
- Edit title, author, subject, keywords
- View creation and modification dates
- Clean metadata for privacy

### 🔓 Unlock
Remove password protection from PDFs:
- Unlock password-protected files (when you have the password)
- Remove restrictions for editing and printing
- Batch unlock multiple files

### 🔢 Numbering
Add page numbers to PDF documents:
- Customizable position and format
- Multiple numbering styles
- Batch processing support

## Quick Start

### Requirements

- Python 3.11 or later
- Ghostscript (optional, for font subsetting and maximum compression in Optimize tool)

### Install

```bash
# Clone
git clone https://github.com/safetoolhub/safetool-pdf.git
cd safetool-pdf

# Install in development mode
pip install -e ".[dev]"
```

### Run the desktop app

```bash
safetool-pdf-desktop
# or
python -m safetool_pdf_desktop.app
```

### Run the CLI

```bash
# Optimize (lossless by default)
safetool-pdf optimize document.pdf

# Optimize with balanced preset
safetool-pdf optimize -p balanced document.pdf

# Optimize with maximum compression
safetool-pdf optimize -p maximum -o ./optimized/ *.pdf

# Merge PDFs
safetool-pdf merge file1.pdf file2.pdf file3.pdf -o combined.pdf

# Edit metadata
safetool-pdf metadata document.pdf --title "My Document" --author "John Doe"

# Unlock PDF
safetool-pdf unlock protected.pdf --password "secret"

# Dry-run analysis
safetool-pdf optimize --dry-run document.pdf

# Verbose output
safetool-pdf optimize -v document.pdf
```

## Optimization Presets

| Preset | Images | Fonts | Description |
|--------|--------|-------|-------------|
| **Lossless** | Untouched | Untouched | Stream recompression, deduplication, object streams |
| **Balanced** | 150 DPI, Q80 | Subset | Good balance of size and quality |
| **Maximum** | 96 DPI, Q50 | Subset + rewrite | Aggressive — best for web/email |
| **Custom** | Configurable | Configurable | Full control over every option |

## Architecture

```
safetool_pdf_core/           # Headless engine — no UI dependencies
├── analyzer.py              # PDF analysis (PyMuPDF + pikepdf)
├── tools/                   # Tool implementations
│   ├── optimize/            # Optimization pipeline
│   │   ├── optimize.py      # Pipeline orchestrator
│   │   ├── presets.py       # Preset factories
│   │   ├── stages/          # Optimization stages
│   │   │   ├── lossless.py           # pikepdf (QPDF)
│   │   │   ├── lossy_images.py       # PyMuPDF
│   │   │   ├── lossy_ghostscript.py  # Ghostscript subprocess
│   │   │   └── cleanup.py            # Feature removal/flattening
│   │   └── verifier.py      # Output validation
│   ├── merge.py             # PDF merging
│   ├── metadata.py          # Metadata editing
│   ├── unlock.py            # Password removal
│   └── numbering.py         # Page numbering
├── models.py                # Data models
└── ...

safetool_pdf_cli/            # Command-line interface
safetool_pdf_desktop/        # PySide6 desktop application
├── screens/                 # UI screens for each tool
├── workers/                 # Background workers for processing
├── dialogs/                 # Settings, about, details dialogs
└── styles/                  # Design system and theming
```

## User Interface

- **Modern design**: Clean, intuitive interface with drag-and-drop support
- **Dark mode**: Light/dark/system theme toggle
- **Batch processing**: Queue multiple files, processed sequentially
- **Progress tracking**: Real-time progress updates with detailed feedback
- **Cross-platform**: Linux, macOS, Windows

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests excluding UI smoke tests
pytest --ignore=tests/test_ui_smoke.py

# Generate test PDFs
python tests/test_pdfs/generate_test_pdfs.py

# Validate translations
python dev-tools/validate_translations.py
```

## Ghostscript

Ghostscript is optional but enables font subsetting and maximum compression in the Optimize tool. If not available, those features are gracefully disabled.

- **Linux**: `sudo apt install ghostscript` or `brew install ghostscript`
- **macOS**: `brew install ghostscript`
- **Windows**: Download from [ghostscript.com](https://ghostscript.com/releases/gsdnld.html)

For packaged releases, Ghostscript is bundled in `vendor/gs/`.

## Building

See [BUILD_LOCAL.md](BUILD_LOCAL.md) for detailed instructions on building the application for different platforms.

## License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

**Attribution requirement**: Any distribution or derivative work must include attribution to SafeToolHub and [safetoolhub.org](https://safetoolhub.org).

See [LICENSE](LICENSE) for the full text.

## Links

- **Website**: [safetoolhub.org](https://safetoolhub.org)
- **Repository**: [github.com/safetoolhub/safetool-pdf](https://github.com/safetoolhub/safetool-pdf)
- **Contact**: safetoolhub@protonmail.com
