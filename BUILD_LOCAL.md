# BUILD_LOCAL.md - SafeTool PDF Local Build Guide

## Table of Contents

1. [Introduction](#1-introduction)
   - [Purpose](#purpose)
   - [Prerequisites Overview](#prerequisites-overview)
   - [Quick Start (TL;DR)](#quick-start-tldr)

2. [System Requirements](#2-system-requirements)
   - [2.1 Common Requirements (All Platforms)](#21-common-requirements-all-platforms)
   - [2.2 Linux Requirements](#22-linux-requirements)
   - [2.3 macOS Requirements](#23-macos-requirements)
   - [2.4 Windows Requirements](#24-windows-requirements)

3. [Build Process Overview](#3-build-process-overview)
   - [3.1 Two-Phase Build System](#31-two-phase-build-system)
   - [3.2 Build Script Architecture](#32-build-script-architecture)
   - [3.3 Output Artifacts by Platform](#33-output-artifacts-by-platform)

4. [Quick Start Guides](#4-quick-start-guides)
   - [4.1 Linux Quick Start](#41-linux-quick-start)
   - [4.2 macOS Quick Start](#42-macos-quick-start)
   - [4.3 Windows Quick Start](#43-windows-quick-start)

5. [Detailed Build Instructions](#5-detailed-build-instructions)
   - [5.1 Using the Unified Build Script (build.py)](#51-using-the-unified-build-script-buildpy)
   - [5.2 PyInstaller Build (Manual)](#52-pyinstaller-build-manual)
   - [5.3 Linux Packaging](#53-linux-packaging)
     - [5.3.1 .deb Package](#531-deb-package)
     - [5.3.2 .rpm Package](#532-rpm-package)
     - [5.3.3 AppImage](#533-appimage)
   - [5.4 macOS Packaging](#54-macos-packaging)
     - [5.4.1 .app Bundle](#541-app-bundle)
     - [5.4.2 DMG Creation](#542-dmg-creation)
   - [5.5 Windows Packaging](#55-windows-packaging)
     - [5.5.1 Inno Setup Installer](#551-inno-setup-installer)

6. [Ghostscript Integration](#6-ghostscript-integration)
   - [6.1 Vendored vs System Ghostscript](#61-vendored-vs-system-ghostscript)
   - [6.2 Downloading Vendored Ghostscript](#62-downloading-vendored-ghostscript)
   - [6.3 Verification](#63-verification)

7. [Verification and Testing](#7-verification-and-testing)
   - [7.1 Pre-Build Verification](#71-pre-build-verification)
   - [7.2 Post-Build Verification](#72-post-build-verification)
   - [7.3 Functional Testing Checklist](#73-functional-testing-checklist)

8. [Troubleshooting](#8-troubleshooting)
   - [8.1 Common Build Errors](#81-common-build-errors)
   - [8.2 Platform-Specific Issues](#82-platform-specific-issues)
   - [8.3 Diagnostic Commands](#83-diagnostic-commands)

9. [Advanced Topics](#9-advanced-topics)
   - [9.1 CI vs Local Builds](#91-ci-vs-local-builds)
   - [9.2 Packaging Directory Structure](#92-packaging-directory-structure)
   - [9.3 Customizing Build Scripts](#93-customizing-build-scripts)
   - [9.4 Cross-Platform Considerations](#94-cross-platform-considerations)

10. [Reference](#10-reference)
    - [10.1 Build Script Options](#101-build-script-options)
    - [10.2 Environment Variables](#102-environment-variables)
    - [10.3 File Locations](#103-file-locations)

---

## 1. Introduction

### Purpose

SafeTool PDF is a Python-based (PyQt6) PDF optimization application that uses GitHub Actions to create multi-platform binaries (.rpm, .deb, flatpak, AppImage, macOS DMG, Windows installer). This document provides comprehensive instructions for building SafeTool PDF binaries locally on Linux, macOS, and Windows without relying on GitHub Actions.

This guide enables developers to:

- Build distribution-ready binaries on their local machines
- Test changes before pushing to CI/CD pipelines
- Understand the complete build process for each platform
- Troubleshoot common build issues independently
- Customize the build process for specific needs

### Prerequisites Overview

Before starting the build process, you will need:

- **Python 3.12 or higher** - The minimum required Python version
- **PyInstaller 6.0+** - For bundling the Python application into standalone executables
- **Platform-specific build tools** - Varies by target platform (detailed in Section 2)
- **Ghostscript (optional)** - For advanced PDF processing features
- **Basic command-line knowledge** - Familiarity with terminal/command prompt usage

The build process follows a two-phase approach:

1. **Phase 1: PyInstaller** - Common to all platforms, creates a bundled executable directory
2. **Phase 2: Platform Packaging** - Creates platform-specific distribution formats (.deb, .rpm, AppImage, DMG, .exe installer)

### Quick Start (TL;DR)

For experienced developers who want to build immediately:

**Linux:**
```bash
pip install -r requirements.txt
python dev-tools/build.py
```

**macOS:**
```bash
pip install -r requirements.txt
python dev-tools/build.py
```

**Windows:**
```cmd
pip install -r requirements.txt
python dev-tools\build.py
```

The unified build script (`build.py`) automatically detects your platform and executes the appropriate build steps. Artifacts will be created in the `dist/` directory.

For detailed step-by-step instructions, platform-specific requirements, and troubleshooting, continue reading the sections below.

---

## 2. System Requirements

This section details all dependencies required to build SafeTool PDF binaries on your platform. The build process requires both common dependencies (shared across all platforms) and platform-specific tools for creating native packages.

### 2.1 Common Requirements (All Platforms)

These dependencies are required regardless of your operating system:

#### Core Dependencies

| Dependency | Min Version | Required | Purpose |
|------------|-------------|----------|---------|
| Python | 3.12 | Yes | Runtime and build environment |
| pip | Latest | Yes | Python package manager |
| PyInstaller | 6.0+ | Yes | Bundle Python app into standalone executable |
| pikepdf | 9.0+ | Yes | PDF manipulation library |
| PyMuPDF | 1.25+ | Yes | PDF rendering and processing |
| PySide6-Essentials | 6.7+ | Yes | Qt6 GUI framework |
| Pillow | 10.0+ | Yes | Image processing |
| qtawesome | 1.4+ | Yes | Icon fonts for Qt |

#### Development Dependencies (Optional)

| Dependency | Min Version | Required | Purpose |
|------------|-------------|----------|---------|
| pytest | 8.0+ | No | Unit testing framework |
| pytest-qt | 4.0+ | No | Qt testing utilities |
| fpdf2 | 2.0+ | No | PDF generation for tests |
| reportlab | 4.0+ | No | PDF generation library |

#### Installing Python Dependencies

All Python dependencies are listed in `requirements.txt`. Install them with:

```bash
pip install -r requirements.txt
```

Or install only runtime dependencies:

```bash
pip install pikepdf PyMuPDF PySide6-Essentials Pillow qtawesome pyinstaller
```

#### Verifying Python Installation

Check your Python version:

```bash
python --version
# Should output: Python 3.12.x or higher
```

Check PyInstaller installation:

```bash
python -m PyInstaller --version
# Should output: 6.0 or higher
```

### 2.2 Linux Requirements

Linux builds can create three package formats: `.deb` (Debian/Ubuntu), `.rpm` (Fedora/RHEL), and AppImage (universal).

#### System Dependencies by Distribution

**Ubuntu/Debian (apt):**

```bash
# Essential build tools
sudo apt update
sudo apt install python3.12 python3-pip python3-venv

# Package creation tools
sudo apt install dpkg-deb rpm fuse libfuse2

# Optional: For building all formats
sudo apt install build-essential
```

**Fedora/RHEL/CentOS (dnf/yum):**

```bash
# Essential build tools
sudo dnf install python3.12 python3-pip

# Package creation tools
sudo dnf install dpkg rpm-build fuse fuse-libs

# Optional: Development tools
sudo dnf groupinstall "Development Tools"
```

**Arch Linux (pacman):**

```bash
# Essential build tools
sudo pacman -S python python-pip

# Package creation tools
sudo pacman -S dpkg rpm-tools fuse2

# Optional: Base development tools
sudo pacman -S base-devel
```

#### Linux-Specific Build Tools

| Tool | Required For | Installation | Purpose |
|------|--------------|--------------|---------|
| dpkg-deb | .deb packages | Pre-installed on Debian/Ubuntu | Create Debian packages |
| rpmbuild | .rpm packages | `sudo apt install rpm` (Ubuntu)<br>`sudo dnf install rpm-build` (Fedora) | Create RPM packages |
| appimagetool | AppImage | Auto-downloaded by build script | Create portable AppImage |
| fuse | AppImage testing | `sudo apt install fuse libfuse2` | Mount AppImage for testing |

#### Ghostscript (Optional)

Ghostscript enables advanced PDF processing features. On Linux, the system-installed version is used:

**Ubuntu/Debian:**
```bash
sudo apt install ghostscript
```

**Fedora/RHEL:**
```bash
sudo dnf install ghostscript
```

**Arch Linux:**
```bash
sudo pacman -S ghostscript
```

Verify installation:
```bash
gs --version
```

### 2.3 macOS Requirements

macOS builds create a `.app` bundle and `.dmg` disk image for distribution.

#### System Dependencies

**Homebrew (Recommended Package Manager):**

If you don't have Homebrew installed:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Install Build Dependencies:**

```bash
# Python 3.12+
brew install python@3.12

# DMG creation tool
brew install create-dmg

# Optional: Ghostscript for advanced PDF features
brew install ghostscript
```

#### macOS-Specific Build Tools

| Tool | Required For | Installation | Purpose |
|------|--------------|--------------|---------|
| create-dmg | DMG creation | `brew install create-dmg` | Create macOS disk images |
| codesign | Code signing | Pre-installed (Xcode Command Line Tools) | Ad-hoc code signing |
| hdiutil | DMG fallback | Pre-installed | Alternative DMG creation tool |

#### Xcode Command Line Tools

Required for `codesign` and other build utilities:

```bash
xcode-select --install
```

Verify installation:
```bash
codesign --version
```

#### Ghostscript (Optional)

```bash
brew install ghostscript
```

Verify installation:
```bash
gs --version
```

**Note:** On macOS, Ghostscript can be bundled with the application (vendored) or use the system installation. The build script will attempt to download a vendored version for inclusion in the `.app` bundle.

### 2.4 Windows Requirements

Windows builds create an executable installer using Inno Setup.

#### System Dependencies

**Python 3.12+:**

Download and install from [python.org](https://www.python.org/downloads/):
- Check "Add Python to PATH" during installation
- Verify: `python --version` in Command Prompt

**Chocolatey (Recommended Package Manager):**

If you don't have Chocolatey installed, run PowerShell as Administrator:
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

**Install Build Dependencies via Chocolatey:**

```cmd
choco install python312 innosetup
```

#### Windows-Specific Build Tools

| Tool | Required For | Installation | Purpose |
|------|--------------|--------------|---------|
| Inno Setup 6 | Installer creation | `choco install innosetup`<br>or [Manual Download](https://jrsoftware.org/isdl.php) | Create Windows setup wizard |
| ISCC (Inno Setup Compiler) | Installer compilation | Included with Inno Setup | Command-line compiler |

#### Manual Installation (Alternative to Chocolatey)

**Inno Setup:**
1. Download from [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php)
2. Run the installer
3. Add to PATH: `C:\Program Files (x86)\Inno Setup 6\`

Verify installation:
```cmd
iscc /?
```

#### Ghostscript (Optional)

**Via Chocolatey:**
```cmd
choco install ghostscript
```

**Manual Installation:**
1. Download from [ghostscript.com](https://www.ghostscript.com/releases/gsdnld.html)
2. Run the installer
3. Verify: `gswin64c --version`

**Note:** On Windows, the build script automatically downloads a vendored version of Ghostscript to bundle with the application. This ensures users don't need to install Ghostscript separately. The system-installed version is not used.

#### Verifying Windows Build Environment

Check all required tools:

```cmd
REM Python
python --version

REM pip
pip --version

REM PyInstaller
python -m PyInstaller --version

REM Inno Setup
iscc /?

REM Optional: Ghostscript
gswin64c --version
```

---

## 3. Build Process Overview

SafeTool PDF uses a two-phase build system that first creates a standalone executable bundle with PyInstaller, then packages it into platform-specific distribution formats. Understanding this architecture helps you troubleshoot issues and customize the build process.

### 3.1 Two-Phase Build System

The build process is divided into two distinct phases:

#### Phase 1: PyInstaller (Common to All Platforms)

PyInstaller is the first and most critical step, shared across all platforms. It bundles the Python application, all dependencies, and assets into a standalone executable directory.

**What PyInstaller Does:**
- Analyzes the application to detect all Python dependencies
- Bundles the Python interpreter and required libraries
- Packages application code, assets, and translations
- Creates a self-contained executable that doesn't require Python installation
- Includes vendored Ghostscript binaries (if available)

**PyInstaller Command:**

```bash
python -m PyInstaller packaging/pyinstaller/safetool-pdf.spec
```

**Environment Variables:**

| Variable | Purpose | Example |
|----------|---------|---------|
| `APP_VERSION` | Sets the application version in the build | `APP_VERSION=1.0.0` |

**Output Structure:**

PyInstaller creates a directory in `dist/` with all bundled files:

**Linux/Windows:**
```
dist/safetool-pdf/
├── safetool-pdf-desktop          # Main executable
├── _internal/                     # Python runtime and libraries
│   ├── Python libraries (.so/.dll)
│   ├── PyQt6 modules
│   └── Other dependencies
├── assets/                        # Application assets
│   ├── icon.png
│   └── ...
├── i18n/                         # Translation files
│   ├── es.json
│   ├── fr.json
│   └── ...
├── vendor/                       # Vendored binaries
│   └── gs/                       # Ghostscript (if downloaded)
│       └── bin/
└── LICENSE
```

**macOS:**
```
dist/SafeToolPDF/
├── SafeToolPDF                   # Main executable
├── _internal/                    # Python runtime and libraries
├── assets/                       # Application assets
├── i18n/                        # Translation files
├── vendor/                      # Vendored binaries
└── LICENSE
```

**The .spec File:**

The `packaging/pyinstaller/safetool-pdf.spec` file controls what gets bundled:

- **Entry Point**: `safetool_pdf_desktop/app.py` - The main application file
- **Data Files**: Assets, translations, LICENSE, config files
- **Binaries**: Vendored Ghostscript from `packaging/vendor/gs/`
- **Hidden Imports**: Modules that PyInstaller might miss (PySide6, pikepdf, fitz, PIL, qtawesome)
- **Excludes**: Unnecessary modules (tkinter, test packages)
- **Platform-Specific Settings**: Icon files (.icns for macOS, .ico for Windows, .png for Linux)

**Verifying PyInstaller Build:**

After PyInstaller completes, verify the build was successful:

```bash
# Check that the output directory exists
ls -la dist/safetool-pdf/          # Linux/Windows
ls -la dist/SafeToolPDF/            # macOS

# Check the executable exists
ls -lh dist/safetool-pdf/safetool-pdf-desktop*    # Linux/Windows
ls -lh dist/SafeToolPDF/SafeToolPDF*              # macOS

# Test the executable directly (optional)
./dist/safetool-pdf/safetool-pdf-desktop          # Linux
dist\safetool-pdf\safetool-pdf-desktop.exe        # Windows
./dist/SafeToolPDF/SafeToolPDF                    # macOS
```

**Expected Output:**

When PyInstaller succeeds, you should see:
```
Building EXE from EXE-00.toc completed successfully.
✅ PyInstaller output: dist/safetool-pdf
```

**Typical Build Time:** 2-3 minutes (depends on system performance)

#### Phase 2: Platform-Specific Packaging

After PyInstaller creates the executable bundle, platform-specific scripts package it into native distribution formats.

**Linux:**
- `.deb` package (Debian/Ubuntu) - Created with `dpkg-deb`
- `.rpm` package (Fedora/RHEL) - Created with `rpmbuild`
- `AppImage` (Universal) - Created with `appimagetool`

**macOS:**
- `.app` bundle - Created by PyInstaller BUNDLE directive
- `.dmg` disk image - Created with `create-dmg` or `hdiutil`

**Windows:**
- `.exe` installer - Created with Inno Setup

**Phase 2 Commands:**

You can run Phase 2 manually after PyInstaller, or use the unified build script:

**Linux:**
```bash
# .deb and .rpm (automatic via build.py)
python dev-tools/build.py

# AppImage only
bash packaging/linux/appimage/build_appimage.sh
```

**macOS:**
```bash
# .dmg creation
bash packaging/macos/build_macos.sh
```

**Windows:**
```cmd
REM Inno Setup installer
packaging\windows\build_windows.bat
```

**Or use the unified script for all platforms:**
```bash
python dev-tools/build.py
```

**Skip Phase 2 (PyInstaller Only):**

If you only need the PyInstaller bundle without platform packaging:

```bash
python dev-tools/build.py --skip-installer
```

This is useful for:
- Testing the application quickly
- Debugging build issues
- Creating a portable directory without an installer

---

## 4. Quick Start Guides

These quick start guides provide the fastest path to building SafeTool PDF binaries on your platform. Each guide assumes you have basic command-line knowledge and follows a streamlined 5-step process. For detailed explanations, troubleshooting, and customization options, refer to the subsequent sections.

### 4.1 Linux Quick Start

**Prerequisites:** Ubuntu 22.04+, Debian 11+, Fedora 39+, or equivalent distribution

**Estimated Time:** 5-10 minutes

#### Step 1: Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.12 python3-pip dpkg-deb rpm fuse libfuse2
```

**Fedora/RHEL:**
```bash
sudo dnf install python3.12 python3-pip dpkg rpm-build fuse fuse-libs
```

#### Step 2: Clone Repository and Install Python Dependencies

```bash
# Navigate to the project directory (if not already there)
cd safetool-pdf

# Install Python dependencies
pip install -r requirements.txt
```

#### Step 3: Run the Unified Build Script

```bash
python dev-tools/build.py
```

The build script will:
- Execute PyInstaller to bundle the application (2-3 minutes)
- Create .deb, .rpm, and AppImage packages (1-2 minutes)
- Display a build summary with artifact locations

#### Step 4: Locate Build Artifacts

After successful build, find your packages in the `dist/` directory:

```bash
ls -lh dist/SafeToolPDF-*
```

Expected artifacts:
- `SafeToolPDF-{version}-linux-amd64.deb` - Debian/Ubuntu package (~75 MB)
- `SafeToolPDF-{version}-linux-x86_64.rpm` - Fedora/RHEL package (~75 MB)
- `SafeToolPDF-x86_64.AppImage` - Universal Linux package (~80 MB)

#### Step 5: Verify the Build

Test the AppImage (no installation required):

```bash
chmod +x dist/SafeToolPDF-x86_64.AppImage
./dist/SafeToolPDF-x86_64.AppImage
```

Or install and test the .deb package:

```bash
sudo dpkg -i dist/SafeToolPDF-*-linux-amd64.deb
safetool-pdf-desktop
```

**✅ Success Indicators:**
- Build script completes with "Build Summary" message
- Three package files exist in `dist/` directory
- Application launches and displays the main window
- No error messages in the terminal

**❌ If Something Goes Wrong:**
- Check [Section 8.1: Common Build Errors](#81-common-build-errors) for solutions
- Verify all dependencies are installed: `python --version`, `dpkg-deb --version`, `rpm --version`
- Ensure you're using Python 3.12+: `python --version`

---

### 4.2 macOS Quick Start

**Prerequisites:** macOS 13 (Ventura) or later, Homebrew installed

**Estimated Time:** 5-10 minutes

#### Step 1: Install System Dependencies

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.12 and build tools
brew install python@3.12 create-dmg

# Install Xcode Command Line Tools (for codesign)
xcode-select --install
```

#### Step 2: Clone Repository and Install Python Dependencies

```bash
# Navigate to the project directory (if not already there)
cd safetool-pdf

# Install Python dependencies
pip3 install -r requirements.txt
```

#### Step 3: Run the Unified Build Script

```bash
python3 dev-tools/build.py
```

The build script will:
- Execute PyInstaller to create the .app bundle (2-3 minutes)
- Sign the application with ad-hoc signature
- Create a .dmg disk image (1-2 minutes)
- Display a build summary with artifact location

#### Step 4: Locate Build Artifact

After successful build, find your DMG in the `dist/` directory:

```bash
ls -lh dist/SafeToolPDF*.dmg
```

Expected artifact:
- `SafeToolPDF.dmg` - macOS disk image (~80 MB)

#### Step 5: Verify the Build

Mount and test the DMG:

```bash
# Open the DMG
open dist/SafeToolPDF.dmg

# Drag SafeToolPDF.app to Applications folder
# Then launch from Applications or double-click in the DMG
```

Or test the .app bundle directly:

```bash
open dist/SafeToolPDF.app
```

**✅ Success Indicators:**
- Build script completes with "Build Summary" message
- `SafeToolPDF.dmg` file exists in `dist/` directory
- DMG mounts successfully when opened
- Application launches without security warnings (ad-hoc signed)
- Main window displays correctly

**❌ If Something Goes Wrong:**
- Check [Section 8.2: Platform-Specific Issues](#82-platform-specific-issues) for macOS troubleshooting
- Verify Python version: `python3 --version` (should be 3.12+)
- Verify create-dmg is installed: `create-dmg --version`
- If you see "App is damaged" error, check [Section 8.2](#82-platform-specific-issues) for codesign solutions

---

### 4.3 Windows Quick Start

**Prerequisites:** Windows 10 or later, Administrator access

**Estimated Time:** 5-10 minutes

#### Step 1: Install System Dependencies

**Option A: Using Chocolatey (Recommended)**

Open PowerShell as Administrator and install Chocolatey:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

Then install dependencies:

```cmd
choco install python312 innosetup -y
```

**Option B: Manual Installation**

1. Download and install Python 3.12+ from [python.org](https://www.python.org/downloads/)
   - Check "Add Python to PATH" during installation
2. Download and install Inno Setup 6 from [jrsoftware.org](https://jrsoftware.org/isdl.php)
   - Add `C:\Program Files (x86)\Inno Setup 6\` to your PATH

#### Step 2: Clone Repository and Install Python Dependencies

Open Command Prompt or PowerShell:

```cmd
REM Navigate to the project directory (if not already there)
cd safetool-pdf

REM Install Python dependencies
pip install -r requirements.txt
```

#### Step 3: Run the Unified Build Script

```cmd
python dev-tools\build.py
```

The build script will:
- Execute PyInstaller to bundle the application (2-3 minutes)
- Download vendored Ghostscript (if not already present)
- Create Windows installer with Inno Setup (1-2 minutes)
- Display a build summary with artifact location

#### Step 4: Locate Build Artifact

After successful build, find your installer in the `dist/` directory:

```cmd
dir dist\SafeToolPDF-*-setup-x64.exe
```

Expected artifact:
- `SafeToolPDF-{version}-setup-x64.exe` - Windows installer (~85 MB)

**Note:** If Inno Setup is not installed, the build script will still create a portable version in `dist/safetool-pdf/` that can be run without installation.

#### Step 5: Verify the Build

Run the installer:

```cmd
REM Run the installer (double-click or execute from command line)
dist\SafeToolPDF-*-setup-x64.exe
```

Or test the portable version directly:

```cmd
dist\safetool-pdf\safetool-pdf-desktop.exe
```

**✅ Success Indicators:**
- Build script completes with "Build Summary" message
- Installer `.exe` file exists in `dist/` directory (or portable folder if Inno Setup not installed)
- Installer runs and completes successfully
- Application launches from Start Menu or Desktop shortcut
- Main window displays correctly

**❌ If Something Goes Wrong:**
- Check [Section 8.1: Common Build Errors](#81-common-build-errors) for solutions
- Verify Python version: `python --version` (should be 3.12+)
- Verify Inno Setup: `iscc /?` (if you want the installer)
- If PyInstaller fails, check [Section 8.1](#81-common-build-errors) for hidden import issues
- If Inno Setup is missing, you can still use the portable version in `dist/safetool-pdf/`

---

**Next Steps:**

- For detailed build instructions and customization options, see [Section 5: Detailed Build Instructions](#5-detailed-build-instructions)
- To include Ghostscript for advanced PDF features, see [Section 6: Ghostscript Integration](#6-ghostscript-integration)
- For comprehensive testing procedures, see [Section 7: Verification and Testing](#7-verification-and-testing)
- If you encounter issues, consult [Section 8: Troubleshooting](#8-troubleshooting)

---


## 5. Detailed Build Instructions

This section provides comprehensive, step-by-step instructions for building SafeTool PDF binaries using both the unified build script and manual platform-specific methods. These instructions are more detailed than the Quick Start guides and include explanations of what each step does, customization options, and verification procedures.

### 5.1 Using the Unified Build Script (build.py)

The unified build script (`dev-tools/build.py`) is the recommended method for building SafeTool PDF binaries. It automatically detects your platform, executes PyInstaller, and creates the appropriate distribution packages.

#### Purpose

The `build.py` script orchestrates the entire build process:

1. Detects the current platform (Linux, macOS, Windows)
2. Optionally downloads vendored Ghostscript for Windows/macOS
3. Executes PyInstaller with the correct spec file
4. Runs platform-specific packaging scripts
5. Displays a build summary with artifact locations

#### Basic Usage

```bash
# Build everything (PyInstaller + platform packages)
python dev-tools/build.py
```

#### Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--skip-installer` | Only run PyInstaller, skip platform packaging | `python dev-tools/build.py --skip-installer` |
| `--help` | Display help message with all options | `python dev-tools/build.py --help` |

#### Examples by Platform

**Linux - Build all formats (.deb, .rpm, AppImage):**

```bash
python dev-tools/build.py
```

**Linux - PyInstaller only (no packages):**

```bash
python dev-tools/build.py --skip-installer
```

**macOS - Build .app bundle and DMG:**

```bash
python dev-tools/build.py
```

**Windows - Build installer:**

```cmd
python dev-tools\build.py
```

#### What build.py Does

**Phase 1: Ghostscript Download (Windows/macOS only)**

The script checks if vendored Ghostscript exists in `packaging/vendor/gs/`. If not, it attempts to download it:

```bash
python packaging/scripts/download_ghostscript.py
```

This step is optional and will not fail the build if it doesn't succeed (continue-on-error behavior).

**Phase 2: PyInstaller Execution**

The script runs PyInstaller with the platform-specific spec file:

```bash
python -m PyInstaller packaging/pyinstaller/safetool-pdf.spec
```

**Phase 3: Platform Packaging**

Depending on your platform, the script executes:

- **Linux**: Creates .deb, .rpm, and AppImage packages
- **macOS**: Runs `packaging/macos/build_macos.sh` to create DMG
- **Windows**: Runs `packaging/windows/build_windows.bat` to create installer

**Phase 4: Build Summary**

The script displays a summary of created artifacts:

```
=== Build Summary ===
✅ PyInstaller output: dist/safetool-pdf
✅ Debian package: dist/SafeToolPDF-1.0.0-linux-amd64.deb
✅ RPM package: dist/SafeToolPDF-1.0.0-linux-x86_64.rpm
✅ AppImage: dist/SafeToolPDF-x86_64.AppImage
```

#### Environment Variables

You can customize the build with environment variables:

| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `APP_VERSION` | Set application version | Auto-detected from `config.py` | `APP_VERSION=1.2.0 python dev-tools/build.py` |

#### Verifying build.py Success

After `build.py` completes successfully, you should see:

1. **No error messages** in the terminal output
2. **Build Summary** section listing all created artifacts
3. **Artifact files** in the `dist/` directory

Check artifacts:

```bash
# Linux
ls -lh dist/SafeToolPDF-*

# macOS
ls -lh dist/SafeToolPDF.dmg

# Windows
dir dist\SafeToolPDF-*-setup-x64.exe
```

#### Troubleshooting build.py

**Error: "PyInstaller failed"**
- Check that all Python dependencies are installed: `pip install -r requirements.txt`
- Verify Python version: `python --version` (must be 3.12+)
- Run PyInstaller manually to see detailed error: `python -m PyInstaller packaging/pyinstaller/safetool-pdf.spec`

**Error: "Platform packaging failed"**
- Check that platform-specific tools are installed (see [Section 2](#2-system-requirements))
- Try running with `--skip-installer` to isolate the issue
- Check platform-specific troubleshooting in [Section 8.2](#82-platform-specific-issues)

---

### 5.2 PyInstaller Build (Manual)

PyInstaller is the first and most critical step in the build process. This section explains how to run PyInstaller manually, which is useful for debugging, testing, or when you only need the bundled executable without platform-specific packaging.

#### Why PyInstaller First?

PyInstaller must be run before any platform-specific packaging because:

1. It creates the standalone executable bundle that all packaging formats use
2. Platform scripts expect to find the PyInstaller output in `dist/safetool-pdf/` (or `dist/SafeToolPDF/` on macOS)
3. It bundles all Python dependencies, assets, and translations into a single directory

#### Manual PyInstaller Command

```bash
python -m PyInstaller packaging/pyinstaller/safetool-pdf.spec
```

**Estimated Time:** 2-3 minutes

#### Understanding the .spec File

The `packaging/pyinstaller/safetool-pdf.spec` file controls what gets bundled. Key sections:

**Entry Point:**
```python
a = Analysis(
    ['safetool_pdf_desktop/app.py'],  # Main application file
    ...
)
```

**Data Files (Assets, Translations, License):**
```python
datas=[
    ('assets', 'assets'),
    ('i18n', 'i18n'),
    ('LICENSE', '.'),
    ('config.py', '.'),
],
```

**Vendored Binaries (Ghostscript):**
```python
binaries=[
    # Ghostscript from packaging/vendor/gs/ if present
],
```

**Hidden Imports (Modules PyInstaller might miss):**
```python
hiddenimports=[
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'pikepdf',
    'fitz',  # PyMuPDF
    'PIL',
    'qtawesome',
],
```

**Excluded Modules (Reduce bundle size):**
```python
excludes=[
    'tkinter',
    'test',
    'unittest',
],
```

#### PyInstaller Output Structure

After PyInstaller completes, you'll find the bundled application in:

**Linux/Windows:**
```
dist/safetool-pdf/
├── safetool-pdf-desktop          # Main executable
├── safetool-pdf-desktop.exe      # (Windows only)
├── _internal/                     # Python runtime and libraries
│   ├── *.so / *.dll              # Shared libraries
│   ├── PySide6/                  # Qt6 framework
│   ├── pikepdf/                  # PDF library
│   ├── fitz/                     # PyMuPDF
│   └── ...                       # Other dependencies
├── assets/                        # Application assets
│   ├── icon.png
│   └── ...
├── i18n/                         # Translation files
│   ├── es.json
│   ├── fr.json
│   └── ...
├── vendor/                       # Vendored binaries (if present)
│   └── gs/                       # Ghostscript
│       └── bin/
│           └── gs / gswin64c.exe
├── config.py                     # Application configuration
└── LICENSE                       # License file
```

**macOS:**
```
dist/SafeToolPDF/
├── SafeToolPDF                   # Main executable
├── _internal/                    # Python runtime and libraries
├── assets/                       # Application assets
├── i18n/                        # Translation files
├── vendor/                      # Vendored binaries
├── config.py
└── LICENSE
```

**Note:** On macOS, the BUNDLE directive in the .spec file creates a `.app` bundle structure:

```
dist/SafeToolPDF.app/
└── Contents/
    ├── MacOS/
    │   └── SafeToolPDF           # Executable
    ├── Resources/                # Assets, translations
    ├── Frameworks/               # Qt and other frameworks
    └── Info.plist                # macOS metadata
```

#### Verifying PyInstaller Output

**Check that the output directory exists:**

```bash
# Linux/Windows
ls -la dist/safetool-pdf/

# macOS (directory)
ls -la dist/SafeToolPDF/

# macOS (.app bundle)
ls -la dist/SafeToolPDF.app/
```

**Check the executable exists and has correct permissions:**

```bash
# Linux
ls -lh dist/safetool-pdf/safetool-pdf-desktop
file dist/safetool-pdf/safetool-pdf-desktop

# Windows
dir dist\safetool-pdf\safetool-pdf-desktop.exe

# macOS
ls -lh dist/SafeToolPDF.app/Contents/MacOS/SafeToolPDF
```

**Check that assets and translations are included:**

```bash
# Linux/Windows
ls dist/safetool-pdf/assets/
ls dist/safetool-pdf/i18n/

# macOS
ls dist/SafeToolPDF.app/Contents/Resources/assets/
ls dist/SafeToolPDF.app/Contents/Resources/i18n/
```

**Test the executable directly (optional):**

```bash
# Linux
./dist/safetool-pdf/safetool-pdf-desktop

# Windows
dist\safetool-pdf\safetool-pdf-desktop.exe

# macOS
./dist/SafeToolPDF.app/Contents/MacOS/SafeToolPDF
# Or double-click the .app bundle
open dist/SafeToolPDF.app
```

If the application launches and displays the main window, PyInstaller succeeded.

#### Expected Output Messages

When PyInstaller runs successfully, you should see:

```
Building EXE from EXE-00.toc
Building EXE from EXE-00.toc completed successfully.
```

**On macOS (with BUNDLE):**
```
Building BUNDLE BUNDLE-00.toc
Building BUNDLE BUNDLE-00.toc completed successfully.
```

#### Common PyInstaller Issues

**Error: "ModuleNotFoundError: No module named 'X'"**

PyInstaller missed a hidden import. Add it to the `hiddenimports` list in the .spec file:

```python
hiddenimports=[
    'PySide6.QtCore',
    'X',  # Add the missing module here
],
```

**Error: "FileNotFoundError: [Errno 2] No such file or directory: 'assets/icon.png'"**

Data files are not being collected. Check the `datas` list in the .spec file:

```python
datas=[
    ('assets', 'assets'),  # Ensure this line exists
],
```

**Warning: "Hidden import 'X' not found"**

This is usually safe to ignore if the application runs correctly. PyInstaller lists potential imports that may not be needed.

**Large bundle size (>200 MB)**

Check if unnecessary modules are being included. Add them to `excludes`:

```python
excludes=[
    'tkinter',
    'matplotlib',  # If not used
    'numpy',       # If not used
],
```

For more PyInstaller troubleshooting, see [Section 8.1: Common Build Errors](#81-common-build-errors).

---

### 5.3 Linux Packaging

Linux builds can create three distribution formats: `.deb` (Debian/Ubuntu), `.rpm` (Fedora/RHEL/CentOS), and `AppImage` (universal portable format). Each format has different requirements and use cases.

#### Prerequisites for Linux Packaging

Before creating Linux packages, ensure:

1. **PyInstaller has been run** - The `dist/safetool-pdf/` directory must exist
2. **Platform tools are installed** - See [Section 2.2: Linux Requirements](#22-linux-requirements)
3. **Permissions are correct** - Shell scripts must be executable (`chmod +x`)

#### 5.3.1 .deb Package

Debian packages (`.deb`) are used on Debian, Ubuntu, Linux Mint, and other Debian-based distributions.

**Requirements:**
- `dpkg-deb` (pre-installed on Debian/Ubuntu)

**Build Command:**

The unified build script automatically creates .deb packages on Linux:

```bash
python dev-tools/build.py
```

**Manual Creation:**

The .deb package is created by the build script's internal logic. There is no standalone script for .deb creation.

**Output Location:**

```
dist/SafeToolPDF-{version}-linux-amd64.deb
```

Example: `dist/SafeToolPDF-1.0.0-linux-amd64.deb`

**Typical Size:** ~75 MB

**Verification:**

Check package info:

```bash
dpkg-deb --info dist/SafeToolPDF-*-linux-amd64.deb
```

List package contents:

```bash
dpkg-deb --contents dist/SafeToolPDF-*-linux-amd64.deb
```

**Installation and Testing:**

```bash
# Install the package
sudo dpkg -i dist/SafeToolPDF-*-linux-amd64.deb

# Launch the application
safetool-pdf-desktop

# Or from the application menu
# Look for "SafeTool PDF" in your desktop environment's application launcher

# Uninstall
sudo dpkg -r safetoolpdf
```

**Package Contents:**

The .deb package installs files to:

- `/opt/safetool-pdf/` - Application files
- `/usr/share/applications/` - Desktop entry
- `/usr/share/icons/` - Application icon
- `/usr/bin/safetool-pdf-desktop` - Symlink to executable

---

#### 5.3.2 .rpm Package

RPM packages (`.rpm`) are used on Fedora, RHEL, CentOS, openSUSE, and other RPM-based distributions.

**Requirements:**
- `rpmbuild` (install with `sudo apt install rpm` on Ubuntu or `sudo dnf install rpm-build` on Fedora)

**Build Command:**

The unified build script automatically creates .rpm packages on Linux:

```bash
python dev-tools/build.py
```

**Manual Creation:**

The .rpm package is created by the build script's internal logic. There is no standalone script for .rpm creation.

**Output Location:**

```
dist/SafeToolPDF-{version}-linux-x86_64.rpm
```

Example: `dist/SafeToolPDF-1.0.0-linux-x86_64.rpm`

**Typical Size:** ~75 MB

**Verification:**

Check package info:

```bash
rpm -qpi dist/SafeToolPDF-*-linux-x86_64.rpm
```

List package contents:

```bash
rpm -qpl dist/SafeToolPDF-*-linux-x86_64.rpm
```

**Installation and Testing:**

```bash
# Install the package (Fedora/RHEL)
sudo dnf install dist/SafeToolPDF-*-linux-x86_64.rpm

# Or using rpm directly
sudo rpm -ivh dist/SafeToolPDF-*-linux-x86_64.rpm

# Launch the application
safetool-pdf-desktop

# Uninstall
sudo dnf remove SafeToolPDF
# Or
sudo rpm -e SafeToolPDF
```

**Package Contents:**

The .rpm package installs files to the same locations as the .deb package:

- `/opt/safetool-pdf/` - Application files
- `/usr/share/applications/` - Desktop entry
- `/usr/share/icons/` - Application icon
- `/usr/bin/safetool-pdf-desktop` - Symlink to executable

---

#### 5.3.3 AppImage

AppImage is a universal, portable format for Linux applications. It doesn't require installation or root privileges and works on most Linux distributions.

**What is AppImage?**

AppImage is a format for distributing portable software on Linux. Key benefits:

- **No installation required** - Run directly by making it executable
- **No root privileges needed** - Users can run without sudo
- **Distribution-agnostic** - Works on Ubuntu, Fedora, Arch, etc.
- **Self-contained** - Includes all dependencies
- **Portable** - Can be run from USB drives or network shares

**Requirements:**

- `fuse` and `libfuse2` - For mounting the AppImage filesystem
  ```bash
  # Ubuntu/Debian
  sudo apt install fuse libfuse2
  
  # Fedora/RHEL
  sudo dnf install fuse fuse-libs
  
  # Arch Linux
  sudo pacman -S fuse2
  ```

- `appimagetool` - Automatically downloaded by the build script

**Build Command:**

**Option 1: Using the unified build script (recommended):**

```bash
python dev-tools/build.py
```

This creates .deb, .rpm, and AppImage packages.

**Option 2: Build AppImage only:**

```bash
bash packaging/linux/appimage/build_appimage.sh
```

**Important:** PyInstaller must be run first. If you haven't run PyInstaller yet:

```bash
# Run PyInstaller first
python -m PyInstaller packaging/pyinstaller/safetool-pdf.spec

# Then build AppImage
bash packaging/linux/appimage/build_appimage.sh
```

**What the build_appimage.sh Script Does:**

The script performs these steps:

1. **Verifies PyInstaller output exists** - Checks for `dist/safetool-pdf/`
2. **Creates AppDir structure** - Standard AppImage directory layout
3. **Copies PyInstaller bundle** - Places application in `AppDir/opt/safetool-pdf/`
4. **Installs desktop entry** - Adds `.desktop` file for application metadata
5. **Installs icon** - Copies application icon to standard location
6. **Installs AppStream metadata** - Adds `.metainfo.xml` for software centers
7. **Creates AppRun script** - Entry point that launches the application
8. **Downloads appimagetool** - If not already present
9. **Builds the AppImage** - Packages AppDir into a single executable file

**AppDir Structure:**

The script creates this directory structure before packaging:

```
dist/AppDir/
├── AppRun                                    # Entry point script
├── org.safetoolhub.safetoolpdf.desktop      # Desktop entry (root)
├── org.safetoolhub.safetoolpdf.png          # Icon (root)
├── opt/
│   └── safetool-pdf/                        # PyInstaller bundle
│       ├── safetool-pdf-desktop             # Main executable
│       ├── _internal/                       # Python runtime
│       ├── assets/                          # Application assets
│       ├── i18n/                           # Translations
│       ├── vendor/                         # Ghostscript (if present)
│       └── ...
└── usr/
    └── share/
        ├── applications/
        │   └── org.safetoolhub.safetoolpdf.desktop
        ├── icons/
        │   └── hicolor/
        │       └── 512x512/
        │           └── apps/
        │               └── org.safetoolhub.safetoolpdf.png
        └── metainfo/
            ├── org.safetoolhub.safetoolpdf.metainfo.xml
            └── org.safetoolhub.safetoolpdf.appdata.xml
```

**AppRun Script:**

The `AppRun` script is the entry point for the AppImage. It:

1. Determines the AppImage mount point
2. Adds vendored Ghostscript to PATH (if present)
3. Executes the main application

```bash
#!/usr/bin/env bash
SELF="$(readlink -f "$0")"
APPDIR="${SELF%/*}"

# Make bundled Ghostscript available
if [ -d "${APPDIR}/opt/safetool-pdf/vendor/gs/bin" ]; then
    export PATH="${APPDIR}/opt/safetool-pdf/vendor/gs/bin:${PATH}"
fi

exec "${APPDIR}/opt/safetool-pdf/safetool-pdf-desktop" "$@"
```

**Output Location:**

```
dist/SafeToolPDF-x86_64.AppImage
```

**Typical Size:** ~80 MB

**Verification:**

Check that the AppImage was created:

```bash
ls -lh dist/SafeToolPDF-x86_64.AppImage
```

Check file type:

```bash
file dist/SafeToolPDF-x86_64.AppImage
```

Expected output:
```
dist/SafeToolPDF-x86_64.AppImage: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, for GNU/Linux 2.6.18, stripped
```

**Running the AppImage:**

Make it executable and run:

```bash
# Make executable
chmod +x dist/SafeToolPDF-x86_64.AppImage

# Run directly
./dist/SafeToolPDF-x86_64.AppImage
```

**Testing on Different Distributions:**

AppImages are designed to work across distributions. Test on:

- Ubuntu 22.04+
- Debian 11+
- Fedora 39+
- Arch Linux (latest)
- openSUSE Leap 15.5+

**Integration with Desktop Environment:**

To integrate the AppImage with your desktop environment:

```bash
# Move to a permanent location
mkdir -p ~/Applications
mv dist/SafeToolPDF-x86_64.AppImage ~/Applications/

# Make executable
chmod +x ~/Applications/SafeToolPDF-x86_64.AppImage

# Run once to register with desktop
~/Applications/SafeToolPDF-x86_64.AppImage
```

Some desktop environments will automatically detect the AppImage and add it to the application menu.

**Extracting AppImage Contents (for debugging):**

```bash
# Extract to a directory
./dist/SafeToolPDF-x86_64.AppImage --appimage-extract

# Contents will be in squashfs-root/
ls squashfs-root/
```

**Troubleshooting AppImage:**

**Error: "fuse: failed to exec fusermount: No such file or directory"**

Install fuse:
```bash
sudo apt install fuse libfuse2  # Ubuntu/Debian
sudo dnf install fuse fuse-libs # Fedora/RHEL
```

**Error: "Permission denied"**

Make the AppImage executable:
```bash
chmod +x dist/SafeToolPDF-x86_64.AppImage
```

**Error: "AppImage requires FUSE to run"**

If FUSE is not available (e.g., in containers), extract and run directly:
```bash
./dist/SafeToolPDF-x86_64.AppImage --appimage-extract
./squashfs-root/AppRun
```

**AppImage doesn't appear in application menu:**

This is normal. AppImages don't automatically integrate with desktop environments. You can:
- Run from terminal
- Create a manual desktop entry
- Use AppImageLauncher (third-party tool)

For more troubleshooting, see [Section 8.2: Platform-Specific Issues](#82-platform-specific-issues).

---


### 5.4 macOS Packaging

macOS builds create a `.app` bundle (the standard macOS application format) and a `.dmg` disk image for distribution. The `.app` bundle is a directory structure that contains the executable, resources, and metadata, while the DMG provides a convenient installer experience for users.

#### Prerequisites for macOS Packaging

Before creating macOS packages, ensure:

1. **PyInstaller has been run** - The `dist/safetool-pdf/` directory must exist
2. **Platform tools are installed** - See [Section 2.3: macOS Requirements](#23-macos-requirements)
3. **Xcode Command Line Tools** - Required for `codesign` utility
4. **create-dmg (optional)** - For enhanced DMG creation with custom styling

#### 5.4.1 .app Bundle

The `.app` bundle is the standard macOS application format. It appears as a single file in Finder but is actually a directory structure containing the executable, libraries, resources, and metadata.

**What is a .app Bundle?**

A macOS `.app` bundle is a directory with a specific structure defined by Apple:

```
SafeToolPDF.app/
└── Contents/
    ├── Info.plist                    # Application metadata
    ├── MacOS/                        # Executable and runtime files
    │   ├── safetool-pdf-desktop      # Main executable
    │   ├── _internal/                # Python runtime and libraries
    │   │   ├── *.dylib               # Shared libraries
    │   │   ├── PySide6/              # Qt6 framework
    │   │   ├── pikepdf/              # PDF library
    │   │   ├── fitz/                 # PyMuPDF
    │   │   └── ...                   # Other dependencies
    │   ├── assets/                   # Application assets
    │   │   ├── icon.png
    │   │   └── ...
    │   ├── i18n/                     # Translation files
    │   │   ├── es.json
    │   │   ├── fr.json
    │   │   └── ...
    │   ├── vendor/                   # Vendored binaries (if present)
    │   │   └── gs/                   # Ghostscript
    │   │       └── bin/
    │   ├── config.py                 # Application configuration
    │   └── LICENSE                   # License file
    └── Resources/                    # Application resources
        └── SafeToolPDF.icns          # Application icon
```

**Info.plist Metadata:**

The `Info.plist` file contains essential metadata about the application:

| Key | Value | Purpose |
|-----|-------|---------|
| `CFBundleName` | SafeTool PDF | Application name |
| `CFBundleIdentifier` | org.safetoolhub.SafeToolPDF | Unique bundle identifier |
| `CFBundleVersion` | 0.1.0 | Build version number |
| `CFBundleExecutable` | safetool-pdf-desktop | Name of the main executable |
| `CFBundleIconFile` | SafeToolPDF.icns | Application icon filename |
| `LSMinimumSystemVersion` | 11.0 | Minimum macOS version (Big Sur) |
| `NSHighResolutionCapable` | true | Supports Retina displays |
| `CFBundleDocumentTypes` | PDF | Supported file types |
| `LSApplicationCategoryType` | public.app-category.utilities | App Store category |

**Build Command:**

The `.app` bundle is created automatically by the `build_macos.sh` script:

```bash
bash packaging/macos/build_macos.sh
```

Or use the unified build script:

```bash
python dev-tools/build.py
```

**What the build_macos.sh Script Does:**

The script performs these steps to create the `.app` bundle:

1. **Verifies PyInstaller output exists** - Checks for `dist/safetool-pdf/`
2. **Creates .app directory structure** - Creates `Contents/MacOS/` and `Contents/Resources/`
3. **Copies Info.plist** - Installs application metadata from `packaging/macos/Info.plist`
4. **Copies PyInstaller bundle** - Places all files from `dist/safetool-pdf/` into `Contents/MacOS/`
5. **Copies application icon** - Installs `.icns` icon file into `Contents/Resources/`
6. **Ad-hoc code signs** - Signs the bundle with `codesign` for local use

**Manual .app Bundle Creation:**

If you need to create the `.app` bundle manually (without the script):

```bash
# Step 1: Verify PyInstaller output
ls dist/safetool-pdf/

# Step 2: Create bundle structure
mkdir -p dist/SafeToolPDF.app/Contents/MacOS
mkdir -p dist/SafeToolPDF.app/Contents/Resources

# Step 3: Copy Info.plist
cp packaging/macos/Info.plist dist/SafeToolPDF.app/Contents/

# Step 4: Copy PyInstaller output
cp -a dist/safetool-pdf/. dist/SafeToolPDF.app/Contents/MacOS/

# Step 5: Copy icon
cp assets/SafeToolPDF.icns dist/SafeToolPDF.app/Contents/Resources/

# Step 6: Ad-hoc sign
codesign --force --deep --sign - dist/SafeToolPDF.app
```

**Output Location:**

```
dist/SafeToolPDF.app
```

**Typical Size:** ~80 MB

**Verification:**

Check that the .app bundle was created:

```bash
ls -lh dist/SafeToolPDF.app
```

Check bundle structure:

```bash
ls -la dist/SafeToolPDF.app/Contents/
ls -la dist/SafeToolPDF.app/Contents/MacOS/
ls -la dist/SafeToolPDF.app/Contents/Resources/
```

Verify Info.plist:

```bash
plutil -lint dist/SafeToolPDF.app/Contents/Info.plist
```

Expected output:
```
dist/SafeToolPDF.app/Contents/Info.plist: OK
```

Check code signature:

```bash
codesign -dv dist/SafeToolPDF.app
```

Expected output (ad-hoc signature):
```
Executable=/path/to/dist/SafeToolPDF.app/Contents/MacOS/safetool-pdf-desktop
Identifier=safetool-pdf-desktop
Format=app bundle with Mach-O thin (x86_64)
CodeDirectory v=20500 size=... flags=0x2(adhoc) hashes=...
Signature=adhoc
```

**Running the .app Bundle:**

Double-click the `.app` bundle in Finder, or run from terminal:

```bash
open dist/SafeToolPDF.app
```

Or execute the binary directly:

```bash
./dist/SafeToolPDF.app/Contents/MacOS/safetool-pdf-desktop
```

**Code Signing:**

The build script performs **ad-hoc signing** with `codesign --sign -`. This is sufficient for local use and testing but not for distribution through the App Store or notarization.

**Ad-hoc Signature:**
- Allows the app to run on the local machine
- Satisfies Gatekeeper's basic requirements
- Does not require a Developer ID certificate
- Cannot be notarized or distributed widely

**For Distribution:**

If you need to distribute the app to other users, you'll need:

1. **Apple Developer ID certificate** - Sign with a real certificate
2. **Notarization** - Submit to Apple for malware scanning
3. **Stapling** - Attach notarization ticket to the app

These steps are beyond the scope of local builds. For local testing and development, ad-hoc signing is sufficient.

**Troubleshooting .app Bundle:**

**Error: "PyInstaller dist not found"**

Run PyInstaller first:
```bash
python -m PyInstaller packaging/pyinstaller/safetool-pdf.spec
```

**Error: "codesign failed"**

Install Xcode Command Line Tools:
```bash
xcode-select --install
```

**Error: "App is damaged and can't be opened"**

This usually means the code signature is invalid. Re-sign the app:
```bash
codesign --force --deep --sign - dist/SafeToolPDF.app
```

**Error: "Icon not found"**

The script looks for `assets/icon.icns` or `assets/SafeToolPDF.icns`. Ensure one of these files exists, or the app will use the default icon.

---

#### 5.4.2 DMG Creation

A DMG (Disk Image) is the standard distribution format for macOS applications. It provides a convenient installer experience where users can drag the app to their Applications folder.

**What is a DMG?**

A DMG is a mountable disk image that:

- **Mounts as a virtual disk** - Appears in Finder like a USB drive
- **Contains the .app bundle** - Users drag it to Applications
- **Provides visual installer** - Can include custom background, icons, and layout
- **Compresses the app** - Reduces download size
- **Is the standard distribution format** - Expected by macOS users

**Requirements:**

- `create-dmg` (optional, recommended) - For enhanced DMG with custom styling
  ```bash
  brew install create-dmg
  ```

- `hdiutil` (pre-installed) - Fallback for basic DMG creation

**Build Command:**

The DMG is created automatically by the `build_macos.sh` script:

```bash
bash packaging/macos/build_macos.sh
```

Or use the unified build script:

```bash
python dev-tools/build.py
```

**Important:** The script must create the `.app` bundle first (see [Section 5.4.1](#541-app-bundle)), then packages it into a DMG.

**What the build_macos.sh Script Does:**

After creating the `.app` bundle, the script creates a DMG:

1. **Checks for create-dmg** - Prefers `create-dmg` if available
2. **Creates styled DMG** - Uses `create-dmg` with custom window size, icon placement, and background
3. **Falls back to hdiutil** - If `create-dmg` is not installed or fails
4. **Compresses the DMG** - Uses UDZO format for optimal compression

**DMG Creation with create-dmg (Preferred):**

If `create-dmg` is installed, the script creates a styled DMG:

```bash
create-dmg \
    --volname "SafeTool PDF" \
    --volicon "$APP_BUNDLE/Contents/Resources/SafeToolPDF.icns" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "SafeToolPDF.app" 150 190 \
    --app-drop-link 450 190 \
    "$DMG_OUTPUT" \
    "$APP_BUNDLE"
```

**create-dmg Options:**

| Option | Value | Purpose |
|--------|-------|---------|
| `--volname` | "SafeTool PDF" | Volume name shown in Finder |
| `--volicon` | SafeToolPDF.icns | Custom volume icon |
| `--window-pos` | 200 120 | Initial window position (x, y) |
| `--window-size` | 600 400 | Window dimensions (width, height) |
| `--icon-size` | 100 | Size of icons in pixels |
| `--icon` | "SafeToolPDF.app" 150 190 | Position of app icon (x, y) |
| `--app-drop-link` | 450 190 | Position of Applications symlink (x, y) |

This creates a DMG with:
- Custom window size and position
- Application icon on the left
- Applications folder symlink on the right
- Visual cue to drag the app to Applications

**DMG Creation with hdiutil (Fallback):**

If `create-dmg` is not available or fails, the script falls back to `hdiutil`:

```bash
hdiutil create \
    -volname "SafeTool PDF" \
    -srcfolder "$APP_BUNDLE" \
    -ov -format UDZO \
    "$DMG_OUTPUT"
```

**hdiutil Options:**

| Option | Value | Purpose |
|--------|-------|---------|
| `-volname` | "SafeTool PDF" | Volume name shown in Finder |
| `-srcfolder` | SafeToolPDF.app | Source directory to package |
| `-ov` | (flag) | Overwrite existing DMG |
| `-format` | UDZO | Compressed read-only format |

This creates a basic DMG without custom styling, but it's fully functional.

**Manual DMG Creation:**

If you need to create a DMG manually:

**Option 1: Using create-dmg (recommended):**

```bash
# Install create-dmg if not already installed
brew install create-dmg

# Create styled DMG
create-dmg \
    --volname "SafeTool PDF" \
    --volicon "dist/SafeToolPDF.app/Contents/Resources/SafeToolPDF.icns" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "SafeToolPDF.app" 150 190 \
    --app-drop-link 450 190 \
    "dist/SafeToolPDF.dmg" \
    "dist/SafeToolPDF.app"
```

**Option 2: Using hdiutil (fallback):**

```bash
# Create basic DMG
hdiutil create \
    -volname "SafeTool PDF" \
    -srcfolder "dist/SafeToolPDF.app" \
    -ov -format UDZO \
    "dist/SafeToolPDF.dmg"
```

**Output Location:**

```
dist/SafeToolPDF.dmg
```

**Typical Size:** ~75 MB (compressed from ~80 MB .app bundle)

**Verification:**

Check that the DMG was created:

```bash
ls -lh dist/SafeToolPDF.dmg
```

Check DMG info:

```bash
hdiutil imageinfo dist/SafeToolPDF.dmg
```

Mount the DMG:

```bash
hdiutil attach dist/SafeToolPDF.dmg
```

This will mount the DMG and open a Finder window. You should see:
- The SafeToolPDF.app bundle
- A symlink to the Applications folder (if created with create-dmg)

Unmount the DMG:

```bash
hdiutil detach "/Volumes/SafeTool PDF"
```

**Testing the DMG:**

1. **Mount the DMG:**
   ```bash
   open dist/SafeToolPDF.dmg
   ```

2. **Drag the app to Applications:**
   - In the Finder window that opens, drag SafeToolPDF.app to the Applications folder symlink
   - Or manually copy to `/Applications/`

3. **Launch the app:**
   ```bash
   open /Applications/SafeToolPDF.app
   ```

4. **Verify functionality:**
   - Application launches without errors
   - Main window displays correctly
   - Can open and process PDF files

5. **Eject the DMG:**
   - Click the eject button in Finder
   - Or: `hdiutil detach "/Volumes/SafeTool PDF"`

**DMG Distribution:**

The DMG is ready for distribution to other macOS users. They can:

1. Download the DMG file
2. Double-click to mount it
3. Drag the app to Applications
4. Launch from Applications or Spotlight

**Note:** For wide distribution, you should sign the app with a Developer ID certificate and notarize it with Apple. Ad-hoc signed apps will show a security warning on other users' machines.

**Troubleshooting DMG Creation:**

**Error: "create-dmg failed"**

The script automatically falls back to `hdiutil`. Check the output for the fallback message:
```
create-dmg failed — falling back to hdiutil
```

If you want to use `create-dmg`, install it:
```bash
brew install create-dmg
```

**Error: "hdiutil: create failed - Resource busy"**

A DMG with the same name is already mounted. Unmount it:
```bash
hdiutil detach "/Volumes/SafeTool PDF"
```

Then retry the build.

**Error: "hdiutil: create failed - File exists"**

The DMG file already exists. The script uses `-ov` to overwrite, but if you're running manually, either delete the old DMG or use the `-ov` flag:
```bash
rm dist/SafeToolPDF.dmg
# Or
hdiutil create -ov ...
```

**DMG mounts but app won't run:**

This usually means the `.app` bundle inside is invalid. Verify the bundle:
```bash
# Mount the DMG
hdiutil attach dist/SafeToolPDF.dmg

# Check the app inside
ls -la "/Volumes/SafeTool PDF/SafeToolPDF.app"
codesign -dv "/Volumes/SafeTool PDF/SafeToolPDF.app"

# Unmount
hdiutil detach "/Volumes/SafeTool PDF"
```

If the app is invalid, rebuild the `.app` bundle first (see [Section 5.4.1](#541-app-bundle)).

**"App is damaged" error on other machines:**

This is expected for ad-hoc signed apps. To distribute to other users, you need:

1. **Sign with Developer ID certificate:**
   ```bash
   codesign --force --deep --sign "Developer ID Application: Your Name" dist/SafeToolPDF.app
   ```

2. **Notarize with Apple:**
   ```bash
   xcrun notarytool submit dist/SafeToolPDF.dmg --keychain-profile "notary-profile" --wait
   ```

3. **Staple the notarization ticket:**
   ```bash
   xcrun stapler staple dist/SafeToolPDF.dmg
   ```

These steps require an Apple Developer account ($99/year) and are beyond the scope of local builds.

**Customizing DMG Appearance:**

To customize the DMG window appearance, modify the `create-dmg` options in `packaging/macos/build_macos.sh`:

- **Window size:** `--window-size 600 400` (width, height)
- **Icon positions:** `--icon "SafeToolPDF.app" 150 190` (x, y)
- **Background image:** `--background background.png` (add custom background)
- **Icon size:** `--icon-size 100` (pixels)

For more customization options, see the [create-dmg documentation](https://github.com/create-dmg/create-dmg).

---

### 5.5 Windows Packaging

Windows builds create an executable installer using Inno Setup, a free installer creation tool for Windows applications. The installer provides a professional setup wizard experience with options for desktop shortcuts, file associations, and Start Menu entries.

#### Prerequisites for Windows Packaging

Before creating Windows installers, ensure:

1. **PyInstaller has been run** - The `dist/safetool-pdf/` directory must exist
2. **Inno Setup 6 is installed** - See [Section 2.4: Windows Requirements](#24-windows-requirements)
3. **ISCC is in PATH** - The Inno Setup Compiler command-line tool

#### 5.5.1 Inno Setup Installer

Inno Setup is a free installer creation system for Windows applications. It creates a professional setup wizard that installs the application, creates shortcuts, and optionally registers file associations.

**What is Inno Setup?**

Inno Setup is a script-driven installer builder that:

- **Creates professional installers** - Standard Windows setup wizard interface
- **Supports modern Windows** - Windows 10 and 11 compatible
- **Handles installation tasks** - File copying, registry entries, shortcuts, uninstaller
- **Provides customization** - Custom icons, license display, language selection
- **Compresses efficiently** - LZMA2 compression reduces installer size
- **Is free and open source** - No licensing costs

**Requirements:**

Inno Setup 6 must be installed on your system. The build script looks for it in standard locations:

- `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`
- `C:\Program Files\Inno Setup 6\ISCC.exe`

**Installing Inno Setup:**

**Option 1: Using Chocolatey (Recommended):**

```cmd
choco install innosetup -y
```

**Option 2: Manual Installation:**

1. Download Inno Setup 6 from [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php)
2. Run the installer (`innosetup-6.x.x.exe`)
3. Follow the installation wizard
4. Verify installation:
   ```cmd
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /?
   ```

**Adding ISCC to PATH (Optional):**

To run `iscc` from any directory:

1. Open System Properties → Environment Variables
2. Edit the `Path` variable
3. Add: `C:\Program Files (x86)\Inno Setup 6\`
4. Verify: `iscc /?`

**Build Command:**

**Option 1: Using the unified build script (recommended):**

```cmd
python dev-tools\build.py
```

This automatically:
- Runs PyInstaller to create the bundle
- Downloads vendored Ghostscript (if not present)
- Compiles the Inno Setup installer (if Inno Setup is installed)

**Option 2: Using the Windows build script:**

```cmd
packaging\windows\build_windows.bat
```

This script performs three steps:
1. Runs PyInstaller
2. Verifies the PyInstaller output
3. Compiles the Inno Setup installer

**Option 3: Manual Inno Setup compilation:**

If you've already run PyInstaller and just need to rebuild the installer:

```cmd
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\windows\safetool-pdf.iss
```

Or if `iscc` is in your PATH:

```cmd
iscc packaging\windows\safetool-pdf.iss
```

**What the build_windows.bat Script Does:**

The script performs these steps:

1. **Runs PyInstaller** - Creates the bundled application in `dist/safetool-pdf/`
   ```cmd
   python -m PyInstaller --clean --noconfirm packaging\pyinstaller\safetool-pdf.spec
   ```

2. **Verifies PyInstaller output** - Checks that `dist\safetool-pdf\safetool-pdf-desktop.exe` exists

3. **Locates Inno Setup** - Searches for `ISCC.exe` in standard installation paths

4. **Compiles the installer** - Runs Inno Setup Compiler with the `.iss` script
   ```cmd
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\windows\safetool-pdf.iss
   ```

5. **Displays build summary** - Shows output locations

**The Inno Setup Script (.iss File):**

The `packaging/windows/safetool-pdf.iss` file controls the installer creation. Key sections:

**Application Metadata:**
```ini
[Setup]
AppName=SafeTool PDF
AppVersion=0.1.0
AppPublisher=SafeToolHub
AppPublisherURL=https://safetoolhub.org
DefaultDirName={autopf}\SafeTool PDF
DefaultGroupName=SafeTool PDF
```

**Files to Install:**
```ini
[Files]
; Bundle all PyInstaller output (exe + _internal/ with libs, data, and vendored GS)
Source: "..\..\dist\safetool-pdf\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
```

This installs the entire PyInstaller bundle, including:
- `safetool-pdf-desktop.exe` - Main executable
- `_internal/` - Python runtime and libraries
- `assets/` - Application assets
- `i18n/` - Translation files
- `vendor/gs/` - Vendored Ghostscript (if present)
- `LICENSE` - License file

**Shortcuts:**
```ini
[Icons]
Name: "{group}\SafeTool PDF"; Filename: "{app}\safetool-pdf-desktop.exe"
Name: "{autodesktop}\SafeTool PDF"; Filename: "{app}\safetool-pdf-desktop.exe"; Tasks: desktopicon
```

**Optional Tasks:**
```ini
[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; Flags: unchecked
Name: "fileassoc"; Description: "Associate with .pdf files"; Flags: unchecked
```

**Installer Configuration:**
- **Compression:** LZMA2 ultra64 (maximum compression)
- **Architecture:** x64 only
- **Privileges:** Admin (required for Program Files installation)
- **Minimum Windows:** Windows 10 build 17763 (October 2018 Update)
- **Languages:** English, Spanish

**Output Location:**

After successful compilation, the installer is created in:

```
dist\SafeToolPDF-{version}-windows-setup.exe
```

Example: `dist\SafeToolPDF-0.1.0-windows-setup.exe`

**Typical Size:** ~85 MB (compressed from ~90 MB PyInstaller bundle)

**Portable vs Installer:**

The build process creates two distribution options:

1. **Installer (with Inno Setup):**
   - `dist\SafeToolPDF-{version}-windows-setup.exe` - Setup wizard
   - Installs to Program Files
   - Creates Start Menu shortcuts
   - Includes uninstaller
   - Optionally creates desktop shortcut
   - Optionally registers .pdf file association

2. **Portable (without Inno Setup):**
   - `dist\safetool-pdf\` - Standalone directory
   - No installation required
   - Run `safetool-pdf-desktop.exe` directly
   - Can be copied to USB drive or network share
   - No registry entries or shortcuts

**If Inno Setup is not installed:**

The build script will detect this and display a warning:

```
WARNING: Inno Setup not found. Skipping installer creation.
Install Inno Setup 6 to build the installer.
```

The build will still succeed, and you can use the portable version in `dist\safetool-pdf\`.

**Verification:**

**Check that the installer was created:**

```cmd
dir dist\SafeToolPDF-*-windows-setup.exe
```

**Check installer size:**

```cmd
dir dist\SafeToolPDF-*-windows-setup.exe | findstr /C:".exe"
```

Expected size: ~85 MB

**Check that Inno Setup compiled successfully:**

Look for this message in the build output:

```
Successful compile (X.XX sec). Resulting Setup program filename is:
dist\SafeToolPDF-X.X.X-windows-setup.exe
```

**Testing the Installer:**

**Run the installer:**

```cmd
dist\SafeToolPDF-*-windows-setup.exe
```

Or double-click the installer in File Explorer.

**Installer Wizard Steps:**

1. **Welcome Screen** - Introduction and version information
2. **License Agreement** - GPL-3.0 license (must accept to continue)
3. **Select Destination Location** - Default: `C:\Program Files\SafeTool PDF\`
4. **Select Start Menu Folder** - Default: `SafeTool PDF`
5. **Select Additional Tasks:**
   - ☐ Create a desktop icon (unchecked by default)
   - ☐ Associate with .pdf files (unchecked by default)
6. **Ready to Install** - Summary of installation settings
7. **Installing** - Progress bar showing file extraction
8. **Completing Setup** - Option to launch the application

**Post-Installation Verification:**

After installation completes:

1. **Check installation directory:**
   ```cmd
   dir "C:\Program Files\SafeTool PDF"
   ```

2. **Check Start Menu shortcut:**
   - Open Start Menu
   - Search for "SafeTool PDF"
   - Should appear in the app list

3. **Launch the application:**
   ```cmd
   "C:\Program Files\SafeTool PDF\safetool-pdf-desktop.exe"
   ```
   Or click the Start Menu shortcut

4. **Verify functionality:**
   - Application launches without errors
   - Main window displays correctly
   - Can open and process PDF files
   - Translations work (if applicable)
   - Ghostscript integration works (if vendored)

5. **Check uninstaller:**
   - Open Settings → Apps → Installed apps
   - Find "SafeTool PDF" in the list
   - Should show version, size, and uninstall option

**Uninstalling:**

**Option 1: Windows Settings:**
1. Open Settings → Apps → Installed apps
2. Find "SafeTool PDF"
3. Click the three dots → Uninstall
4. Confirm the uninstallation

**Option 2: Start Menu:**
1. Open Start Menu
2. Find "SafeTool PDF" folder
3. Click "Uninstall SafeTool PDF"
4. Confirm the uninstallation

**Option 3: Control Panel:**
1. Open Control Panel → Programs → Programs and Features
2. Find "SafeTool PDF"
3. Right-click → Uninstall
4. Confirm the uninstallation

**Option 4: Command Line:**
```cmd
"C:\Program Files\SafeTool PDF\unins000.exe" /SILENT
```

**Verification Commands:**

**Check Inno Setup installation:**

```cmd
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /?
```

Expected output:
```
Inno Setup 6.x.x Command-Line Compiler
Copyright (C) 1997-2024 Jordan Russell. All rights reserved.
...
```

**Check PyInstaller output before building installer:**

```cmd
dir dist\safetool-pdf\safetool-pdf-desktop.exe
```

**Check vendored Ghostscript (optional):**

```cmd
dir dist\safetool-pdf\vendor\gs\bin\gswin64c.exe
```

**Test portable version before building installer:**

```cmd
dist\safetool-pdf\safetool-pdf-desktop.exe
```

**Troubleshooting Inno Setup Installer:**

**Error: "Inno Setup not found"**

Install Inno Setup 6:
```cmd
choco install innosetup -y
```

Or download manually from [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php)

**Error: "PyInstaller dist not found"**

Run PyInstaller first:
```cmd
python -m PyInstaller packaging\pyinstaller\safetool-pdf.spec
```

Verify the output:
```cmd
dir dist\safetool-pdf\safetool-pdf-desktop.exe
```

**Error: "ISCC.exe failed with exit code 1"**

Check the Inno Setup compilation output for specific errors. Common issues:

- **Missing source files:** Ensure `dist\safetool-pdf\` exists and contains all files
- **Invalid .iss syntax:** Check `packaging\windows\safetool-pdf.iss` for syntax errors
- **Missing icon file:** Ensure `assets\icon.ico` exists

Run ISCC manually to see detailed error messages:
```cmd
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\windows\safetool-pdf.iss
```

**Error: "Access denied" during installation**

The installer requires administrator privileges. Right-click the installer and select "Run as administrator".

**Error: "Installer is damaged or corrupted"**

The installer file may be incomplete or corrupted. Rebuild it:
```cmd
del dist\SafeToolPDF-*-windows-setup.exe
python dev-tools\build.py
```

**Installer runs but app won't launch:**

This usually means the PyInstaller bundle is invalid. Test the portable version first:
```cmd
dist\safetool-pdf\safetool-pdf-desktop.exe
```

If the portable version doesn't work, the issue is with PyInstaller, not Inno Setup. See [Section 8.1: Common Build Errors](#81-common-build-errors) for PyInstaller troubleshooting.

**"Windows protected your PC" SmartScreen warning:**

This is expected for unsigned installers. Users can click "More info" → "Run anyway" to proceed.

To avoid this warning, you need to:
1. **Sign the installer** with a code signing certificate
2. **Build reputation** with Microsoft SmartScreen (requires many downloads)

Code signing certificates cost $100-$400/year and are beyond the scope of local builds.

**Customizing the Installer:**

To customize the installer, edit `packaging/windows/safetool-pdf.iss`:

**Change default installation directory:**
```ini
[Setup]
DefaultDirName={autopf}\MyCustomFolder
```

**Change Start Menu folder name:**
```ini
[Setup]
DefaultGroupName=My Custom Name
```

**Enable desktop icon by default:**
```ini
[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; Flags: checked
```

**Add custom installer images:**
```ini
[Setup]
WizardImageFile=path\to\wizard-image.bmp
WizardSmallImageFile=path\to\wizard-small-image.bmp
```

**Change compression level:**
```ini
[Setup]
Compression=lzma2/fast    ; Faster compilation, larger installer
Compression=lzma2/ultra64 ; Slower compilation, smaller installer (default)
```

**Add additional languages:**
```ini
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
```

For more customization options, see the [Inno Setup documentation](https://jrsoftware.org/ishelp/).

**Environment Variables:**

The Inno Setup script uses environment variables for versioning:

| Variable | Purpose | Example | Default |
|----------|---------|---------|---------|
| `APP_VERSION` | Application version | `0.1.0` | Auto-detected from `config.py` |
| `APP_FULL_VERSION` | Full version string | `0.1.0-beta` | Same as `APP_VERSION` |

Set these before building:

```cmd
set APP_VERSION=1.2.0
set APP_FULL_VERSION=1.2.0-beta
python dev-tools\build.py
```

This creates: `dist\SafeToolPDF-1.2.0-beta-windows-setup.exe`

**Installer Distribution:**

The installer is ready for distribution to Windows users. They can:

1. Download the `.exe` installer
2. Run the installer (may need to click "More info" → "Run anyway" for unsigned installers)
3. Follow the setup wizard
4. Launch from Start Menu or Desktop shortcut

**Note:** For professional distribution, consider:
- **Code signing** - Sign the installer with a certificate to avoid SmartScreen warnings
- **Virus scanning** - Scan the installer with multiple antivirus tools before distribution
- **Testing** - Test on clean Windows 10 and Windows 11 installations
- **Documentation** - Provide installation instructions for end users

---

## 6. Ghostscript Integration

Ghostscript is an optional dependency that enables advanced PDF processing features in SafeTool PDF, including lossy compression, font subsetting, and full PDF rewriting. This section explains how Ghostscript is integrated into the build process and how to verify its inclusion in the final binaries.

### 6.1 Vendored vs System Ghostscript

SafeTool PDF uses different Ghostscript integration strategies depending on the platform:

#### Platform-Specific Behavior

| Platform | Ghostscript Source | Integration Method | User Installation Required |
|----------|-------------------|-------------------|---------------------------|
| **Windows** | Vendored (bundled) | Downloaded and included in binary | No - bundled with app |
| **macOS** | Vendored (bundled) | Downloaded and included in .app | No - bundled with app |
| **Linux** | System installation | Uses system-installed Ghostscript | Yes - via package manager |

#### Why Different Approaches?

**Windows and macOS - Vendored Ghostscript:**

On Windows and macOS, Ghostscript is downloaded and bundled with the application during the build process. This approach:

- **Simplifies user experience** - Users don't need to install Ghostscript separately
- **Ensures version compatibility** - The application is tested with a specific Ghostscript version
- **Provides consistent behavior** - All users have the same Ghostscript version
- **Reduces support burden** - No need to troubleshoot user-installed Ghostscript issues

The vendored Ghostscript binary is placed in `packaging/vendor/gs/bin/` and included by PyInstaller in the `vendor/gs/` directory of the final bundle.

**Linux - System Ghostscript:**

On Linux, the application uses the system-installed Ghostscript (if available). This approach:

- **Follows Linux conventions** - System packages are preferred over bundled libraries
- **Reduces binary size** - No need to bundle Ghostscript in .deb, .rpm, or AppImage
- **Leverages system updates** - Users benefit from security updates via package manager
- **Respects user choice** - Users can install their preferred Ghostscript version

The application detects Ghostscript using the standard `gs` command in the system PATH.

#### Ghostscript Detection Order

The application searches for Ghostscript in this order:

1. **Bundled Ghostscript** - `<app_dir>/vendor/gs/bin/gswin64c.exe` (Windows) or `<app_dir>/vendor/gs/bin/gs` (macOS)
2. **System Ghostscript** - `gs` or `gswin64c.exe` in system PATH

If Ghostscript is not found, the application still works but advanced PDF processing features are disabled.

#### Minimum Ghostscript Version

SafeTool PDF requires **Ghostscript 9.50 or higher**. The application verifies the version by running:

```bash
gs --version
```

If the installed version is too old, the application will not use it and will display a warning.

---

### 6.2 Downloading Vendored Ghostscript

The build process can automatically download Ghostscript for Windows and macOS builds. This section explains how to manually download Ghostscript or verify that it was downloaded correctly.

#### Automatic Download (Recommended)

The unified build script (`dev-tools/build.py`) automatically attempts to download Ghostscript before running PyInstaller:

```bash
# Windows/macOS - Ghostscript is downloaded automatically
python dev-tools/build.py
```

The script executes:

```bash
python packaging/scripts/download_ghostscript.py
```

**What the Download Script Does:**

1. **Checks platform** - Only downloads for Windows x64 (macOS support planned)
2. **Downloads Ghostscript installer** - From official GitHub releases (version 10.06.0)
3. **Extracts the binary** - Uses 7-Zip if available, otherwise copies the installer
4. **Places in vendor directory** - `packaging/vendor/gs/bin/gswin64c.exe`
5. **Verifies installation** - Checks that the binary exists

**Download URL:**

The script downloads from the official Ghostscript GitHub releases:

```
https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10060/gs10060w64.exe
```

**Output Location:**

```
packaging/vendor/gs/bin/gswin64c.exe
```

This location is recognized by PyInstaller and included in the final bundle.

#### Manual Download

If the automatic download fails or you want to use a specific Ghostscript version, you can download it manually:

**Windows:**

```cmd
REM Run the download script manually
python packaging\scripts\download_ghostscript.py
```

Or download manually:

1. Download Ghostscript from [ghostscript.com](https://www.ghostscript.com/releases/gsdnld.html)
2. Extract `gswin64c.exe` from the installer (using 7-Zip or similar)
3. Place it in `packaging\vendor\gs\bin\gswin64c.exe`

**macOS:**

```bash
# Run the download script manually
python packaging/scripts/download_ghostscript.py
```

**Note:** The current download script only supports Windows. For macOS, you can install Ghostscript via Homebrew and it will be detected by the application:

```bash
brew install ghostscript
```

**Linux:**

Ghostscript download is not supported on Linux. Install via your package manager:

```bash
# Ubuntu/Debian
sudo apt install ghostscript

# Fedora/RHEL
sudo dnf install ghostscript

# Arch Linux
sudo pacman -S ghostscript
```

#### Continue-on-Error Behavior

The Ghostscript download step uses **continue-on-error** behavior, meaning:

- **If download succeeds** - Ghostscript is bundled with the application
- **If download fails** - The build continues without Ghostscript
- **No build failure** - The application still builds successfully

This design ensures that:

- Builds don't fail due to network issues or download problems
- The application remains functional without Ghostscript (with reduced features)
- Users can still install Ghostscript manually after installation

**When Download Fails:**

If the download fails, you'll see a message like:

```
Platform: windows 64-bit
Ghostscript download is only supported for Windows x64.
[WARNING] Binary not found - check the output above for errors.
```

Or:

```
[WARNING] Could not download Ghostscript. Build will continue without it.
```

The build will proceed, and the final binary will not include Ghostscript. Users can install it separately if needed.

#### Verifying Download Success

After running the download script, verify that Ghostscript was downloaded:

**Windows:**

```cmd
dir packaging\vendor\gs\bin\gswin64c.exe
```

Expected output:
```
 Directory of packaging\vendor\gs\bin

gswin64c.exe
```

**Check file size:**

```cmd
dir packaging\vendor\gs\bin\gswin64c.exe | findstr /C:".exe"
```

Expected size: ~15-20 MB

**Test the binary:**

```cmd
packaging\vendor\gs\bin\gswin64c.exe --version
```

Expected output:
```
10.06.0
```

**macOS:**

```bash
ls -lh packaging/vendor/gs/bin/gs
```

Or check system installation:

```bash
gs --version
```

**Linux:**

```bash
gs --version
```

Expected output:
```
GPL Ghostscript 9.55.0 (2021-09-27)
```

Or similar version 9.50+.

---

### 6.3 Verification

After building the application, you should verify that Ghostscript is correctly included in the final binary (Windows/macOS) or available on the system (Linux).

#### Verifying Ghostscript in PyInstaller Bundle

**Windows:**

Check that Ghostscript is in the PyInstaller output:

```cmd
dir dist\safetool-pdf\vendor\gs\bin\gswin64c.exe
```

Expected output:
```
 Directory of dist\safetool-pdf\vendor\gs\bin

gswin64c.exe
```

**macOS:**

Check that Ghostscript is in the .app bundle:

```bash
ls -lh dist/SafeToolPDF.app/Contents/Resources/vendor/gs/bin/gs
```

Or in the non-bundle output:

```bash
ls -lh dist/SafeToolPDF/vendor/gs/bin/gs
```

**Linux:**

Linux builds don't bundle Ghostscript. Verify system installation:

```bash
which gs
gs --version
```

#### Verifying Ghostscript in Final Packages

**Windows Installer:**

After installing the application, check that Ghostscript is included:

```cmd
dir "C:\Program Files\SafeTool PDF\vendor\gs\bin\gswin64c.exe"
```

**macOS DMG:**

Mount the DMG and check the .app bundle:

```bash
open dist/SafeToolPDF.dmg
ls -lh /Volumes/SafeToolPDF/SafeToolPDF.app/Contents/Resources/vendor/gs/bin/gs
```

**Linux Packages (.deb, .rpm, AppImage):**

Linux packages don't include Ghostscript. Verify system installation:

```bash
gs --version
```

#### Testing Ghostscript Integration in the Application

The most reliable way to verify Ghostscript integration is to run the application and test PDF processing features:

**Launch the application:**

```bash
# Windows
dist\safetool-pdf\safetool-pdf-desktop.exe

# macOS
open dist/SafeToolPDF.app

# Linux
./dist/safetool-pdf/safetool-pdf-desktop
```

**Check Ghostscript status:**

1. Open the application
2. Go to Settings or Preferences (if available)
3. Look for Ghostscript status indicator

Or check the application logs:

**Windows:**
```cmd
type "%APPDATA%\SafeToolPDF\logs\app.log" | findstr /C:"Ghostscript"
```

**macOS/Linux:**
```bash
grep "Ghostscript" ~/Library/Application\ Support/SafeToolPDF/logs/app.log  # macOS
grep "Ghostscript" ~/.local/share/SafeToolPDF/logs/app.log                  # Linux
```

Expected log messages:

```
INFO: Using bundled Ghostscript: C:\Program Files\SafeTool PDF\vendor\gs\bin\gswin64c.exe
```

Or:

```
INFO: Using system Ghostscript: /usr/bin/gs
```

Or if not found:

```
INFO: Ghostscript not found.
```

**Test PDF processing:**

1. Open a PDF file in the application
2. Select an optimization preset that uses Ghostscript (e.g., "Lossy Compression")
3. Process the PDF
4. Verify that the operation completes successfully

If Ghostscript is not available, the application will display a warning:

```
Warning: Ghostscript not found. Some optimization features are unavailable.
```

#### Diagnostic Commands

**Check if Ghostscript is in the bundle:**

**Windows:**
```cmd
REM Check PyInstaller output
dir dist\safetool-pdf\vendor\gs\bin\gswin64c.exe

REM Check installed application
dir "C:\Program Files\SafeTool PDF\vendor\gs\bin\gswin64c.exe"

REM Test the bundled binary
dist\safetool-pdf\vendor\gs\bin\gswin64c.exe --version
```

**macOS:**
```bash
# Check PyInstaller output
ls -lh dist/SafeToolPDF.app/Contents/Resources/vendor/gs/bin/gs

# Test the bundled binary
dist/SafeToolPDF.app/Contents/Resources/vendor/gs/bin/gs --version
```

**Linux:**
```bash
# Check system installation
which gs
gs --version

# Check if version meets minimum requirement (9.50+)
gs --version | grep -E "^[0-9]+\.[0-9]+"
```

**Check Ghostscript version:**

```bash
# Windows (bundled)
dist\safetool-pdf\vendor\gs\bin\gswin64c.exe --version

# macOS (bundled)
dist/SafeToolPDF.app/Contents/Resources/vendor/gs/bin/gs --version

# Linux (system)
gs --version
```

Expected output: `10.06.0` (or higher)

**Verify minimum version requirement:**

SafeTool PDF requires Ghostscript 9.50 or higher. Check that your version meets this requirement:

```bash
# Extract version number
gs --version | head -n 1
```

If the version is below 9.50, the application will not use it.

#### Troubleshooting Ghostscript Integration

**Issue: Ghostscript not found in bundle**

**Symptom:** `vendor/gs/bin/` directory is missing or empty in the PyInstaller output

**Cause:** Ghostscript was not downloaded before PyInstaller ran

**Solution:**

1. Download Ghostscript manually:
   ```cmd
   python packaging\scripts\download_ghostscript.py
   ```

2. Verify the download:
   ```cmd
   dir packaging\vendor\gs\bin\gswin64c.exe
   ```

3. Re-run PyInstaller:
   ```cmd
   python -m PyInstaller packaging\pyinstaller\safetool-pdf.spec
   ```

4. Verify inclusion:
   ```cmd
   dir dist\safetool-pdf\vendor\gs\bin\gswin64c.exe
   ```

**Issue: Ghostscript version too old**

**Symptom:** Application logs show "System GS found but version too old"

**Cause:** System-installed Ghostscript is below version 9.50

**Solution:**

**Linux:**
```bash
# Ubuntu/Debian - upgrade Ghostscript
sudo apt update
sudo apt install --only-upgrade ghostscript

# Fedora/RHEL
sudo dnf update ghostscript

# Arch Linux
sudo pacman -Syu ghostscript
```

**macOS:**
```bash
# Upgrade via Homebrew
brew upgrade ghostscript
```

**Windows:**

Download and install the latest version from [ghostscript.com](https://www.ghostscript.com/releases/gsdnld.html)

**Issue: Download script fails**

**Symptom:** `download_ghostscript.py` exits with an error

**Common causes and solutions:**

1. **Network connectivity issues:**
   - Check internet connection
   - Try downloading manually from [GitHub releases](https://github.com/ArtifexSoftware/ghostpdl-downloads/releases)

2. **7-Zip not found (Windows):**
   - Install 7-Zip: `choco install 7zip`
   - Or extract the installer manually and place `gswin64c.exe` in `packaging\vendor\gs\bin\`

3. **Platform not supported:**
   - The script only supports Windows x64
   - On Linux/macOS, install via package manager instead

**Issue: Ghostscript works in development but not in built binary**

**Symptom:** Ghostscript is detected when running from source but not in the PyInstaller bundle

**Cause:** PyInstaller didn't include the vendored Ghostscript

**Solution:**

1. Verify the .spec file includes the vendor directory:
   ```python
   # In packaging/pyinstaller/safetool-pdf.spec
   datas=[
       ('vendor', 'vendor'),  # Ensure this line exists
   ]
   ```

2. Check that Ghostscript is in the source location:
   ```cmd
   dir packaging\vendor\gs\bin\gswin64c.exe
   ```

3. Re-run PyInstaller with the `--clean` flag:
   ```cmd
   python -m PyInstaller --clean packaging\pyinstaller\safetool-pdf.spec
   ```

4. Verify inclusion in output:
   ```cmd
   dir dist\safetool-pdf\vendor\gs\bin\gswin64c.exe
   ```

**Issue: Application can't execute Ghostscript**

**Symptom:** Ghostscript binary exists but application can't run it

**Cause:** Permissions issue or missing dependencies

**Solution:**

**Linux/macOS:**
```bash
# Make the binary executable
chmod +x dist/safetool-pdf/vendor/gs/bin/gs

# Check for missing shared libraries
ldd dist/safetool-pdf/vendor/gs/bin/gs
```

**Windows:**
```cmd
REM Check if the binary is blocked
REM Right-click gswin64c.exe → Properties → Unblock

REM Test execution directly
dist\safetool-pdf\vendor\gs\bin\gswin64c.exe --version
```

**For more troubleshooting, see [Section 8: Troubleshooting](#8-troubleshooting).**

---

## 7. Verification and Testing

This section provides comprehensive verification and testing procedures to ensure your SafeTool PDF build is correct and functional. Following these steps helps you catch issues early and confirm that all features work as expected before distribution.

### 7.1 Pre-Build Verification

Before starting the build process, verify that all required dependencies and tools are properly installed. This pre-flight check helps prevent build failures and saves time by catching missing dependencies early.

#### Check Python Version

Verify Python 3.12 or higher is installed:

```bash
python --version
# Expected output: Python 3.12.x or higher
```

**Windows users:** You may need to use `python3` or `py -3.12`:

```cmd
python --version
py -3.12 --version
```

#### Check pip Installation

```bash
pip --version
# Expected output: pip 23.x or higher from python 3.12
```

#### Check PyInstaller

```bash
python -m PyInstaller --version
# Expected output: 6.0 or higher
```

If PyInstaller is not installed:

```bash
pip install pyinstaller>=6.0
```

#### Check Platform-Specific Build Tools

**Linux:**

```bash
# Check dpkg-deb (for .deb packages)
dpkg-deb --version
# Expected output: Debian 'dpkg-deb' package management program version x.x.x

# Check rpm (for .rpm packages)
rpm --version
# Expected output: RPM version x.x.x

# Check fuse (for AppImage)
fusermount --version
# Expected output: fusermount version x.x.x
```

**macOS:**

```bash
# Check create-dmg
create-dmg --version
# Expected output: create-dmg x.x.x

# Check codesign (Xcode Command Line Tools)
codesign --version
# Expected output: codesign-xxx

# Check hdiutil (pre-installed)
hdiutil --version
# Expected output: hdiutil x.x.x
```

**Windows:**

```cmd
REM Check Inno Setup Compiler
iscc /?
REM Expected output: Inno Setup Preprocessor x.x.x

REM If not found, Inno Setup is not installed or not in PATH
```

#### Check Python Dependencies

Verify all required Python packages are installed:

```bash
# Check all dependencies at once
pip list | grep -E "(pikepdf|PyMuPDF|PySide6|Pillow|qtawesome|pyinstaller)"

# Or check individually
python -c "import pikepdf; print(f'pikepdf {pikepdf.__version__}')"
python -c "import fitz; print(f'PyMuPDF {fitz.__version__}')"
python -c "import PySide6; print(f'PySide6 {PySide6.__version__}')"
python -c "import PIL; print(f'Pillow {PIL.__version__}')"
python -c "import qtawesome; print(f'qtawesome {qtawesome.__version__}')"
```

**Windows users:** Use `findstr` instead of `grep`:

```cmd
pip list | findstr /C:"pikepdf" /C:"PyMuPDF" /C:"PySide6" /C:"Pillow" /C:"qtawesome" /C:"pyinstaller"
```

If any packages are missing, install them:

```bash
pip install -r requirements.txt
```

#### Check Ghostscript (Optional)

If you want to include Ghostscript for advanced PDF features:

**Linux:**
```bash
gs --version
# Expected output: GPL Ghostscript 9.50 or higher
```

**macOS:**
```bash
gs --version
# Expected output: GPL Ghostscript 9.50 or higher
```

**Windows (vendored):**
```cmd
dir packaging\vendor\gs\bin\gswin64c.exe
REM If not found, run: python packaging\scripts\download_ghostscript.py
```

#### Verify Project Structure

Ensure you're in the correct directory and all required files exist:

```bash
# Check you're in the project root
ls -la | grep -E "(safetool_pdf_desktop|packaging|dev-tools|requirements.txt)"

# Verify key files exist
ls packaging/pyinstaller/safetool-pdf.spec
ls dev-tools/build.py
ls requirements.txt
ls safetool_pdf_desktop/app.py
```

**Windows:**
```cmd
dir packaging\pyinstaller\safetool-pdf.spec
dir dev-tools\build.py
dir requirements.txt
dir safetool_pdf_desktop\app.py
```

#### Pre-Build Checklist

Before running the build, confirm:

- [ ] Python 3.12+ is installed and in PATH
- [ ] PyInstaller 6.0+ is installed
- [ ] All Python dependencies from requirements.txt are installed
- [ ] Platform-specific build tools are installed (dpkg-deb, rpm, create-dmg, or Inno Setup)
- [ ] You're in the project root directory
- [ ] The `packaging/pyinstaller/safetool-pdf.spec` file exists
- [ ] (Optional) Ghostscript is installed or downloaded for vendoring

If all checks pass, you're ready to build!

---

### 7.2 Post-Build Verification

After the build completes, verify that all artifacts were created successfully and are functional. These checks help ensure the build process completed correctly and the binaries are ready for distribution or testing.

#### Verify PyInstaller Output

Check that PyInstaller created the bundled executable directory:

**Linux/Windows:**
```bash
# Check the directory exists
ls -la dist/safetool-pdf/

# Check the main executable exists
ls -lh dist/safetool-pdf/safetool-pdf-desktop*

# Check directory size (should be 50-100 MB)
du -sh dist/safetool-pdf/
```

**macOS:**
```bash
# Check the directory exists
ls -la dist/SafeToolPDF/

# Check the main executable exists
ls -lh dist/SafeToolPDF/SafeToolPDF*

# Check directory size (should be 50-100 MB)
du -sh dist/SafeToolPDF/
```

**Windows:**
```cmd
REM Check the directory exists
dir dist\safetool-pdf\

REM Check the main executable exists
dir dist\safetool-pdf\safetool-pdf-desktop.exe

REM Check directory size
dir dist\safetool-pdf\ | findstr /C:"bytes"
```

#### Verify Platform-Specific Artifacts

**Linux:**

Check that all package formats were created:

```bash
# List all artifacts
ls -lh dist/SafeToolPDF-*

# Check .deb package
ls -lh dist/SafeToolPDF-*-linux-amd64.deb
# Expected size: ~75 MB

# Check .rpm package
ls -lh dist/SafeToolPDF-*-linux-x86_64.rpm
# Expected size: ~75 MB

# Check AppImage
ls -lh dist/SafeToolPDF-x86_64.AppImage
# Expected size: ~80 MB

# Verify .deb package contents
dpkg-deb --info dist/SafeToolPDF-*-linux-amd64.deb
dpkg-deb --contents dist/SafeToolPDF-*-linux-amd64.deb | head -20

# Verify .rpm package contents
rpm -qpi dist/SafeToolPDF-*-linux-x86_64.rpm
rpm -qpl dist/SafeToolPDF-*-linux-x86_64.rpm | head -20

# Verify AppImage is executable
file dist/SafeToolPDF-x86_64.AppImage
# Expected output: ELF 64-bit LSB executable
```

**macOS:**

Check that the .app bundle and DMG were created:

```bash
# Check .app bundle
ls -lh dist/SafeToolPDF.app
du -sh dist/SafeToolPDF.app
# Expected size: ~80 MB

# Check DMG
ls -lh dist/SafeToolPDF.dmg
# Expected size: ~80 MB

# Verify .app bundle structure
ls -la dist/SafeToolPDF.app/Contents/
ls -la dist/SafeToolPDF.app/Contents/MacOS/
ls -la dist/SafeToolPDF.app/Contents/Resources/

# Verify code signature
codesign -dv dist/SafeToolPDF.app
# Expected output: Signature=adhoc (for local builds)

# Mount and inspect DMG
hdiutil attach dist/SafeToolPDF.dmg
ls -la /Volumes/SafeToolPDF/
hdiutil detach /Volumes/SafeToolPDF
```

**Windows:**

Check that the installer was created:

```cmd
REM Check installer exists
dir dist\SafeToolPDF-*-setup-x64.exe
REM Expected size: ~85 MB

REM If Inno Setup was not available, check portable version
dir dist\safetool-pdf\safetool-pdf-desktop.exe

REM Check file properties (right-click → Properties in Explorer)
REM Or use PowerShell:
powershell -Command "Get-Item dist\SafeToolPDF-*-setup-x64.exe | Select-Object Name, Length, LastWriteTime"
```

#### Verify Executable Permissions

**Linux/macOS:**

Ensure the main executable has execute permissions:

```bash
# Check permissions
ls -l dist/safetool-pdf/safetool-pdf-desktop          # Linux
ls -l dist/SafeToolPDF/SafeToolPDF                    # macOS
ls -l dist/SafeToolPDF-x86_64.AppImage                # Linux AppImage

# If not executable, add permissions
chmod +x dist/safetool-pdf/safetool-pdf-desktop       # Linux
chmod +x dist/SafeToolPDF/SafeToolPDF                 # macOS
chmod +x dist/SafeToolPDF-x86_64.AppImage             # Linux AppImage
```

#### Test PyInstaller Executable Directly

Before testing the packaged versions, verify the PyInstaller output works:

**Linux:**
```bash
./dist/safetool-pdf/safetool-pdf-desktop
```

**macOS:**
```bash
./dist/SafeToolPDF/SafeToolPDF
# Or open the .app bundle
open dist/SafeToolPDF.app
```

**Windows:**
```cmd
dist\safetool-pdf\safetool-pdf-desktop.exe
```

**Expected behavior:**
- Application window opens without errors
- No missing module errors in the console
- UI renders correctly
- Application is responsive

If the application doesn't launch, check the console output for error messages and refer to [Section 8: Troubleshooting](#8-troubleshooting).

#### Verify Ghostscript Inclusion

If you downloaded vendored Ghostscript, verify it's included in the bundle:

**Windows:**
```cmd
REM Check in PyInstaller output
dir dist\safetool-pdf\vendor\gs\bin\gswin64c.exe

REM Test the bundled Ghostscript
dist\safetool-pdf\vendor\gs\bin\gswin64c.exe --version
REM Expected output: 10.06.0 or higher
```

**macOS:**
```bash
# Check in .app bundle
ls -lh dist/SafeToolPDF.app/Contents/Resources/vendor/gs/bin/gs

# Test the bundled Ghostscript
dist/SafeToolPDF.app/Contents/Resources/vendor/gs/bin/gs --version
# Expected output: 10.06.0 or higher
```

**Linux:**
```bash
# Linux uses system Ghostscript, not bundled
which gs
gs --version
# Expected output: GPL Ghostscript 9.50 or higher
```

#### Verify Translations Inclusion

Check that translation files are included in the bundle:

**All Platforms:**

```bash
# Linux
ls -la dist/safetool-pdf/i18n/
# Expected files: es.json, fr.json, de.json, etc.

# macOS
ls -la dist/SafeToolPDF.app/Contents/Resources/i18n/
# Or: ls -la dist/SafeToolPDF/i18n/

# Windows
dir dist\safetool-pdf\i18n\
# Expected files: es.json, fr.json, de.json, etc.
```

Verify translation files are not empty:

```bash
# Linux/macOS
cat dist/safetool-pdf/i18n/es.json | head -10

# Windows
type dist\safetool-pdf\i18n\es.json
```

Expected content: JSON object with translation keys and values.

#### Verify Assets (Icons) Inclusion

Check that application assets (icons, images) are included:

**All Platforms:**

```bash
# Linux
ls -la dist/safetool-pdf/assets/
# Expected files: icon.png, logo.png, etc.

# macOS
ls -la dist/SafeToolPDF.app/Contents/Resources/assets/
# Or: ls -la dist/SafeToolPDF/assets/

# Windows
dir dist\safetool-pdf\assets\
# Expected files: icon.png, logo.png, etc.
```

Verify icon files exist and have reasonable sizes:

```bash
# Linux/macOS
ls -lh dist/safetool-pdf/assets/icon.png
# Expected size: 10-100 KB

# Windows
dir dist\safetool-pdf\assets\icon.png
```

#### Post-Build Checklist

After the build completes, confirm:

- [ ] PyInstaller output directory exists in `dist/`
- [ ] Main executable exists and has correct permissions
- [ ] Platform-specific packages were created (.deb, .rpm, AppImage, DMG, or .exe installer)
- [ ] Package file sizes are reasonable (50-100 MB)
- [ ] PyInstaller executable launches successfully
- [ ] Ghostscript is included (Windows/macOS) or available on system (Linux)
- [ ] Translation files (i18n/*.json) are present
- [ ] Asset files (assets/*.png) are present
- [ ] No error messages during build process

If all checks pass, proceed to functional testing!

---

### 7.3 Functional Testing Checklist

After verifying that the build artifacts exist and are structurally correct, perform functional testing to ensure the application works as expected. This checklist covers the most important features and helps catch runtime issues before distribution.

#### Basic Launch and UI Testing

**Test 1: Application Launch**

- [ ] Application launches without errors
- [ ] Main window appears within 5 seconds
- [ ] No error dialogs or crash messages
- [ ] Application icon displays correctly in taskbar/dock
- [ ] Window title shows "SafeTool PDF" or similar

**How to test:**

```bash
# Linux - AppImage
./dist/SafeToolPDF-x86_64.AppImage

# Linux - Installed .deb
safetool-pdf-desktop

# macOS - .app bundle
open dist/SafeToolPDF.app

# Windows - Portable
dist\safetool-pdf\safetool-pdf-desktop.exe

# Windows - Installed
"C:\Program Files\SafeTool PDF\safetool-pdf-desktop.exe"
```

**Test 2: UI Rendering**

- [ ] All UI elements render correctly (buttons, menus, text)
- [ ] Icons display properly (not missing or broken)
- [ ] Text is readable and properly aligned
- [ ] Window is resizable (if applicable)
- [ ] Menus open and close correctly
- [ ] Tooltips appear on hover (if applicable)

**Test 3: Language/Translation**

- [ ] Application displays in the correct language (default or system language)
- [ ] UI text is translated (not showing translation keys like "app.title")
- [ ] Language can be changed in settings (if feature exists)
- [ ] All UI elements update when language changes

**How to test:**

1. Launch the application
2. Check that UI text is in the expected language
3. Go to Settings → Language (if available)
4. Change to a different language (e.g., Spanish, French)
5. Verify that all UI elements update correctly

#### Core Functionality Testing

**Test 4: Open PDF File**

- [ ] File → Open menu works
- [ ] File dialog appears
- [ ] Can browse and select a PDF file
- [ ] PDF loads successfully
- [ ] PDF content displays correctly (if preview feature exists)
- [ ] File name appears in the UI

**How to test:**

1. Launch the application
2. Click File → Open (or equivalent)
3. Select a test PDF file
4. Verify the file loads without errors
5. Check that the file name is displayed

**Test 5: PDF Optimization**

- [ ] Can select an optimization preset or options
- [ ] Optimization process starts when triggered
- [ ] Progress indicator appears (if applicable)
- [ ] Optimization completes successfully
- [ ] Output file is created
- [ ] Output file is smaller than input (for compression presets)
- [ ] Output file is a valid PDF (can be opened)

**How to test:**

1. Open a test PDF file
2. Select an optimization preset (e.g., "Standard Compression")
3. Click "Optimize" or equivalent button
4. Wait for the process to complete
5. Verify the output file exists
6. Open the output file in a PDF viewer to verify it's valid
7. Compare file sizes: `ls -lh input.pdf output.pdf`

**Test 6: Multiple PDF Operations**

- [ ] Can process multiple PDFs in sequence
- [ ] Application remains stable after multiple operations
- [ ] No memory leaks (application doesn't slow down)
- [ ] Can open different PDFs without restarting

**How to test:**

1. Process 3-5 different PDF files in sequence
2. Verify each operation completes successfully
3. Check that the application remains responsive
4. Monitor memory usage (Task Manager / Activity Monitor / htop)

#### Ghostscript Integration Testing

**Test 7: Ghostscript Detection**

- [ ] Application detects Ghostscript (bundled or system)
- [ ] Ghostscript version is displayed in About or Settings (if applicable)
- [ ] No "Ghostscript not found" warnings (if Ghostscript is included)

**How to test:**

1. Launch the application
2. Go to Help → About or Settings → Advanced
3. Look for Ghostscript status or version information
4. Verify it shows the correct version (10.06.0 for bundled, or system version)

**Test 8: Ghostscript-Dependent Features**

- [ ] Lossy compression preset works (if available)
- [ ] Advanced PDF rewriting works (if available)
- [ ] Font subsetting works (if available)
- [ ] No errors when using Ghostscript features

**How to test:**

1. Open a test PDF file
2. Select a preset that uses Ghostscript (e.g., "Lossy Compression" or "Maximum Compression")
3. Process the PDF
4. Verify the operation completes without errors
5. Check that the output file is significantly smaller than the input
6. Open the output file to verify it's valid

**Test 9: Ghostscript Fallback (Linux)**

On Linux, test that the application works with system Ghostscript:

- [ ] Application detects system Ghostscript
- [ ] Ghostscript features work with system installation
- [ ] Correct version is used (9.50+)

**How to test:**

```bash
# Check system Ghostscript
gs --version

# Launch application and verify detection
./dist/SafeToolPDF-x86_64.AppImage

# Check application logs
grep "Ghostscript" ~/.local/share/SafeToolPDF/logs/app.log
```

#### Platform-Specific Testing

**Test 10: Installation (Package Formats)**

**Linux (.deb):**

```bash
# Install the package
sudo dpkg -i dist/SafeToolPDF-*-linux-amd64.deb

# Verify installation
which safetool-pdf-desktop
dpkg -l | grep safetool

# Launch from command line
safetool-pdf-desktop

# Launch from application menu
# Check Applications → Graphics → SafeTool PDF

# Uninstall
sudo dpkg -r safetool-pdf
```

**Linux (.rpm):**

```bash
# Install the package
sudo rpm -i dist/SafeToolPDF-*-linux-x86_64.rpm

# Verify installation
which safetool-pdf-desktop
rpm -qa | grep SafeTool

# Launch from command line
safetool-pdf-desktop

# Uninstall
sudo rpm -e SafeToolPDF
```

**macOS (DMG):**

```bash
# Mount the DMG
open dist/SafeToolPDF.dmg

# Drag SafeToolPDF.app to Applications folder
# Launch from Applications folder or Spotlight

# Verify no security warnings appear
# If "App is damaged" error appears, see Section 8.2

# Eject DMG
hdiutil detach /Volumes/SafeToolPDF
```

**Windows (Installer):**

```cmd
REM Run the installer
dist\SafeToolPDF-*-setup-x64.exe

REM Follow installation wizard
REM Verify installation completes successfully

REM Launch from Start Menu
REM Search for "SafeTool PDF"

REM Or launch from installation directory
"C:\Program Files\SafeTool PDF\safetool-pdf-desktop.exe"

REM Uninstall via Control Panel → Programs and Features
```

#### Clean System Testing

To ensure the application works on user systems without development dependencies, test on a clean system:

**Test 11: Clean System Installation**

**Linux - Using Docker:**

```bash
# Create a clean Ubuntu container
docker run -it --rm -v $(pwd)/dist:/dist ubuntu:22.04 bash

# Inside container:
apt update
apt install -y fuse libfuse2

# Test AppImage
cd /dist
chmod +x SafeToolPDF-x86_64.AppImage
./SafeToolPDF-x86_64.AppImage

# Or test .deb package
apt install -y ./SafeToolPDF-*-linux-amd64.deb
safetool-pdf-desktop
```

**macOS - Using a Clean User Account:**

1. Create a new user account (System Preferences → Users & Groups)
2. Log in as the new user
3. Copy the DMG to the new user's Downloads folder
4. Install and test the application
5. Verify no errors related to missing dependencies

**Windows - Using a Clean VM:**

1. Create a Windows 10/11 VM (VirtualBox, VMware, or Hyper-V)
2. Do NOT install Python, Visual Studio, or development tools
3. Copy the installer to the VM
4. Run the installer
5. Test the application
6. Verify it works without any runtime dependencies

**Expected behavior on clean systems:**

- [ ] Application installs without errors
- [ ] No missing DLL/library errors
- [ ] Application launches successfully
- [ ] All features work as expected
- [ ] No Python installation required
- [ ] No "missing module" errors

#### Error Handling and Edge Cases

**Test 12: Error Handling**

- [ ] Application handles invalid PDF files gracefully (shows error message, doesn't crash)
- [ ] Application handles corrupted PDF files gracefully
- [ ] Application handles very large PDF files (100+ MB)
- [ ] Application handles PDFs with special characters in filename
- [ ] Application handles insufficient disk space gracefully
- [ ] Application handles permission errors gracefully (read-only files)

**How to test:**

1. Try to open a non-PDF file (e.g., .txt, .jpg)
2. Try to open a corrupted PDF file
3. Try to process a very large PDF file
4. Try to save to a read-only directory
5. Verify the application shows appropriate error messages
6. Verify the application doesn't crash

**Test 13: Edge Cases**

- [ ] Application works with PDF files containing non-ASCII characters
- [ ] Application works with very small PDF files (< 1 KB)
- [ ] Application works with password-protected PDFs (if feature exists)
- [ ] Application works with PDFs containing forms, annotations, or embedded files

#### Performance Testing

**Test 14: Performance Benchmarks**

- [ ] Application launches in < 5 seconds
- [ ] Small PDF (< 1 MB) processes in < 5 seconds
- [ ] Medium PDF (1-10 MB) processes in < 30 seconds
- [ ] Large PDF (10-100 MB) processes in < 2 minutes
- [ ] Application memory usage is reasonable (< 500 MB for typical operations)
- [ ] Application CPU usage returns to idle after operations complete

**How to test:**

```bash
# Measure launch time
time ./dist/safetool-pdf/safetool-pdf-desktop

# Monitor resource usage during PDF processing
# Linux: htop or top
# macOS: Activity Monitor
# Windows: Task Manager
```

#### Comprehensive Testing Checklist

Use this checklist to ensure thorough testing before distribution:

**Pre-Distribution Checklist:**

- [ ] **Build Verification**
  - [ ] All build artifacts created successfully
  - [ ] No build errors or warnings
  - [ ] File sizes are reasonable (50-100 MB)

- [ ] **Basic Functionality**
  - [ ] Application launches without errors
  - [ ] UI renders correctly
  - [ ] Can open PDF files
  - [ ] Can process/optimize PDFs
  - [ ] Output files are valid PDFs

- [ ] **Translations**
  - [ ] Translation files are included
  - [ ] UI displays in correct language
  - [ ] Language switching works (if applicable)

- [ ] **Assets**
  - [ ] Icons display correctly
  - [ ] Application icon appears in taskbar/dock
  - [ ] All images load properly

- [ ] **Ghostscript Integration**
  - [ ] Ghostscript is detected (bundled or system)
  - [ ] Ghostscript-dependent features work
  - [ ] No "Ghostscript not found" errors (if bundled)

- [ ] **Platform-Specific**
  - [ ] Package installs correctly (.deb, .rpm, DMG, installer)
  - [ ] Application appears in application menu/Start Menu
  - [ ] Desktop shortcuts work (if created)
  - [ ] Uninstallation works cleanly

- [ ] **Clean System Testing**
  - [ ] Works on system without Python installed
  - [ ] Works on system without development tools
  - [ ] No missing dependency errors

- [ ] **Error Handling**
  - [ ] Handles invalid files gracefully
  - [ ] Shows appropriate error messages
  - [ ] Doesn't crash on errors

- [ ] **Performance**
  - [ ] Launches in reasonable time (< 5 seconds)
  - [ ] Processes PDFs efficiently
  - [ ] Memory usage is reasonable
  - [ ] No memory leaks after multiple operations

**If all items are checked, the build is ready for distribution!**

---

**Next Steps:**

- If you encounter issues during testing, see [Section 8: Troubleshooting](#8-troubleshooting)
- For information about CI vs local builds, see [Section 9.1: CI vs Local Builds](#91-ci-vs-local-builds)
- For customizing the build process, see [Section 9.3: Customizing Build Scripts](#93-customizing-build-scripts)

---
## 8. Troubleshooting

This section provides solutions to common build errors, platform-specific issues, and diagnostic commands to help you resolve problems quickly. If you encounter an issue not covered here, check the project's issue tracker or community forums for additional support.

### 8.1 Common Build Errors

This subsection covers the most frequently encountered build errors across all platforms, with symptoms, root causes, and step-by-step solutions.

---

#### Error: "PyInstaller dist not found"

**Symptom:**

The build script fails with an error message indicating that the PyInstaller output directory is missing:

```
Error: PyInstaller dist not found
Expected directory: dist/safetool-pdf/
```

Or platform-specific packaging scripts fail with:

```
Error: Cannot find dist/safetool-pdf/ directory
Please run PyInstaller first
```

**Cause:**

The PyInstaller step failed, was skipped, or didn't complete successfully. Platform-specific packaging scripts (build_appimage.sh, build_macos.sh, build_windows.bat) require the PyInstaller output to exist before they can create distribution packages.

**Solution:**

**Step 1: Run PyInstaller manually to see detailed error output**

```bash
python -m PyInstaller packaging/pyinstaller/safetool-pdf.spec
```

Watch the output carefully for error messages. Common issues include:
- Missing Python dependencies
- Hidden import errors
- File not found errors
- Permission issues

**Step 2: Check for missing dependencies**

If you see `ModuleNotFoundError`, install the missing package:

```bash
pip install -r requirements.txt
```

Or install the specific missing module:

```bash
pip install <module-name>
```

**Step 3: Verify Python version**

Ensure you're using Python 3.12 or higher:

```bash
python --version
```

If the version is too old, install Python 3.12+ and retry.

**Step 4: Check that the spec file exists**

```bash
ls packaging/pyinstaller/safetool-pdf.spec
```

If the file is missing, you may be in the wrong directory or the repository is incomplete.

**Step 5: Verify the output was created**

After PyInstaller completes successfully, verify the output:

```bash
# Linux/Windows
ls -la dist/safetool-pdf/

# macOS
ls -la dist/SafeToolPDF/
```

**Step 6: Retry the full build**

Once PyInstaller succeeds, retry the full build:

```bash
python dev-tools/build.py
```

---

#### Error: "Permission denied" on shell scripts

**Symptom:**

When running build scripts on Linux or macOS, you see:

```bash
bash: ./build_appimage.sh: Permission denied
```

Or:

```bash
bash: packaging/macos/build_macos.sh: Permission denied
```

**Cause:**

Shell scripts (.sh files) are not marked as executable. By default, files cloned from Git repositories may not have execute permissions set.

**Solution:**

**Step 1: Add execute permissions to the script**

```bash
# For AppImage build script
chmod +x packaging/linux/appimage/build_appimage.sh

# For macOS build script
chmod +x packaging/macos/build_macos.sh

# Or add permissions to all shell scripts at once
find packaging -name "*.sh" -exec chmod +x {} \;
```

**Step 2: Verify permissions were set**

```bash
ls -l packaging/linux/appimage/build_appimage.sh
```

Expected output:
```
-rwxr-xr-x 1 user group 1234 date build_appimage.sh
```

The `x` in `-rwxr-xr-x` indicates execute permission.

**Step 3: Retry the build**

```bash
bash packaging/linux/appimage/build_appimage.sh
# Or
python dev-tools/build.py
```

**Prevention:**

To avoid this issue in the future, set execute permissions immediately after cloning the repository:

```bash
find packaging -name "*.sh" -exec chmod +x {} \;
```

---

#### Error: Missing dependencies by platform

**Symptom:**

Build fails with errors indicating missing system packages or tools:

**Linux:**
```
dpkg-deb: command not found
rpm: command not found
fuse: command not found
```

**macOS:**
```
create-dmg: command not found
codesign: No such file or directory
```

**Windows:**
```
'iscc' is not recognized as an internal or external command
```

**Cause:**

Required platform-specific build tools are not installed on your system.

**Solution:**

**Linux (Ubuntu/Debian):**

```bash
# Install all build tools
sudo apt update
sudo apt install dpkg-deb rpm fuse libfuse2

# Verify installation
dpkg-deb --version
rpm --version
fusermount --version
```

**Linux (Fedora/RHEL):**

```bash
# Install all build tools
sudo dnf install dpkg rpm-build fuse fuse-libs

# Verify installation
dpkg-deb --version
rpm --version
fusermount --version
```

**Linux (Arch):**

```bash
# Install all build tools
sudo pacman -S dpkg rpm-tools fuse2

# Verify installation
dpkg-deb --version
rpm --version
fusermount --version
```

**macOS:**

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install build tools
brew install create-dmg

# Install Xcode Command Line Tools (for codesign)
xcode-select --install

# Verify installation
create-dmg --version
codesign --version
```

**Windows:**

```cmd
REM Install via Chocolatey (recommended)
choco install innosetup -y

REM Verify installation
iscc /?

REM If Chocolatey is not installed, download Inno Setup manually:
REM https://jrsoftware.org/isdl.php
```

**After installing dependencies, retry the build:**

```bash
python dev-tools/build.py
```

---

#### Error: Ghostscript issues

**Symptom:**

Ghostscript-related errors during build or runtime:

```
Warning: Could not download Ghostscript
Ghostscript not found in vendor directory
```

Or at runtime:

```
Warning: Ghostscript not found. Some optimization features are unavailable.
```

**Cause:**

- Ghostscript download failed during build (Windows/macOS)
- Ghostscript is not installed on the system (Linux)
- Ghostscript version is too old (< 9.50)

**Solution:**

**Windows - Download vendored Ghostscript:**

```cmd
REM Run the download script manually
python packaging\scripts\download_ghostscript.py

REM Verify the download
dir packaging\vendor\gs\bin\gswin64c.exe

REM If download fails, install manually:
REM 1. Download from https://www.ghostscript.com/releases/gsdnld.html
REM 2. Extract gswin64c.exe from the installer
REM 3. Place in packaging\vendor\gs\bin\gswin64c.exe

REM Rebuild
python dev-tools\build.py
```

**macOS - Install via Homebrew:**

```bash
# Install Ghostscript
brew install ghostscript

# Verify installation
gs --version

# Rebuild
python dev-tools/build.py
```

**Linux - Install via package manager:**

```bash
# Ubuntu/Debian
sudo apt install ghostscript

# Fedora/RHEL
sudo dnf install ghostscript

# Arch Linux
sudo pacman -S ghostscript

# Verify installation
gs --version

# Rebuild
python dev-tools/build.py
```

**Check Ghostscript version:**

SafeTool PDF requires Ghostscript 9.50 or higher. Check your version:

```bash
gs --version
```

If the version is below 9.50, upgrade:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install --only-upgrade ghostscript

# Fedora/RHEL
sudo dnf update ghostscript

# macOS
brew upgrade ghostscript
```

**Verify Ghostscript in built binary:**

After rebuilding, verify Ghostscript is included:

```bash
# Windows
dir dist\safetool-pdf\vendor\gs\bin\gswin64c.exe

# macOS
ls -lh dist/SafeToolPDF.app/Contents/Resources/vendor/gs/bin/gs

# Linux (uses system Ghostscript)
which gs
```

**Note:** Ghostscript is optional. The application will work without it, but some advanced PDF optimization features will be unavailable.

---

#### Error: Code signing errors on macOS

**Symptom:**

On macOS, you encounter code signing errors during build or when running the application:

```
codesign: command not found
```

Or:

```
Error: The application "SafeToolPDF" can't be opened.
The application is damaged and can't be opened.
```

Or:

```
"SafeToolPDF.app" is damaged and can't be opened. You should move it to the Trash.
```

**Cause:**

- Xcode Command Line Tools are not installed (missing `codesign`)
- Code signature is invalid or missing
- Gatekeeper is blocking the unsigned application
- The .app bundle structure is corrupted

**Solution:**

**Step 1: Install Xcode Command Line Tools**

```bash
# Install Xcode Command Line Tools
xcode-select --install

# Verify installation
codesign --version
```

Expected output:
```
codesign-xxx
```

**Step 2: Re-sign the application with ad-hoc signature**

```bash
# Remove existing signature
codesign --remove-signature dist/SafeToolPDF.app

# Sign with ad-hoc signature
codesign --force --deep --sign - dist/SafeToolPDF.app

# Verify signature
codesign -dv dist/SafeToolPDF.app
```

Expected output:
```
Executable=/path/to/dist/SafeToolPDF.app/Contents/MacOS/SafeToolPDF
Identifier=SafeToolPDF
Format=app bundle with Mach-O thin (arm64)
CodeDirectory v=20500 size=... flags=0x2(adhoc) hashes=...
Signature=adhoc
```

**Step 3: Bypass Gatekeeper for local testing**

If you see "App is damaged" error, bypass Gatekeeper:

```bash
# Remove quarantine attribute
xattr -cr dist/SafeToolPDF.app

# Or allow the app explicitly
sudo spctl --add dist/SafeToolPDF.app
sudo spctl --enable --label "SafeToolPDF"
```

**Step 4: Test the application**

```bash
open dist/SafeToolPDF.app
```

The application should launch without security warnings.

**Step 5: Rebuild the DMG**

After re-signing the .app bundle, rebuild the DMG:

```bash
bash packaging/macos/build_macos.sh
```

**For distribution to other users:**

Ad-hoc signing is sufficient for local testing but not for distribution. To distribute to other users, you need:

1. **Apple Developer ID certificate** - Sign with a real certificate ($99/year)
2. **Notarization** - Submit to Apple for malware scanning
3. **Stapling** - Attach notarization ticket to the app

These steps are beyond the scope of local builds. For local testing, ad-hoc signing is sufficient.

**Alternative: Run without signing (not recommended)**

If you can't sign the app, you can run it directly from the command line:

```bash
./dist/SafeToolPDF.app/Contents/MacOS/SafeToolPDF
```

This bypasses Gatekeeper but is not recommended for regular use.

---

#### Error: Inno Setup problems on Windows

**Symptom:**

On Windows, the installer creation fails:

```
Error: Inno Setup not found
ISCC.exe is not recognized as an internal or external command
```

Or:

```
Error: ISCC.exe failed with exit code 1
```

**Cause:**

- Inno Setup is not installed
- Inno Setup is not in the system PATH
- The .iss script has syntax errors
- PyInstaller output is missing or incomplete

**Solution:**

**Step 1: Install Inno Setup**

**Option A: Via Chocolatey (recommended)**

```cmd
choco install innosetup -y
```

**Option B: Manual installation**

1. Download Inno Setup 6 from [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php)
2. Run the installer
3. Follow the installation wizard

**Step 2: Verify Inno Setup installation**

```cmd
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /?
```

Expected output:
```
Inno Setup 6.x.x Command-Line Compiler
Copyright (C) 1997-2024 Jordan Russell. All rights reserved.
```

**Step 3: Add Inno Setup to PATH (optional)**

To run `iscc` from any directory:

1. Open System Properties → Environment Variables
2. Edit the `Path` variable
3. Add: `C:\Program Files (x86)\Inno Setup 6\`
4. Click OK and restart Command Prompt

Verify:
```cmd
iscc /?
```

**Step 4: Verify PyInstaller output exists**

Inno Setup requires the PyInstaller output to exist:

```cmd
dir dist\safetool-pdf\safetool-pdf-desktop.exe
```

If the file doesn't exist, run PyInstaller first:

```cmd
python -m PyInstaller packaging\pyinstaller\safetool-pdf.spec
```

**Step 5: Check the .iss script for errors**

If ISCC fails with exit code 1, run it manually to see detailed errors:

```cmd
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\windows\safetool-pdf.iss
```

Common issues:
- **Missing source files:** Ensure `dist\safetool-pdf\` exists and contains all files
- **Invalid paths:** Check that all file paths in the .iss script are correct
- **Missing icon:** Ensure `assets\icon.ico` exists

**Step 6: Retry the build**

```cmd
python dev-tools\build.py
```

**If Inno Setup is not available:**

The build script will create a portable version in `dist\safetool-pdf\` that can be used without installation. You'll see a warning:

```
WARNING: Inno Setup not found. Skipping installer creation.
Install Inno Setup 6 to build the installer.
```

The portable version works without installation - just run `dist\safetool-pdf\safetool-pdf-desktop.exe`.

---

#### Error: Module import errors (hidden imports)

**Symptom:**

PyInstaller completes successfully, but the application fails to launch with module import errors:

```
ModuleNotFoundError: No module named 'PySide6.QtCore'
ModuleNotFoundError: No module named 'pikepdf'
ModuleNotFoundError: No module named 'fitz'
ImportError: cannot import name 'X' from 'Y'
```

Or you see warnings during PyInstaller build:

```
WARNING: Hidden import "X" not found!
```

**Cause:**

PyInstaller's automatic dependency detection missed some modules. This commonly happens with:
- Dynamic imports (using `importlib` or `__import__`)
- Plugins or extensions loaded at runtime
- Modules imported conditionally
- C extensions with complex dependencies

**Solution:**

**Step 1: Identify the missing module**

Note the exact module name from the error message. For example:
- `PySide6.QtCore` → Missing Qt module
- `pikepdf._core` → Missing pikepdf submodule
- `fitz` → Missing PyMuPDF module

**Step 2: Add the module to hidden imports**

Edit `packaging/pyinstaller/safetool-pdf.spec` and add the missing module to the `hiddenimports` list:

```python
a = Analysis(
    ['safetool_pdf_desktop/app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('i18n', 'i18n'),
        ('LICENSE', '.'),
        ('config.py', '.'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'pikepdf',
        'pikepdf._core',  # Add missing submodule
        'fitz',
        'PIL',
        'qtawesome',
        # Add your missing module here
        'your_missing_module',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'test',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
```

**Step 3: Rebuild with PyInstaller**

```bash
# Clean previous build
rm -rf build/ dist/

# Rebuild
python -m PyInstaller packaging/pyinstaller/safetool-pdf.spec
```

**Step 4: Test the application**

```bash
# Linux
./dist/safetool-pdf/safetool-pdf-desktop

# macOS
open dist/SafeToolPDF.app

# Windows
dist\safetool-pdf\safetool-pdf-desktop.exe
```

If the error persists, check the console output for additional missing modules and repeat steps 2-4.

**Step 5: Use PyInstaller's --debug option for detailed analysis**

If you're unsure which modules are missing, run PyInstaller with debug logging:

```bash
python -m PyInstaller --log-level DEBUG packaging/pyinstaller/safetool-pdf.spec 2>&1 | tee pyinstaller-debug.log
```

Search the log for "not found" or "WARNING" messages to identify missing modules.

**Common hidden imports for SafeTool PDF:**

If you encounter import errors, try adding these common hidden imports:

```python
hiddenimports=[
    # Qt6 modules
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtPrintSupport',
    
    # PDF libraries
    'pikepdf',
    'pikepdf._core',
    'pikepdf._qpdf',
    'fitz',
    'fitz.fitz',
    
    # Image processing
    'PIL',
    'PIL.Image',
    'PIL.ImageQt',
    
    # Icons
    'qtawesome',
    'qtawesome.iconic_font',
    
    # Other
    'pkg_resources',
],
```

**Alternative: Use --collect-all for problematic packages**

If a package has many submodules, you can collect all of them:

Edit the .spec file to use `collect_all`:

```python
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# Collect all submodules from pikepdf
tmp_ret = collect_all('pikepdf')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

a = Analysis(
    ['safetool_pdf_desktop/app.py'],
    ...
    datas=datas + [
        ('assets', 'assets'),
        ...
    ],
    binaries=binaries,
    hiddenimports=hiddenimports + [
        'PySide6.QtCore',
        ...
    ],
    ...
)
```

**Prevention:**

To avoid hidden import issues:
- Use explicit imports instead of dynamic imports when possible
- Test the PyInstaller bundle immediately after building
- Keep a list of known hidden imports in the .spec file

---

### 8.2 Platform-Specific Issues

This subsection covers issues that are specific to individual platforms (Linux, macOS, or Windows).

---

#### Linux-Specific Issues

**Issue: AppImage won't run - "fuse: failed to exec fusermount"**

**Symptom:**
```
fuse: failed to exec fusermount: No such file or directory
Cannot mount AppImage, please check your FUSE setup.
```

**Solution:**

Install FUSE:

```bash
# Ubuntu/Debian
sudo apt install fuse libfuse2

# Fedora/RHEL
sudo dnf install fuse fuse-libs

# Arch Linux
sudo pacman -S fuse2
```

Verify installation:
```bash
fusermount --version
```

**Alternative: Extract and run without FUSE**

If FUSE is not available (e.g., in containers):

```bash
# Extract AppImage contents
./SafeToolPDF-x86_64.AppImage --appimage-extract

# Run directly
./squashfs-root/AppRun
```

---

**Issue: .deb package installation fails - "dependency problems"**

**Symptom:**
```
dpkg: dependency problems prevent configuration of safetoolpdf:
 safetoolpdf depends on libqt6core6; however:
  Package libqt6core6 is not installed.
```

**Solution:**

Install dependencies first:

```bash
# Fix broken dependencies
sudo apt --fix-broken install

# Or install dependencies manually
sudo apt install libqt6core6 libqt6gui6 libqt6widgets6

# Then install the package
sudo dpkg -i dist/SafeToolPDF-*-linux-amd64.deb
```

---

**Issue: .rpm package installation fails - "Failed dependencies"**

**Symptom:**
```
error: Failed dependencies:
    qt6-qtbase is needed by SafeToolPDF-0.1.0-1.x86_64
```

**Solution:**

Install dependencies first:

```bash
# Fedora/RHEL
sudo dnf install qt6-qtbase

# Then install the package
sudo rpm -i dist/SafeToolPDF-*-linux-x86_64.rpm

# Or use dnf to auto-resolve dependencies
sudo dnf install dist/SafeToolPDF-*-linux-x86_64.rpm
```

---

#### macOS-Specific Issues

**Issue: "App is damaged and can't be opened" on other machines**

**Symptom:**

The application works on your build machine but shows this error on other Macs:

```
"SafeToolPDF.app" is damaged and can't be opened. You should move it to the Trash.
```

**Cause:**

The application is ad-hoc signed, which only works on the machine where it was built. macOS Gatekeeper blocks ad-hoc signed apps from other sources.

**Solution for local testing:**

On the target machine, bypass Gatekeeper:

```bash
# Remove quarantine attribute
xattr -cr /Applications/SafeToolPDF.app

# Or allow the app via System Preferences
# System Preferences → Security & Privacy → General → "Open Anyway"
```

**Solution for distribution:**

To distribute to other users, you need to sign with a Developer ID certificate and notarize:

1. **Obtain Apple Developer ID certificate** ($99/year)
2. **Sign the application:**
   ```bash
   codesign --force --deep --sign "Developer ID Application: Your Name" dist/SafeToolPDF.app
   ```
3. **Create DMG:**
   ```bash
   bash packaging/macos/build_macos.sh
   ```
4. **Notarize the DMG:**
   ```bash
   xcrun notarytool submit dist/SafeToolPDF.dmg --keychain-profile "notary-profile" --wait
   ```
5. **Staple the notarization ticket:**
   ```bash
   xcrun stapler staple dist/SafeToolPDF.dmg
   ```

These steps require an Apple Developer account and are beyond the scope of local builds.

---

**Issue: create-dmg fails - "Device busy"**

**Symptom:**
```
create-dmg: error: Could not create DMG
hdiutil: create failed - Resource busy
```

**Cause:**

A DMG with the same name is already mounted, or the output file is locked.

**Solution:**

```bash
# Unmount any existing DMG
hdiutil detach "/Volumes/SafeTool PDF"

# Remove the old DMG file
rm dist/SafeToolPDF.dmg

# Retry the build
bash packaging/macos/build_macos.sh
```

---

**Issue: Application won't run on Apple Silicon (M1/M2/M3)**

**Symptom:**

The application fails to launch on Apple Silicon Macs with:

```
Bad CPU type in executable
```

**Cause:**

The application was built on an Intel Mac and is not compatible with Apple Silicon.

**Solution:**

Build on an Apple Silicon Mac, or create a universal binary:

**Option 1: Build on Apple Silicon**

Build the application on an M1/M2/M3 Mac. The resulting binary will work on Apple Silicon.

**Option 2: Create a universal binary (advanced)**

Modify the .spec file to create a universal binary that works on both Intel and Apple Silicon:

```python
# In packaging/pyinstaller/safetool-pdf.spec
a = Analysis(
    ...
    target_arch='universal2',  # Add this line
    ...
)
```

Then rebuild:

```bash
python -m PyInstaller packaging/pyinstaller/safetool-pdf.spec
```

**Note:** Universal binaries are larger (~2x size) but work on both architectures.

---

#### Windows-Specific Issues

**Issue: "Windows protected your PC" SmartScreen warning**

**Symptom:**

When running the installer, Windows SmartScreen shows:

```
Windows protected your PC
Microsoft Defender SmartScreen prevented an unrecognized app from starting.
```

**Cause:**

The installer is not signed with a code signing certificate. Windows SmartScreen blocks unsigned executables from unknown publishers.

**Solution for users:**

Click "More info" → "Run anyway" to proceed with installation.

**Solution for developers (distribution):**

To avoid this warning, sign the installer with a code signing certificate:

1. **Obtain a code signing certificate** ($100-$400/year from certificate authorities)
2. **Sign the installer:**
   ```cmd
   signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com dist\SafeToolPDF-*-setup-x64.exe
   ```
3. **Build reputation with Microsoft SmartScreen** (requires many downloads over time)

Code signing is beyond the scope of local builds but is necessary for professional distribution.

---

**Issue: Installer fails - "Access denied"**

**Symptom:**
```
Error: Access denied
The installer could not write to C:\Program Files\SafeTool PDF\
```

**Cause:**

The installer requires administrator privileges to write to Program Files.

**Solution:**

Right-click the installer and select "Run as administrator":

```cmd
REM Or from command line with admin privileges
runas /user:Administrator dist\SafeToolPDF-*-setup-x64.exe
```

---

**Issue: Application fails to start - "VCRUNTIME140.dll not found"**

**Symptom:**
```
The code execution cannot proceed because VCRUNTIME140.dll was not found.
```

**Cause:**

The Visual C++ Redistributable is not installed on the system. PyInstaller bundles most dependencies, but some system DLLs may be missing on clean Windows installations.

**Solution:**

Install the Visual C++ Redistributable:

1. Download from [Microsoft's website](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
2. Install the x64 version
3. Retry launching the application

**Prevention:**

To bundle the Visual C++ Redistributable with your installer, modify the Inno Setup script:

```ini
[Files]
Source: "vcredist_x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Run]
Filename: "{tmp}\vcredist_x64.exe"; Parameters: "/quiet /norestart"; StatusMsg: "Installing Visual C++ Redistributable..."; Check: VCRedistNeedsInstall
```

---

**Issue: Antivirus flags the installer as malware**

**Symptom:**

Antivirus software quarantines or deletes the installer, showing warnings like:

```
Threat detected: Trojan:Win32/Wacatac
```

**Cause:**

PyInstaller-generated executables are sometimes flagged as false positives by antivirus software because:
- They use self-extraction techniques similar to malware
- They're unsigned (no code signing certificate)
- They're not widely distributed (low reputation)

**Solution for users:**

Add the installer to your antivirus exclusion list:

1. Open your antivirus software
2. Go to Settings → Exclusions
3. Add `dist\SafeToolPDF-*-setup-x64.exe` to the exclusion list
4. Retry the installation

**Solution for developers:**

1. **Sign the installer** with a code signing certificate (reduces false positives)
2. **Submit to antivirus vendors** for whitelisting (VirusTotal, Microsoft, etc.)
3. **Build reputation** over time (more downloads = fewer false positives)
4. **Use alternative packaging** (e.g., MSI instead of Inno Setup)

**Verify it's a false positive:**

Upload the installer to [VirusTotal](https://www.virustotal.com/) to check multiple antivirus engines. If only 1-2 engines flag it and the rest are clean, it's likely a false positive.

---

### 8.3 Diagnostic Commands

This subsection provides useful commands for diagnosing build issues, verifying installations, and troubleshooting problems.

---

#### Check Build Environment

**Verify Python installation:**

```bash
# Check Python version
python --version
python3 --version  # macOS/Linux alternative

# Check Python location
which python       # Linux/macOS
where python       # Windows

# Check pip version
pip --version
```

**Verify PyInstaller installation:**

```bash
# Check PyInstaller version
python -m PyInstaller --version

# Check PyInstaller location
pip show pyinstaller
```

**Verify Python dependencies:**

```bash
# List all installed packages
pip list

# Check specific packages
pip show pikepdf
pip show PyMuPDF
pip show PySide6-Essentials
pip show Pillow
pip show qtawesome

# Verify all requirements are installed
pip check
```

---

#### Check Platform-Specific Tools

**Linux:**

```bash
# Check dpkg-deb
dpkg-deb --version
which dpkg-deb

# Check rpm
rpm --version
which rpm

# Check fuse
fusermount --version
which fusermount

# Check Ghostscript
gs --version
which gs
```

**macOS:**

```bash
# Check create-dmg
create-dmg --version
which create-dmg

# Check codesign
codesign --version
which codesign

# Check hdiutil
hdiutil --version
which hdiutil

# Check Ghostscript
gs --version
which gs

# Check Xcode Command Line Tools
xcode-select -p
```

**Windows:**

```cmd
REM Check Inno Setup
iscc /?
where iscc

REM Check Ghostscript
gswin64c --version
where gswin64c

REM Check Python
python --version
where python

REM Check pip
pip --version
where pip
```

---

#### Verify Build Artifacts

**Check PyInstaller output:**

```bash
# Linux/Windows
ls -la dist/safetool-pdf/
ls -lh dist/safetool-pdf/safetool-pdf-desktop*
du -sh dist/safetool-pdf/

# macOS
ls -la dist/SafeToolPDF/
ls -lh dist/SafeToolPDF/SafeToolPDF*
du -sh dist/SafeToolPDF/

# Windows
dir dist\safetool-pdf\
dir dist\safetool-pdf\safetool-pdf-desktop.exe
```

**Check platform-specific packages:**

```bash
# Linux - Check all packages
ls -lh dist/SafeToolPDF-*

# Linux - Check .deb
dpkg-deb --info dist/SafeToolPDF-*-linux-amd64.deb
dpkg-deb --contents dist/SafeToolPDF-*-linux-amd64.deb

# Linux - Check .rpm
rpm -qpi dist/SafeToolPDF-*-linux-x86_64.rpm
rpm -qpl dist/SafeToolPDF-*-linux-x86_64.rpm

# Linux - Check AppImage
file dist/SafeToolPDF-x86_64.AppImage
ls -lh dist/SafeToolPDF-x86_64.AppImage

# macOS - Check .app bundle
ls -la dist/SafeToolPDF.app/Contents/
codesign -dv dist/SafeToolPDF.app

# macOS - Check DMG
ls -lh dist/SafeToolPDF.dmg
hdiutil imageinfo dist/SafeToolPDF.dmg

# Windows - Check installer
dir dist\SafeToolPDF-*-setup-x64.exe
```

**Check Ghostscript inclusion:**

```bash
# Windows
dir dist\safetool-pdf\vendor\gs\bin\gswin64c.exe
dist\safetool-pdf\vendor\gs\bin\gswin64c.exe --version

# macOS
ls -lh dist/SafeToolPDF.app/Contents/Resources/vendor/gs/bin/gs
dist/SafeToolPDF.app/Contents/Resources/vendor/gs/bin/gs --version

# Linux (system Ghostscript)
which gs
gs --version
```

**Check translations and assets:**

```bash
# Linux
ls -la dist/safetool-pdf/i18n/
ls -la dist/safetool-pdf/assets/

# macOS
ls -la dist/SafeToolPDF.app/Contents/Resources/i18n/
ls -la dist/SafeToolPDF.app/Contents/Resources/assets/

# Windows
dir dist\safetool-pdf\i18n\
dir dist\safetool-pdf\assets\
```

---

#### Test Executables

**Test PyInstaller executable directly:**

```bash
# Linux
./dist/safetool-pdf/safetool-pdf-desktop --version
./dist/safetool-pdf/safetool-pdf-desktop --help

# macOS
./dist/SafeToolPDF/SafeToolPDF --version
open dist/SafeToolPDF.app

# Windows
dist\safetool-pdf\safetool-pdf-desktop.exe --version
dist\safetool-pdf\safetool-pdf-desktop.exe --help
```

**Test package installations:**

```bash
# Linux - Test .deb
sudo dpkg -i dist/SafeToolPDF-*-linux-amd64.deb
safetool-pdf-desktop --version
sudo dpkg -r safetoolpdf

# Linux - Test .rpm
sudo rpm -i dist/SafeToolPDF-*-linux-x86_64.rpm
safetool-pdf-desktop --version
sudo rpm -e SafeToolPDF

# Linux - Test AppImage
chmod +x dist/SafeToolPDF-x86_64.AppImage
./dist/SafeToolPDF-x86_64.AppImage --version

# macOS - Test DMG
hdiutil attach dist/SafeToolPDF.dmg
ls -la /Volumes/SafeToolPDF/
hdiutil detach /Volumes/SafeToolPDF

# Windows - Test installer (requires admin)
dist\SafeToolPDF-*-setup-x64.exe /SILENT
"C:\Program Files\SafeTool PDF\safetool-pdf-desktop.exe" --version
```

---

#### Debug PyInstaller Issues

**Run PyInstaller with debug logging:**

```bash
# Generate detailed debug log
python -m PyInstaller --log-level DEBUG packaging/pyinstaller/safetool-pdf.spec 2>&1 | tee pyinstaller-debug.log

# Search for errors in the log
grep -i "error" pyinstaller-debug.log
grep -i "warning" pyinstaller-debug.log
grep -i "not found" pyinstaller-debug.log
```

**Check for missing imports:**

```bash
# Run the executable and capture output
./dist/safetool-pdf/safetool-pdf-desktop 2>&1 | tee runtime-errors.log

# Search for import errors
grep -i "ModuleNotFoundError" runtime-errors.log
grep -i "ImportError" runtime-errors.log
```

**Analyze PyInstaller bundle contents:**

```bash
# List all files in the bundle
find dist/safetool-pdf/ -type f

# Check for specific modules
find dist/safetool-pdf/_internal/ -name "*pikepdf*"
find dist/safetool-pdf/_internal/ -name "*PySide6*"
find dist/safetool-pdf/_internal/ -name "*fitz*"

# Check bundle size breakdown
du -sh dist/safetool-pdf/*
du -sh dist/safetool-pdf/_internal/*
```

**Test individual components:**

```bash
# Test Python imports in the bundle
cd dist/safetool-pdf/
./safetool-pdf-desktop -c "import pikepdf; print(pikepdf.__version__)"
./safetool-pdf-desktop -c "import PySide6; print(PySide6.__version__)"
./safetool-pdf-desktop -c "import fitz; print(fitz.__version__)"
```

---

#### Check System Resources

**Monitor build process:**

```bash
# Linux - Monitor CPU and memory
htop
# Or
top

# macOS - Monitor resources
# Open Activity Monitor app
# Or use command line:
top -o cpu

# Windows - Monitor resources
# Open Task Manager (Ctrl+Shift+Esc)
# Or use command line:
tasklist
```

**Check disk space:**

```bash
# Linux/macOS
df -h .
du -sh dist/

# Windows
dir dist\
```

**Check available memory:**

```bash
# Linux
free -h

# macOS
vm_stat

# Windows
systeminfo | findstr /C:"Available Physical Memory"
```

---

#### Network Diagnostics (for Ghostscript download)

**Test Ghostscript download URL:**

```bash
# Test connectivity
curl -I https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10060/gs10060w64.exe

# Download manually
curl -L -o gs10060w64.exe https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10060/gs10060w64.exe

# Check file size
ls -lh gs10060w64.exe
```

**Check proxy settings:**

```bash
# Linux/macOS
echo $HTTP_PROXY
echo $HTTPS_PROXY

# Windows
echo %HTTP_PROXY%
echo %HTTPS_PROXY%
```

---

#### Collect Diagnostic Information

**Generate a comprehensive diagnostic report:**

```bash
#!/bin/bash
# Save as: diagnose.sh

echo "=== System Information ==="
uname -a
python --version
pip --version

echo ""
echo "=== Python Packages ==="
pip list | grep -E "(pikepdf|PyMuPDF|PySide6|Pillow|qtawesome|pyinstaller)"

echo ""
echo "=== Build Tools ==="
which dpkg-deb && dpkg-deb --version
which rpm && rpm --version
which create-dmg && create-dmg --version
which codesign && codesign --version
which iscc && iscc /?

echo ""
echo "=== Ghostscript ==="
which gs && gs --version

echo ""
echo "=== Build Artifacts ==="
ls -lh dist/

echo ""
echo "=== Disk Space ==="
df -h .

echo ""
echo "=== Memory ==="
free -h  # Linux
vm_stat  # macOS
```

Run the script:

```bash
chmod +x diagnose.sh
./diagnose.sh > diagnostic-report.txt
```

**Windows diagnostic script:**

```cmd
@echo off
REM Save as: diagnose.bat

echo === System Information ===
systeminfo | findstr /C:"OS Name" /C:"OS Version"
python --version
pip --version

echo.
echo === Python Packages ===
pip list | findstr /C:"pikepdf" /C:"PyMuPDF" /C:"PySide6" /C:"Pillow" /C:"qtawesome" /C:"pyinstaller"

echo.
echo === Build Tools ===
where iscc
iscc /?

echo.
echo === Ghostscript ===
where gswin64c
gswin64c --version

echo.
echo === Build Artifacts ===
dir dist\

echo.
echo === Disk Space ===
dir dist\
```

Run the script:

```cmd
diagnose.bat > diagnostic-report.txt
```

---

#### Common Diagnostic Workflows

**Workflow 1: PyInstaller fails to build**

```bash
# Step 1: Check Python version
python --version

# Step 2: Check dependencies
pip check
pip list | grep -E "(pikepdf|PyMuPDF|PySide6)"

# Step 3: Run PyInstaller with debug logging
python -m PyInstaller --log-level DEBUG packaging/pyinstaller/safetool-pdf.spec 2>&1 | tee debug.log

# Step 4: Search for errors
grep -i "error" debug.log
grep -i "not found" debug.log

# Step 5: Check spec file
cat packaging/pyinstaller/safetool-pdf.spec
```

**Workflow 2: Application fails to launch**

```bash
# Step 1: Check executable exists
ls -lh dist/safetool-pdf/safetool-pdf-desktop

# Step 2: Check permissions
chmod +x dist/safetool-pdf/safetool-pdf-desktop

# Step 3: Run and capture errors
./dist/safetool-pdf/safetool-pdf-desktop 2>&1 | tee runtime-errors.log

# Step 4: Check for missing modules
grep -i "ModuleNotFoundError" runtime-errors.log

# Step 5: Check bundle contents
ls -la dist/safetool-pdf/_internal/
```

**Workflow 3: Package creation fails**

```bash
# Step 1: Verify PyInstaller output exists
ls -la dist/safetool-pdf/

# Step 2: Check platform tools
which dpkg-deb  # Linux
which create-dmg  # macOS
where iscc  # Windows

# Step 3: Check script permissions
ls -l packaging/linux/appimage/build_appimage.sh
chmod +x packaging/linux/appimage/build_appimage.sh

# Step 4: Run packaging script manually
bash packaging/linux/appimage/build_appimage.sh 2>&1 | tee package-errors.log

# Step 5: Check for errors
grep -i "error" package-errors.log
```

---

**For additional help:**

- Check the project's GitHub Issues: [github.com/your-repo/issues](https://github.com)
- Consult the PyInstaller documentation: [pyinstaller.org/en/stable/](https://pyinstaller.org/en/stable/)
- Ask in the project's community forums or Discord
- Review the CI/CD workflow files in `.github/workflows/` for reference

---


## 9. Advanced Topics

This section covers advanced topics for developers who want to understand the differences between CI and local builds, customize the build process, or work with the packaging directory structure. These topics are optional but provide valuable insights for maintaining and extending the build system.

### 9.1 CI vs Local Builds

Understanding the differences between GitHub Actions CI builds and local builds helps you replicate CI behavior locally and troubleshoot discrepancies between environments.

#### Key Differences

**1. Environment Variables**

GitHub Actions sets several environment variables that affect the build:

| Variable | CI Value | Local Default | Purpose |
|----------|----------|---------------|---------|
| `APP_VERSION` | Extracted from Git tag | Auto-detected from `config.py` | Sets application version in build |
| `GITHUB_REF` | `refs/tags/v1.0.0` | Not set | Git reference (tag/branch) |
| `GITHUB_WORKSPACE` | `/home/runner/work/...` | Current directory | Workspace root path |
| `CI` | `true` | Not set | Indicates CI environment |

**How CI extracts APP_VERSION:**

```yaml
# From .github/workflows/release.yml
- name: Extract version from tag
  id: version
  run: |
    if [ -n "${{ github.event.inputs.tag }}" ]; then
      TAG="${{ github.event.inputs.tag }}"
      TAG="${TAG#v}"
    else
      TAG="${GITHUB_REF#refs/tags/v}"
    fi
    echo "tag=$TAG" >> "$GITHUB_OUTPUT"

- name: Build
  run: python dev-tools/build.py
  env:
    APP_VERSION: ${{ steps.version.outputs.tag }}
```

**Replicating CI version locally:**

```bash
# Set APP_VERSION manually
export APP_VERSION=1.0.0
python dev-tools/build.py

# Or inline
APP_VERSION=1.0.0 python dev-tools/build.py
```

**2. Code Signing Differences**

| Aspect | CI Build | Local Build |
|--------|----------|-------------|
| **macOS Signing** | Ad-hoc signature (`codesign --sign -`) | Ad-hoc signature (`codesign --sign -`) |
| **macOS Notarization** | Not performed | Not performed |
| **Windows Signing** | Not performed (unsigned) | Not performed (unsigned) |
| **Distribution** | Works on build machine only | Works on build machine only |

**Note:** Both CI and local builds use ad-hoc signing for macOS, which is sufficient for testing but not for distribution. For production releases, you need:

- **macOS:** Developer ID certificate + notarization
- **Windows:** Code signing certificate

**3. Continue-on-Error Behavior**

CI uses `continue-on-error: true` for the Ghostscript download step:

```yaml
- name: Download vendored Ghostscript
  run: python packaging/scripts/download_ghostscript.py
  continue-on-error: true
```

**Why continue-on-error is used:**

- Ghostscript download may fail due to network issues
- Ghostscript is optional (application works without it)
- Build should not fail if Ghostscript is unavailable
- Linux uses system Ghostscript (not vendored)

**Local equivalent:**

The build script handles Ghostscript download failures gracefully:

```bash
python packaging/scripts/download_ghostscript.py || echo "Ghostscript download failed (optional)"
python dev-tools/build.py
```

If the download fails, the build continues without vendored Ghostscript.

**4. Multi-Platform Builds**

| Aspect | CI Build | Local Build |
|--------|----------|-------------|
| **Platforms** | Linux, macOS, Windows (parallel) | Single platform (your machine) |
| **Runners** | GitHub-hosted runners | Your local machine |
| **Artifacts** | All platforms in one workflow | One platform per build |
| **Testing** | Automated on all platforms | Manual on your platform |

**CI builds all platforms in parallel:**

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
```

**Simulating multi-platform builds locally:**

You cannot build for all platforms from a single machine, but you can:

**Option 1: Use VMs or containers**

```bash
# Linux builds in Docker
docker run -it ubuntu:22.04 bash
# Inside container: clone repo, install deps, build

# macOS builds in VM (requires macOS host)
# Use Parallels, VMware, or VirtualBox

# Windows builds in VM
# Use VirtualBox, VMware, or Hyper-V
```

**Option 2: Use GitHub Actions for multi-platform builds**

Even for local development, you can trigger CI builds:

```bash
# Push to a branch
git push origin feature-branch

# Or create a tag
git tag v1.0.0-test
git push origin v1.0.0-test
```

**Option 3: Cross-compilation (limited support)**

PyInstaller does not support cross-compilation. You must build on the target platform.

#### Replicating CI Environment Locally

To replicate the CI environment as closely as possible:

**Step 1: Use the same Python version**

Check the CI workflow for the Python version:

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
```

Install Python 3.12 locally and use it for builds.

**Step 2: Use the same dependencies**

CI installs from `requirements.txt`:

```bash
pip install -r requirements.txt
```

Ensure your local environment matches.

**Step 3: Set environment variables**

```bash
# Linux/macOS
export APP_VERSION=1.0.0
export CI=true

# Windows
set APP_VERSION=1.0.0
set CI=true
```

**Step 4: Use the same build commands**

CI uses the unified build script:

```bash
python dev-tools/build.py
```

Use the same command locally.

**Step 5: Clean build environment**

CI starts with a clean environment. Replicate this locally:

```bash
# Remove previous builds
rm -rf build/ dist/

# Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Rebuild
python dev-tools/build.py
```

**Step 6: Use containers for exact replication (Linux)**

For the most accurate replication, use the same container image as CI:

```bash
# Use Ubuntu 22.04 (same as ubuntu-latest)
docker run -it -v $(pwd):/workspace ubuntu:22.04 bash

# Inside container
cd /workspace
apt update
apt install -y python3.12 python3-pip dpkg-deb rpm fuse libfuse2
pip install -r requirements.txt
python dev-tools/build.py
```

#### Debugging CI vs Local Discrepancies

If builds work in CI but fail locally (or vice versa):

**Check 1: Python version mismatch**

```bash
# Local
python --version

# CI (check workflow file)
# python-version: '3.12'
```

**Check 2: Dependency version mismatch**

```bash
# Compare installed versions
pip list > local-deps.txt

# Compare with requirements.txt
diff local-deps.txt requirements.txt
```

**Check 3: Environment variables**

```bash
# Check if APP_VERSION is set
echo $APP_VERSION

# Check if CI variable affects behavior
export CI=true
python dev-tools/build.py
```

**Check 4: File permissions (Linux/macOS)**

CI may have different default permissions:

```bash
# Ensure scripts are executable
find packaging -name "*.sh" -exec chmod +x {} \;
```

**Check 5: Path differences**

CI uses absolute paths in some cases:

```bash
# Use absolute paths
python -m PyInstaller $(pwd)/packaging/pyinstaller/safetool-pdf.spec
```

---

### 9.2 Packaging Directory Structure

Understanding the `packaging/` directory structure helps you customize the build process, add new packaging formats, or troubleshoot build issues.

#### Directory Tree

```
packaging/
├── ci/
│   └── build.yml                          # CI build workflow template
├── linux/
│   ├── appimage/
│   │   ├── build_appimage.sh              # AppImage build script
│   │   ├── AppRun                         # AppImage entry point
│   │   ├── org.safetoolhub.safetoolpdf.desktop  # Desktop entry
│   │   └── org.safetoolhub.safetoolpdf.metainfo.xml  # AppStream metadata
│   └── flatpak/
│       └── org.safetoolhub.safetoolpdf.metainfo.xml  # Flatpak metadata
├── macos/
│   ├── build_macos.sh                     # macOS build script (.app + DMG)
│   └── Info.plist                         # macOS app bundle metadata
├── nuitka/
│   └── build.sh                           # Nuitka build script (alternative)
├── pyinstaller/
│   └── safetool-pdf.spec                  # PyInstaller specification file
├── scripts/
│   └── download_ghostscript.py            # Ghostscript download script
├── vendor/
│   ├── gs/                                # Vendored Ghostscript (downloaded)
│   │   └── bin/
│   │       ├── gswin64c.exe               # Windows Ghostscript
│   │       └── gs                         # macOS/Linux Ghostscript
│   └── .gitkeep                           # Keep empty directory in Git
└── windows/
    ├── build_windows.bat                  # Windows build script
    └── safetool-pdf.iss                   # Inno Setup installer script
```

#### Subdirectory Purposes

**`packaging/ci/`** - CI/CD Configuration

Contains workflow templates and CI-specific configuration:

- `build.yml` - Template for GitHub Actions build workflow
- Used as reference for CI pipeline configuration
- Not directly executed locally

**`packaging/linux/`** - Linux Packaging

Contains Linux-specific packaging files:

- **`appimage/`** - AppImage packaging
  - `build_appimage.sh` - Creates AppImage from PyInstaller output
  - `AppRun` - Entry point script that sets up environment and launches app
  - `*.desktop` - Desktop entry file (application metadata for desktop environments)
  - `*.metainfo.xml` - AppStream metadata (for software centers)
  
- **`flatpak/`** - Flatpak packaging (future)
  - `*.metainfo.xml` - Flatpak metadata
  - Not currently used in local builds

**`packaging/macos/`** - macOS Packaging

Contains macOS-specific packaging files:

- `build_macos.sh` - Creates .app bundle and DMG from PyInstaller output
- `Info.plist` - macOS app bundle metadata (bundle ID, version, icon, etc.)

**`packaging/nuitka/`** - Alternative Build System

Contains Nuitka build configuration (alternative to PyInstaller):

- `build.sh` - Nuitka build script
- Not used by default (PyInstaller is the primary build system)
- Experimental/alternative approach

**`packaging/pyinstaller/`** - PyInstaller Configuration

Contains the PyInstaller specification file:

- `safetool-pdf.spec` - Controls what gets bundled by PyInstaller
- Defines entry point, data files, hidden imports, exclusions
- Platform-specific settings (icons, bundle type)
- **This is the most important file for customizing the build**

**`packaging/scripts/`** - Build Utility Scripts

Contains helper scripts used during the build process:

- `download_ghostscript.py` - Downloads vendored Ghostscript for Windows/macOS
- Executed automatically by `build.py` or manually
- Handles platform detection and download URLs

**`packaging/vendor/`** - Vendored Dependencies

Contains third-party binaries bundled with the application:

- `gs/` - Ghostscript binaries (downloaded, not in Git)
  - `bin/gswin64c.exe` - Windows Ghostscript executable
  - `bin/gs` - macOS/Linux Ghostscript executable
- `.gitkeep` - Keeps the directory in Git (actual binaries are gitignored)
- Only used on Windows/macOS (Linux uses system Ghostscript)

**`packaging/windows/`** - Windows Packaging

Contains Windows-specific packaging files:

- `build_windows.bat` - Creates Windows installer from PyInstaller output
- `safetool-pdf.iss` - Inno Setup script (installer configuration)
  - Defines installation directory, shortcuts, registry keys
  - Configures installer UI and behavior

#### File Type Relationships

**Build Flow:**

```
1. PyInstaller (.spec) → Bundled executable directory
2. Platform script (.sh/.bat) → Distribution package
3. Metadata files (.desktop/.plist/.iss) → Embedded in package
4. Assets (icons) → Copied to appropriate locations
```

**Relationship Diagram:**

```
safetool-pdf.spec (PyInstaller)
    ↓
dist/safetool-pdf/ (Bundled app)
    ↓
    ├─→ build_appimage.sh + AppRun + .desktop + .metainfo.xml → AppImage
    ├─→ build_macos.sh + Info.plist → .app bundle → DMG
    └─→ build_windows.bat + safetool-pdf.iss → Installer .exe
```

#### Metadata File Locations

**Linux Desktop Entry (`.desktop`)**

- **Source:** `packaging/linux/appimage/org.safetoolhub.safetoolpdf.desktop`
- **Purpose:** Defines application name, icon, categories, MIME types
- **Used by:** AppImage, .deb, .rpm packages
- **Installed to:** `/usr/share/applications/` (system packages)
- **Format:** INI-style key-value pairs

**Example:**
```ini
[Desktop Entry]
Name=SafeTool PDF
Comment=PDF optimization tool
Exec=safetool-pdf-desktop
Icon=org.safetoolhub.safetoolpdf
Type=Application
Categories=Office;Utility;
MimeType=application/pdf;
```

**macOS Info.plist**

- **Source:** `packaging/macos/Info.plist`
- **Purpose:** Defines bundle ID, version, icon, supported file types
- **Used by:** .app bundle, DMG
- **Location in bundle:** `SafeToolPDF.app/Contents/Info.plist`
- **Format:** XML property list

**Example:**
```xml
<key>CFBundleName</key>
<string>SafeTool PDF</string>
<key>CFBundleIdentifier</key>
<string>org.safetoolhub.SafeToolPDF</string>
<key>CFBundleVersion</key>
<string>0.1.0</string>
```

**AppStream Metadata (`.metainfo.xml`)**

- **Source:** `packaging/linux/appimage/org.safetoolhub.safetoolpdf.metainfo.xml`
- **Purpose:** Provides rich metadata for software centers (GNOME Software, KDE Discover)
- **Used by:** AppImage, Flatpak
- **Contains:** Description, screenshots, release notes, developer info
- **Format:** XML

**Windows Inno Setup Script (`.iss`)**

- **Source:** `packaging/windows/safetool-pdf.iss`
- **Purpose:** Defines installer behavior, shortcuts, registry keys
- **Used by:** Windows installer creation
- **Compiled by:** ISCC.exe (Inno Setup Compiler)
- **Format:** Inno Setup scripting language

**Example:**
```ini
[Setup]
AppName=SafeTool PDF
AppVersion=0.1.0
DefaultDirName={pf}\SafeTool PDF
DefaultGroupName=SafeTool PDF

[Files]
Source: "dist\safetool-pdf\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\SafeTool PDF"; Filename: "{app}\safetool-pdf-desktop.exe"
```

#### Asset Locations

**Application Icons**

Icons are stored in the `assets/` directory and used by different packaging formats:

| Platform | Icon Format | Source Location | Destination |
|----------|-------------|-----------------|-------------|
| Linux | PNG (512x512) | `assets/icon.png` | AppImage, .deb, .rpm |
| macOS | ICNS | `assets/SafeToolPDF.icns` | .app bundle Resources/ |
| Windows | ICO | `assets/icon.ico` | Embedded in .exe |

**Icon Usage:**

- **PyInstaller:** Embeds icon in executable (Windows/macOS)
- **AppImage:** Copies icon to AppDir structure
- **.deb/.rpm:** Installs icon to `/usr/share/icons/`
- **.app bundle:** Copies icon to `Contents/Resources/`
- **Inno Setup:** Uses icon for installer and shortcuts

**Other Assets:**

- **Application assets:** `assets/` → Bundled by PyInstaller → `dist/safetool-pdf/assets/`
- **Translations:** `i18n/` → Bundled by PyInstaller → `dist/safetool-pdf/i18n/`
- **License:** `LICENSE` → Bundled by PyInstaller → `dist/safetool-pdf/LICENSE`
- **Config:** `config.py` → Bundled by PyInstaller → `dist/safetool-pdf/config.py`

#### Customizing the Structure

**Adding a new packaging format:**

1. Create a new subdirectory: `packaging/newformat/`
2. Add build script: `packaging/newformat/build_newformat.sh`
3. Add metadata files as needed
4. Update `dev-tools/build.py` to call your script
5. Test the new format

**Example: Adding Snap packaging**

```bash
# Create directory
mkdir -p packaging/linux/snap/

# Create snapcraft.yaml
cat > packaging/linux/snap/snapcraft.yaml << EOF
name: safetool-pdf
version: '0.1.0'
summary: PDF optimization tool
description: |
  SafeTool PDF is a desktop application for optimizing PDF files.

base: core22
confinement: strict
grade: stable

apps:
  safetool-pdf:
    command: bin/safetool-pdf-desktop
    plugs: [home, desktop, desktop-legacy]

parts:
  safetool-pdf:
    plugin: dump
    source: ../../dist/safetool-pdf/
    organize:
      '*': bin/
EOF

# Create build script
cat > packaging/linux/snap/build_snap.sh << 'EOF'
#!/bin/bash
set -e

# Verify PyInstaller output
if [ ! -d "dist/safetool-pdf" ]; then
    echo "Error: PyInstaller dist not found"
    exit 1
fi

# Build snap
cd packaging/linux/snap/
snapcraft

# Move snap to dist/
mv *.snap ../../../dist/
EOF

chmod +x packaging/linux/snap/build_snap.sh
```

---

### 9.3 Customizing Build Scripts

This subsection provides examples of common customizations to the build process, including modifying versions, adding files, changing icons, and adjusting build behavior.

#### Changing Application Version

The application version is defined in `config.py` and can be overridden with the `APP_VERSION` environment variable.

**Method 1: Edit config.py**

```python
# config.py
APP_VERSION = "1.2.0"  # Change this line
APP_NAME = "SafeTool PDF"
```

After changing, rebuild:

```bash
python dev-tools/build.py
```

**Method 2: Use environment variable (temporary)**

```bash
# Linux/macOS
export APP_VERSION=1.2.0
python dev-tools/build.py

# Or inline
APP_VERSION=1.2.0 python dev-tools/build.py

# Windows
set APP_VERSION=1.2.0
python dev-tools\build.py
```

**Method 3: Modify PyInstaller spec file**

You can hardcode the version in the spec file:

```python
# packaging/pyinstaller/safetool-pdf.spec

# Add at the top
import os
version = os.environ.get('APP_VERSION', '1.2.0')  # Default to 1.2.0

# Use in Analysis
a = Analysis(
    ['safetool_pdf_desktop/app.py'],
    ...
)

# Use in EXE (Windows)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='safetool-pdf-desktop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=version,  # Add version here
)
```

#### Adding Hidden Imports

If PyInstaller misses a module, add it to the `hiddenimports` list in the spec file.

**Edit `packaging/pyinstaller/safetool-pdf.spec`:**

```python
a = Analysis(
    ['safetool_pdf_desktop/app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('i18n', 'i18n'),
        ('LICENSE', '.'),
        ('config.py', '.'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'pikepdf',
        'fitz',
        'PIL',
        'qtawesome',
        # Add your custom imports here
        'my_custom_module',
        'another_module.submodule',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'test',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
```

**Rebuild:**

```bash
python -m PyInstaller packaging/pyinstaller/safetool-pdf.spec
```

#### Adding Data Files

To include additional files in the bundle, add them to the `datas` list.

**Edit `packaging/pyinstaller/safetool-pdf.spec`:**

```python
a = Analysis(
    ['safetool_pdf_desktop/app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('i18n', 'i18n'),
        ('LICENSE', '.'),
        ('config.py', '.'),
        # Add custom data files
        ('docs/', 'docs'),                    # Include entire docs/ directory
        ('README.md', '.'),                   # Include README in root
        ('custom_config.json', 'config'),     # Include in config/ subdirectory
    ],
    hiddenimports=[...],
    ...
)
```

**Format:** `(source_path, destination_path_in_bundle)`

**Examples:**

```python
# Include a single file in root
('myfile.txt', '.'),

# Include a single file in a subdirectory
('myfile.txt', 'data'),

# Include entire directory
('mydir/', 'mydir'),

# Include directory contents without parent directory
('mydir/*', 'data'),
```

**Rebuild:**

```bash
python -m PyInstaller packaging/pyinstaller/safetool-pdf.spec
```
