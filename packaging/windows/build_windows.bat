@echo off
REM SafeTool PDF Windows Build Script
REM Copyright (C) 2026 safetoolhub.org
REM License: GPL-3.0-or-later

setlocal enabledelayedexpansion

echo === Building SafeTool PDF for Windows ===

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
set "SPEC_FILE=%PROJECT_ROOT%\packaging\pyinstaller\safetool-pdf.spec"
set "ISS_FILE=%SCRIPT_DIR%safetool-pdf.iss"

REM -----------------------------------------------------------------------
REM Step 1: Build with PyInstaller
REM -----------------------------------------------------------------------
echo.
echo [1/3] Running PyInstaller...
cd /d "%PROJECT_ROOT%"
python -m PyInstaller --clean --noconfirm "%SPEC_FILE%"
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

REM -----------------------------------------------------------------------
REM Step 2: Verify output
REM -----------------------------------------------------------------------
echo.
echo [2/3] Verifying build output...
if not exist "dist\safetool-pdf\safetool-pdf-desktop.exe" (
    echo ERROR: safetool-pdf-desktop.exe not found in dist\safetool-pdf\
    exit /b 1
)
echo Found dist\safetool-pdf\safetool-pdf-desktop.exe

REM -----------------------------------------------------------------------
REM Step 3: Build installer with Inno Setup
REM -----------------------------------------------------------------------
echo.
echo [3/3] Building Inno Setup installer...

set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if defined ISCC (
    echo Using Inno Setup: !ISCC!
    "!ISCC!" "%ISS_FILE%"
    if errorlevel 1 (
        echo ERROR: Inno Setup compilation failed.
        exit /b 1
    )
) else (
    echo WARNING: Inno Setup not found. Skipping installer creation.
    echo Install Inno Setup 6 to build the installer.
)

echo.
echo === Windows build complete ===
echo Output directory: %PROJECT_ROOT%\dist\safetool-pdf\
if exist "%PROJECT_ROOT%\dist\SafeToolPDF-*-setup-x64.exe" (
    echo Installer: %PROJECT_ROOT%\dist\SafeToolPDF-*-setup-x64.exe
)

endlocal
