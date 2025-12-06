@echo off
REM YouTube Downloader Pro Installer Build Script
REM Requires Inno Setup to be installed

setlocal enabledelayedexpansion

echo ========================================
echo   YouTube Downloader Pro Installer Builder
echo ========================================
echo.

REM Set version
set VERSION=2.0.0
if not "%1"=="" set VERSION=%1

echo Building installer for version: %VERSION%
echo.

REM Check if dist folder exists
if not exist "dist\YouTubeDownloaderPro" (
    echo ERROR: Application not built yet. Run build.bat first.
    exit /b 1
)

REM Find Inno Setup
set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
) else (
    echo ERROR: Inno Setup not found. Please install from https://jrsoftware.org/isinfo.php
    exit /b 1
)

echo Found Inno Setup at: %ISCC%
echo.

REM Create output directory
if not exist "installer\Output" mkdir installer\Output

REM Check if setup.iss exists
if not exist "installer\setup.iss" (
    echo ERROR: installer\setup.iss not found.
    exit /b 1
)

REM Build installer
echo Building installer...
"%ISCC%" /DAppVersion="%VERSION%" installer\setup.iss

if errorlevel 1 (
    echo ERROR: Installer build failed
    exit /b 1
)

echo.
echo ========================================
echo   Installer Build Complete!
echo ========================================
echo.
echo Output file:
echo   - installer\Output\YouTubeDownloaderPro-Setup.exe
echo.

endlocal
