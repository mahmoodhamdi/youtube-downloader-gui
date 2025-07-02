#!/usr/bin/env python3
"""
Build script for creating executable using PyInstaller
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, description=""):
    """Run a command and handle errors"""
    print(f"\n{'='*50}")
    print(f"Running: {description if description else command}")
    print('='*50)
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Exit code: {e.returncode}")
        print(f"Error output: {e.stderr}")
        return False

def clean_build_dirs():
    """Clean previous build directories"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}...")
            shutil.rmtree(dir_name)

def create_spec_file():
    """Create PyInstaller spec file with custom configuration"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['youtube_downloader.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'queue',
        'threading',
        'json',
        'pathlib',
        'urllib.parse',
        'datetime',
        're',
        'yt_dlp',
        'yt_dlp.extractor',
        'yt_dlp.postprocessor',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='YouTubeDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)
'''
    
    with open('youtube_downloader.spec', 'w') as f:
        f.write(spec_content)
    
    print("Created PyInstaller spec file")

def build_executable():
    """Build the executable using PyInstaller"""
    print("Building executable with PyInstaller...")
    
    # Create spec file
    create_spec_file()
    
    # Build using spec file
    command = "pyinstaller --clean youtube_downloader.spec"
    
    if not run_command(command, "Building executable"):
        return False
    
    # Check if executable was created
    if sys.platform.startswith('win'):
        exe_path = Path('dist/YouTubeDownloader.exe')
    else:
        exe_path = Path('dist/YouTubeDownloader')
    
    if exe_path.exists():
        print(f"\n✅ Executable created successfully: {exe_path.absolute()}")
        print(f"   Size: {exe_path.stat().st_size / (1024*1024):.1f} MB")
        return True
    else:
        print("❌ Executable not found after build")
        return False

def create_installer_script():
    """Create a simple installer script for Windows"""
    if not sys.platform.startswith('win'):
        return
    
    installer_content = '''@echo off
echo YouTube Downloader Installer
echo ============================

set "INSTALL_DIR=%LOCALAPPDATA%\\YouTubeDownloader"

echo Creating installation directory...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo Copying executable...
copy "YouTubeDownloader.exe" "%INSTALL_DIR%\\YouTubeDownloader.exe"

echo Creating desktop shortcut...
set "SHORTCUT=%USERPROFILE%\\Desktop\\YouTube Downloader.lnk"
powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); $Shortcut.TargetPath = '%INSTALL_DIR%\\YouTubeDownloader.exe'; $Shortcut.Save()"

echo.
echo Installation completed!
echo Executable installed to: %INSTALL_DIR%
echo Desktop shortcut created: %SHORTCUT%
echo.
pause
'''
    
    with open('dist/install.bat', 'w') as f:
        f.write(installer_content)
    
    print("Created Windows installer script: dist/install.bat")

def main():
    """Main build function"""
    print("YouTube Downloader GUI - Build Script")
    print("=====================================")
    
    # Check if main file exists
    if not os.path.exists('youtube_downloader.py'):
        print("❌ youtube_downloader.py not found!")
        print("   Make sure you're running this script from the project root directory.")
        sys.exit(1)
    
    # Clean previous builds
    clean_build_dirs()
    
    # Install/upgrade PyInstaller
    print("\nInstalling/upgrading PyInstaller...")
    if not run_command("pip install --upgrade pyinstaller", "Installing PyInstaller"):
        print("❌ Failed to install PyInstaller")
        sys.exit(1)
    
    # Build executable
    if not build_executable():
        print("❌ Build failed!")
        sys.exit(1)
    
    # Create installer for Windows
    create_installer_script()
    
    print("\n" + "="*50)
    print("🎉 BUILD COMPLETED SUCCESSFULLY!")
    print("="*50)
    print(f"Executable location: {Path('dist').absolute()}")
    
    if sys.platform.startswith('win'):
        print("Run 'dist/install.bat' to install the application")
    
    print("\nYou can now distribute the contents of the 'dist' folder.")

if __name__ == "__main__":
    main()