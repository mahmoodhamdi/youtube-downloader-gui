@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

title YouTube Downloader Pro - Build System v2.0

echo.
echo ████████████████████████████████████████████████████████
echo     YouTube Downloader Pro - Professional Build System
echo                      Version 2.0
echo ████████████████████████████████████████████████████████
echo.

:: Enhanced Configuration
set "APP_NAME=YouTubeDownloaderPro"
set "VERSION=2.0.0"
set "BUILD_DIR=build"
set "RELEASE_DIR=release"
set "DIST_DIR=dist"
set "VENV_DIR=.venv"
set "LOGS_DIR=logs"
set "BACKUP_DIR=backup"

:: Generate clean timestamp (Windows 10/11 compatible)
set "TIMESTAMP="
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do (
    set "MONTH=%%a"
    set "DAY=%%b"
    set "YEAR=%%c"
)
for /f "tokens=1-3 delims=:. " %%a in ('time /t') do (
    set "HOUR=%%a"
    set "MINUTE=%%b"
)
:: Clean up the time format
set "HOUR=%HOUR: =%"
set "MINUTE=%MINUTE: =%"
if "%HOUR:~1%"=="" set "HOUR=0%HOUR%"
if "%MINUTE:~1%"=="" set "MINUTE=0%MINUTE%"
if "%MONTH:~1%"=="" set "MONTH=0%MONTH%"
if "%DAY:~1%"=="" set "DAY=0%DAY%"

set "TIMESTAMP=%YEAR%%MONTH%%DAY%_%HOUR%%MINUTE%"
set "CLIENT_PACKAGE=%APP_NAME%_v%VERSION%_%TIMESTAMP%"
set "LOG_FILE=%LOGS_DIR%\build_%TIMESTAMP%.log"
set "ERROR_LOG=%LOGS_DIR%\error_%TIMESTAMP%.log"

:: Create directories
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

:: Initialize logging
echo =============================================== > "%LOG_FILE%"
echo YouTube Downloader Pro Build Log >> "%LOG_FILE%"
echo Build Started: %DATE% %TIME% >> "%LOG_FILE%"
echo Build Version: %VERSION% >> "%LOG_FILE%"
echo Package Name: %CLIENT_PACKAGE% >> "%LOG_FILE%"
echo =============================================== >> "%LOG_FILE%"

:: Color definitions (Windows 10/11 compatible)
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do (
    set "GREEN=%%a[92m"
    set "RED=%%a[91m"
    set "YELLOW=%%a[93m"
    set "BLUE=%%a[94m"
    set "CYAN=%%a[96m"
    set "WHITE=%%a[97m"
    set "NC=%%a[0m"
)

:: Enhanced logging functions
goto :main

:log_step
echo %BLUE%[%~1]%NC% %~2
echo [%DATE% %TIME%] STEP %~1: %~2 >> "%LOG_FILE%"
exit /b

:log_info
echo %CYAN%[INFO] %~1%NC%
echo [%DATE% %TIME%] INFO: %~1 >> "%LOG_FILE%"
exit /b

:log_success
echo %GREEN%[OK] %~1%NC%
echo [%DATE% %TIME%] SUCCESS: %~1 >> "%LOG_FILE%"
exit /b

:log_warning
echo %YELLOW%[WARN] %~1%NC%
echo [%DATE% %TIME%] WARNING: %~1 >> "%LOG_FILE%"
exit /b

:log_error
echo %RED%[ERROR] %~1%NC%
echo [%DATE% %TIME%] ERROR: %~1 >> "%LOG_FILE%"
echo [%DATE% %TIME%] ERROR: %~1 >> "%ERROR_LOG%"
exit /b

:main

:: Step 1: System Validation
call :log_step "1/11" "Validating System Environment..."
call :log_info "Starting system validation"

:: Check Windows version (simplified)
ver | find "10.0" >nul
if errorlevel 1 (
    ver | find "11.0" >nul
    if errorlevel 1 (
        call :log_error "Unsupported Windows version. Requires Windows 10 or newer"
        goto :cleanup_exit
    )
)
call :log_success "Windows version compatible"

:: Check disk space (simplified)
dir "%SystemDrive%\" | find "bytes free" >nul
if errorlevel 1 (
    call :log_warning "Could not check disk space"
) else (
    call :log_success "Disk space check passed"
)

:: Step 2: Python Validation
call :log_step "2/11" "Validating Python Installation..."
call :log_info "Checking Python installation"

python --version >nul 2>&1
if errorlevel 1 (
    call :log_error "Python not found. Please install Python 3.10 or newer"
    call :log_error "Download from: https://www.python.org/downloads/"
    goto :cleanup_exit
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%i"
call :log_success "Python %PYTHON_VERSION% is available"

:: Step 3: Source Files Validation
call :log_step "3/11" "Verifying Source Files..."
call :log_info "Checking required source files"

set "MISSING_FILES=0"
for %%f in (main.py requirements.txt) do (
    if not exist "%%f" (
        call :log_error "Missing required file: %%f"
        set "MISSING_FILES=1"
    ) else (
        call :log_success "Found %%f"
    )
)

if not exist "src" (
    call :log_error "Missing src directory"
    set "MISSING_FILES=1"
) else (
    call :log_success "Found src directory"
)

if !MISSING_FILES! equ 1 (
    call :log_error "Missing source files detected"
    goto :cleanup_exit
)

:: Step 4: Clean Environment
call :log_step "4/11" "Preparing Build Environment..."
call :log_info "Cleaning workspace"

:: Backup existing release
if exist "%RELEASE_DIR%" (
    call :log_info "Creating backup"
    if exist "%BACKUP_DIR%\release_backup" rmdir /s /q "%BACKUP_DIR%\release_backup" 2>nul
    move "%RELEASE_DIR%" "%BACKUP_DIR%\release_backup" >nul 2>&1
)

:: Clean build directories
for %%d in ("%BUILD_DIR%" "%RELEASE_DIR%" "%DIST_DIR%" "%VENV_DIR%") do (
    if exist "%%~d" (
        rmdir /s /q "%%~d" 2>nul
    )
)

:: Clean temporary files
del /q *.spec 2>nul
for /d %%d in (__pycache__) do rmdir /s /q "%%d" 2>nul

call :log_success "Workspace cleaned"

:: Step 5: Create Build Structure
call :log_step "5/11" "Creating Build Structure..."
call :log_info "Creating directories"

mkdir "%BUILD_DIR%" "%RELEASE_DIR%" "%DIST_DIR%" "%VENV_DIR%" 2>nul

call :log_success "Build structure created"

:: Step 6: Virtual Environment
call :log_step "6/11" "Creating Virtual Environment..."
call :log_info "Setting up Python virtual environment"

python -m venv "%VENV_DIR%" --clear
if errorlevel 1 (
    call :log_error "Virtual environment creation failed"
    goto :cleanup_exit
)
call :log_success "Virtual environment created"

:: Step 7: Activate Environment
call :log_step "7/11" "Activating Virtual Environment..."
call :log_info "Activating environment"

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    call :log_error "Activation script not found"
    goto :cleanup_exit
)

call "%VENV_DIR%\Scripts\activate.bat"
call :log_success "Virtual environment activated"

:: Step 8: Upgrade Tools
call :log_step "8/11" "Upgrading Build Tools..."
call :log_info "Upgrading pip and tools"

python -m pip install --upgrade pip setuptools wheel --quiet >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    call :log_warning "Tool upgrade had issues"
) else (
    call :log_success "Tools upgraded"
)

:: Install PyInstaller
pip install pyinstaller --quiet >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    call :log_error "PyInstaller installation failed"
    goto :cleanup_exit
)
call :log_success "PyInstaller installed"

:: Step 9: Install Dependencies
call :log_step "9/11" "Installing Dependencies..."
call :log_info "Installing application dependencies"

if exist "requirements.txt" (
    pip install -r requirements.txt --quiet >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        call :log_warning "Trying alternative installation..."
        pip install --user -r requirements.txt --quiet >> "%LOG_FILE%" 2>&1
        if errorlevel 1 (
            call :log_error "Dependency installation failed"
            goto :cleanup_exit
        )
    )
    call :log_success "Dependencies installed"
)

:: Step 10: Build Application
call :log_step "10/11" "Building Application..."
call :log_info "Starting build process"

:: Create version file
echo VERSION = "%VERSION%" > src\version.py
echo BUILD_DATE = "%DATE% %TIME%" >> src\version.py
call :log_success "Version file created"

:: Build command
call :log_info "Executing PyInstaller build..."

pyinstaller --noconfirm --onedir --windowed ^
    --name "%APP_NAME%" ^
    --distpath "%DIST_DIR%" ^
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
    main.py >> "%LOG_FILE%" 2>&1

if errorlevel 1 (
    call :log_warning "Advanced build failed, trying simple build..."

    :: Fallback build
    pyinstaller --onefile --windowed --name "%APP_NAME%" --distpath "%DIST_DIR%" main.py >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        call :log_error "All build attempts failed"
        goto :cleanup_exit
    )
    call :log_warning "Simple build completed"
) else (
    call :log_success "Build completed successfully"
)

:: Verify executable
if not exist "%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe" (
    if not exist "%DIST_DIR%\%APP_NAME%.exe" (
        call :log_error "Executable not found!"
        goto :cleanup_exit
    )
)

call :log_success "Executable created successfully"

:: Step 11: Create Package
call :log_step "11/11" "Creating Distribution Package..."
call :log_info "Packaging application"

set "PKG_DIR=%RELEASE_DIR%\%CLIENT_PACKAGE%"
mkdir "%PKG_DIR%" "%PKG_DIR%\bin" "%PKG_DIR%\docs" 2>nul

:: Copy executable (handle both onedir and onefile builds)
if exist "%DIST_DIR%\%APP_NAME%\%APP_NAME%.exe" (
    xcopy "%DIST_DIR%\%APP_NAME%\*" "%PKG_DIR%\bin\" /E /I /Q >nul 2>&1
) else (
    copy "%DIST_DIR%\%APP_NAME%.exe" "%PKG_DIR%\bin\" >nul 2>&1
)

if errorlevel 1 (
    call :log_error "Failed to copy executable"
    goto :cleanup_exit
)
call :log_success "Executable copied to package"

:: Copy additional files
if exist "LICENSE" copy "LICENSE" "%PKG_DIR%\docs\" >nul 2>&1
if exist "README.md" copy "README.md" "%PKG_DIR%\docs\" >nul 2>&1

:: Create launcher
echo @echo off > "%PKG_DIR%\%APP_NAME%.bat"
echo chcp 65001 ^>nul >> "%PKG_DIR%\%APP_NAME%.bat"
echo title %APP_NAME% v%VERSION% >> "%PKG_DIR%\%APP_NAME%.bat"
echo echo Starting YouTube Downloader Pro... >> "%PKG_DIR%\%APP_NAME%.bat"
echo cd /d "%%~dp0" >> "%PKG_DIR%\%APP_NAME%.bat"
echo if exist "bin\%APP_NAME%.exe" ( >> "%PKG_DIR%\%APP_NAME%.bat"
echo     bin\%APP_NAME%.exe >> "%PKG_DIR%\%APP_NAME%.bat"
echo ) else ( >> "%PKG_DIR%\%APP_NAME%.bat"
echo     bin\%APP_NAME%\%APP_NAME%.exe >> "%PKG_DIR%\%APP_NAME%.bat"
echo ) >> "%PKG_DIR%\%APP_NAME%.bat"
echo if errorlevel 1 pause >> "%PKG_DIR%\%APP_NAME%.bat"

call :log_success "Launcher created"

:: Create documentation
echo # %APP_NAME% v%VERSION% > "%PKG_DIR%\docs\INSTALL.md"
echo. >> "%PKG_DIR%\docs\INSTALL.md"
echo Built on: %DATE% %TIME% >> "%PKG_DIR%\docs\INSTALL.md"
echo Python Version: %PYTHON_VERSION% >> "%PKG_DIR%\docs\INSTALL.md"
echo. >> "%PKG_DIR%\docs\INSTALL.md"
echo ## Installation >> "%PKG_DIR%\docs\INSTALL.md"
echo 1. Extract the ZIP package >> "%PKG_DIR%\docs\INSTALL.md"
echo 2. Run %APP_NAME%.bat to launch >> "%PKG_DIR%\docs\INSTALL.md"
echo. >> "%PKG_DIR%\docs\INSTALL.md"
echo ## Requirements >> "%PKG_DIR%\docs\INSTALL.md"
echo - Windows 10 or newer >> "%PKG_DIR%\docs\INSTALL.md"
echo - FFmpeg (optional, for best quality) >> "%PKG_DIR%\docs\INSTALL.md"

:: Create ZIP
call :log_info "Creating ZIP package"
powershell -Command "Compress-Archive -Path '%PKG_DIR%' -DestinationPath '%RELEASE_DIR%\%CLIENT_PACKAGE%.zip' -Force" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    call :log_error "ZIP creation failed"
    goto :cleanup_exit
)

call :log_success "ZIP package created"

:: Generate checksum
certutil -hashfile "%RELEASE_DIR%\%CLIENT_PACKAGE%.zip" SHA256 > "%RELEASE_DIR%\%CLIENT_PACKAGE%.sha256" 2>nul

:: Success report
echo.
echo %GREEN%████████████████████████████████████████████████████████
echo                BUILD COMPLETED SUCCESSFULLY!
echo ████████████████████████████████████████████████████████%NC%
echo.
echo %WHITE%Package Details:%NC%
echo %CYAN%   Application:%NC% %APP_NAME% v%VERSION%
echo %CYAN%   Package:%NC% %CLIENT_PACKAGE%.zip
echo %CYAN%   Location:%NC% %RELEASE_DIR%\
echo.
echo %WHITE%Package Contents:%NC%
echo %CYAN%   bin\%NC% - Application executable
echo %CYAN%   %APP_NAME%.bat%NC% - Launcher
echo %CYAN%   docs\%NC% - Documentation
echo.
echo %WHITE%Next Steps:%NC%
echo %YELLOW%   1.%NC% Extract %CLIENT_PACKAGE%.zip
echo %YELLOW%   2.%NC% Run %APP_NAME%.bat to launch
echo.

if exist "%RELEASE_DIR%\%CLIENT_PACKAGE%.sha256" (
    echo %WHITE%SHA256 Checksum:%NC%
    type "%RELEASE_DIR%\%CLIENT_PACKAGE%.sha256"
    echo.
)

echo %WHITE%Build Log:%NC% %LOG_FILE%
goto :end

:cleanup_exit
echo.
echo %RED%████████████████████████████████████████████████████████
echo                    BUILD FAILED!
echo ████████████████████████████████████████████████████████%NC%
echo.
echo %WHITE%Troubleshooting:%NC%
echo %YELLOW%   - Check build log:%NC% %LOG_FILE%
if exist "%ERROR_LOG%" (
    echo %YELLOW%   - Check error log:%NC% %ERROR_LOG%
)
echo %YELLOW%   - Ensure all source files exist%NC%
echo %YELLOW%   - Verify Python installation%NC%
echo %YELLOW%   - Check internet connection%NC%
echo %YELLOW%   - Run as Administrator%NC%
echo.
exit /b 1

:end
echo %GREEN%Press any key to exit...%NC%
pause >nul
exit /b 0
