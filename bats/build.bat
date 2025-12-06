@echo off
REM YouTube Downloader Pro Build Script
REM This script builds the application for distribution

setlocal enabledelayedexpansion

echo ========================================
echo   YouTube Downloader Pro Build Script
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)

REM Set version
set VERSION=2.0.0
if not "%1"=="" set VERSION=%1

echo Building version: %VERSION%
echo.

REM Create/update version file
if not exist "src" mkdir src
echo VERSION = "%VERSION%" > src\version.py
echo BUILD_DATE = "%date% %time%" >> src\version.py

REM Install dependencies
echo [1/5] Installing dependencies...
python -m pip install pyinstaller -q
python -m pip install -r requirements.txt -q

REM Clean previous builds
echo [2/5] Cleaning previous builds...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

REM Build with PyInstaller
echo [3/5] Building with PyInstaller...
python -m PyInstaller --noconfirm --onedir --windowed ^
    --name "YouTubeDownloaderPro" ^
    --add-data "src;src" ^
    --hidden-import yt_dlp ^
    --hidden-import PIL ^
    --hidden-import PIL._tkinter_finder ^
    --hidden-import requests ^
    --hidden-import urllib3 ^
    --hidden-import certifi ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --hidden-import tkinter.filedialog ^
    --hidden-import tkinter.messagebox ^
    --collect-all yt_dlp ^
    main.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    exit /b 1
)

REM Copy additional files
echo [4/5] Copying additional files...
if exist "LICENSE" copy LICENSE dist\YouTubeDownloaderPro\ >nul 2>&1
if exist "README.md" copy README.md dist\YouTubeDownloaderPro\ >nul 2>&1

REM Create portable zip
echo [5/5] Creating portable archive...
powershell -Command "Compress-Archive -Path 'dist\YouTubeDownloaderPro\*' -DestinationPath 'dist\YouTubeDownloaderPro-%VERSION%-portable.zip' -Force"

echo.
echo ========================================
echo   Build Complete!
echo ========================================
echo.
echo Output files:
echo   - dist\YouTubeDownloaderPro\           (Application folder)
echo   - dist\YouTubeDownloaderPro-%VERSION%-portable.zip (Portable archive)
echo.
echo To create installer, run:
echo   bats\build_installer.bat %VERSION%
echo.

endlocal
