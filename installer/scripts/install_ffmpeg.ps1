# FFmpeg Installer Script for YouTube Downloader Pro
# Downloads and installs FFmpeg automatically

param(
    [string]$InstallPath = "$env:LOCALAPPDATA\FFmpeg"
)

$ErrorActionPreference = "Stop"

# Configuration
$FFmpegUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
$TempDir = "$env:TEMP\ffmpeg_install"
$ZipFile = "$TempDir\ffmpeg.zip"

function Write-Status {
    param([string]$Message, [string]$Type = "Info")

    switch ($Type) {
        "Info"    { Write-Host "[INFO] $Message" -ForegroundColor Cyan }
        "Success" { Write-Host "[OK] $Message" -ForegroundColor Green }
        "Warning" { Write-Host "[WARN] $Message" -ForegroundColor Yellow }
        "Error"   { Write-Host "[ERROR] $Message" -ForegroundColor Red }
    }
}

function Test-FFmpeg {
    try {
        $null = & ffmpeg -version 2>&1
        return $true
    } catch {
        return $false
    }
}

function Add-ToPath {
    param([string]$PathToAdd)

    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")

    if ($currentPath -notlike "*$PathToAdd*") {
        $newPath = "$currentPath;$PathToAdd"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        $env:Path = "$env:Path;$PathToAdd"
        Write-Status "Added FFmpeg to user PATH" "Success"
        return $true
    } else {
        Write-Status "FFmpeg already in PATH" "Info"
        return $false
    }
}

function Install-FFmpeg {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor White
    Write-Host "   FFmpeg Installer for YouTube Downloader Pro" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor White
    Write-Host ""

    # Check if already installed
    if (Test-FFmpeg) {
        Write-Status "FFmpeg is already installed and working!" "Success"
        $ffmpegPath = (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source
        Write-Status "Location: $ffmpegPath" "Info"
        return $true
    }

    Write-Status "FFmpeg not found. Starting installation..." "Info"

    # Create temp directory
    if (Test-Path $TempDir) {
        Remove-Item $TempDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

    # Download FFmpeg
    Write-Status "Downloading FFmpeg (this may take a few minutes)..." "Info"

    try {
        # Use TLS 1.2
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

        # Download with progress
        $webClient = New-Object System.Net.WebClient
        $webClient.DownloadFile($FFmpegUrl, $ZipFile)

        Write-Status "Download completed!" "Success"
    } catch {
        Write-Status "Failed to download FFmpeg: $_" "Error"
        Write-Status "Please download manually from: https://ffmpeg.org/download.html" "Warning"
        return $false
    }

    # Extract
    Write-Status "Extracting FFmpeg..." "Info"

    try {
        Expand-Archive -Path $ZipFile -DestinationPath $TempDir -Force
        Write-Status "Extraction completed!" "Success"
    } catch {
        Write-Status "Failed to extract: $_" "Error"
        return $false
    }

    # Find extracted folder
    $extractedFolder = Get-ChildItem -Path $TempDir -Directory | Where-Object { $_.Name -like "ffmpeg-*" } | Select-Object -First 1

    if (-not $extractedFolder) {
        Write-Status "Could not find extracted FFmpeg folder" "Error"
        return $false
    }

    # Create install directory
    if (Test-Path $InstallPath) {
        Remove-Item $InstallPath -Recurse -Force
    }
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null

    # Copy bin folder
    $binSource = Join-Path $extractedFolder.FullName "bin"
    $binDest = Join-Path $InstallPath "bin"

    try {
        Copy-Item -Path $binSource -Destination $binDest -Recurse -Force
        Write-Status "FFmpeg installed to: $InstallPath" "Success"
    } catch {
        Write-Status "Failed to copy files: $_" "Error"
        return $false
    }

    # Add to PATH
    Add-ToPath -PathToAdd $binDest

    # Cleanup
    Write-Status "Cleaning up temporary files..." "Info"
    Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue

    # Verify installation
    Write-Host ""
    Write-Status "Verifying installation..." "Info"

    # Refresh PATH for current session
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")

    if (Test-FFmpeg) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "   FFmpeg installed successfully!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Status "You may need to restart the application for changes to take effect." "Info"
        return $true
    } else {
        Write-Status "FFmpeg installed but not yet in PATH. Please restart your computer." "Warning"
        return $true
    }
}

# Run installation
try {
    $result = Install-FFmpeg
    if ($result) {
        exit 0
    } else {
        exit 1
    }
} catch {
    Write-Status "Installation failed: $_" "Error"
    exit 1
}
