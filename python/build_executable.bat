@echo off
REM ============================================================================
REM PyInstaller Build Script for Inline Data Analytics Tool
REM ============================================================================

echo.
echo ========================================
echo   Building Inline Data Analytics
echo ========================================
echo.

REM Step 1: Check Python installation
echo [Step 1/6] Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)
echo Python found!
echo.

REM Step 2: Install/Update PyInstaller
echo [Step 2/6] Installing PyInstaller...
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)
echo PyInstaller installed!
echo.

REM Step 3: Install required packages
echo [Step 3/6] Installing dependencies...
python -m pip install --upgrade PyQt5 pandas numpy scipy matplotlib mplcursors openpyxl xlrd nptdms chardet
if errorlevel 1 (
    echo WARNING: Some packages may have failed to install
    echo Press any key to continue anyway...
    pause >nul
)
echo Dependencies installed!
echo.

REM Step 4: Clean previous builds
echo [Step 4/6] Cleaning previous builds...
if exist "build" (
    echo Removing build directory...
    rmdir /s /q build
)
if exist "dist" (
    echo Removing dist directory...
    rmdir /s /q dist
)
if exist "*.spec" (
    echo Keeping spec file...
)
echo Clean complete!
echo.

REM Step 5: Verify spec file exists
echo [Step 5/6] Checking spec file...
if not exist "Inline_Data_Analytics.spec" (
    echo ERROR: Inline_Data_Analytics.spec not found!
    echo Please ensure the .spec file is in the current directory.
    pause
    exit /b 1
)
echo Spec file found!
echo.

REM Step 6: Build executable
echo [Step 6/6] Building executable...
echo This may take several minutes...
echo.
python -m PyInstaller --clean Inline_Data_Analytics.spec
if errorlevel 1 (
    echo.
    echo ========================================
    echo   BUILD FAILED!
    echo ========================================
    echo.
    echo Common issues:
    echo 1. Missing dependencies - run: pip install -r requirements.txt
    echo 2. Incorrect paths in spec file
    echo 3. Missing icons folder
    echo.
    echo Try building with debug mode:
    echo 1. Open Inline_Data_Analytics.spec
    echo 2. Change console=False to console=True
    echo 3. Run this script again
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   BUILD SUCCESSFUL!
echo ========================================
echo.
echo Your executable is located at:
echo   dist\Inline_Data_Analytics.exe
echo.
echo File size:
dir dist\Inline_Data_Analytics.exe | findstr "Inline_Data_Analytics.exe"
echo.
echo You can now:
echo 1. Run the executable directly from: dist\Inline_Data_Analytics.exe
echo 2. Copy it to any location
echo 3. Create a desktop shortcut
echo.
pause
