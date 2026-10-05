@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   Inline Data Analytics - C++ Build Script
echo ============================================================
echo.

:: ---- Configuration ----
set "QT_DIR=C:\Qt\6.11.1\msvc2022_64"
set "QT_CMAKE=C:\Qt\Tools\CMake_64\bin\cmake.exe"
set "QT_NINJA=C:\Qt\Tools\Ninja\ninja.exe"
set "VCVARSALL=C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
set "SRC_DIR=%~dp0."
set "BUILD_DIR=%~dp0build"
set "DIST_DIR=%~dp0dist\InlineDataAnalytics"

:: ---- Check prerequisites ----
if not exist "%QT_DIR%\bin\windeployqt6.exe" goto :noqt
goto :qtok
:noqt
echo ERROR: Qt not found at %QT_DIR%
echo Please edit this script and set QT_DIR to your Qt MSVC installation.
pause
exit /b 1
:qtok

if not exist "%VCVARSALL%" goto :novs
goto :vsok
:novs
echo ERROR: Visual Studio Build Tools not found at:
echo   %VCVARSALL%
echo Please install VS Build Tools or edit VCVARSALL in this script.
pause
exit /b 1
:vsok

:: ---- Setup MSVC environment ----
echo [1/5] Setting up MSVC compiler environment...
call "%VCVARSALL%" amd64
if errorlevel 1 goto :vcfail
goto :vcok
:vcfail
echo ERROR: Failed to set up MSVC environment.
pause
exit /b 1
:vcok

:: ---- Configure with CMake ----
echo.
echo [2/5] Configuring project with CMake...
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

"%QT_CMAKE%" -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "Ninja" -DCMAKE_BUILD_TYPE=Release -DCMAKE_MAKE_PROGRAM="%QT_NINJA%" -DCMAKE_PREFIX_PATH="%QT_DIR%" -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl

if errorlevel 1 goto :cmakefail
goto :cmakeok
:cmakefail
echo.
echo ERROR: CMake configuration failed.
pause
exit /b 1
:cmakeok

:: ---- Build ----
echo.
echo [3/5] Building project (Release)...
"%QT_CMAKE%" --build "%BUILD_DIR%" --config Release -- -j%NUMBER_OF_PROCESSORS%

if errorlevel 1 goto :buildfail
goto :buildok
:buildfail
echo.
echo ERROR: Build failed. Check the errors above.
pause
exit /b 1
:buildok

:: ---- Create distribution folder ----
echo.
echo [4/5] Creating distribution package...
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"

:: Copy the executable
copy "%BUILD_DIR%\InlineDataAnalytics.exe" "%DIST_DIR%\" >nul

:: ---- Run windeployqt to gather all Qt DLLs ----
echo.
echo [5/5] Deploying Qt runtime libraries...
"%QT_DIR%\bin\windeployqt6.exe" --release --no-translations --no-system-d3d-compiler --no-opengl-sw "%DIST_DIR%\InlineDataAnalytics.exe"

:: ---- Done ----
echo.
echo ============================================================
echo   BUILD SUCCESSFUL!
echo ============================================================
echo.
echo   Executable: %DIST_DIR%\InlineDataAnalytics.exe
echo.
echo   Distribution folder ready to share:
echo     %DIST_DIR%
echo.
echo   To share with other users:
echo     1. Zip the entire "dist\InlineDataAnalytics" folder
echo     2. Send the zip to the user
echo     3. They extract and run InlineDataAnalytics.exe
echo.
echo ============================================================

pause
