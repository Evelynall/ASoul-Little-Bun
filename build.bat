@echo off
chcp 65001 >nul
echo ========================================
echo ASoul Little Bun - Build Script
echo ========================================
echo.

REM Check if pyinstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo Cleaning old build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo ========================================
echo Step 1/2: Building updater.exe...
echo ========================================
pyinstaller updater.spec --clean

if errorlevel 1 (
    echo.
    echo [ERROR] Updater packaging failed!
    pause
    exit /b 1
)

echo [OK] Updater built successfully

echo.
echo ========================================
echo Step 2/2: Building main program...
echo ========================================
pyinstaller build.spec --clean

if errorlevel 1 (
    echo.
    echo [ERROR] Main program packaging failed!
    pause
    exit /b 1
)

echo [OK] Main program built successfully

echo.
echo Organizing files...

REM Copy img folder
if exist img (
    if not exist dist\img mkdir dist\img
    xcopy /E /I /Y img dist\img >nul
    echo [OK] img folder copied
)

REM Copy version.json
if exist version.json (
    copy /Y version.json dist\ >nul
    echo [OK] version.json copied
)

REM Copy global config file if exists
if exist global_config.json (
    copy /Y global_config.json dist\ >nul
    echo [OK] Config file copied
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Output files:
echo   Main program: dist\ASoul-Little-Bun.exe (~15-25MB)
echo   Updater:      dist\updater.exe (~10-15MB)
echo   Resources:    dist\img\
echo   Version:      dist\version.json
echo.
echo Distribution options:
echo   1. Distribute entire dist folder (recommended)
echo   2. Zip the dist folder for easier distribution
echo.
echo Total size: ~30-50MB (uncompressed)
echo Zip size:   ~15-25MB (compressed)
echo.
pause
