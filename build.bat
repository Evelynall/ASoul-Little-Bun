@echo off
chcp 65001 >nul
echo Starting packaging desktop pet...
echo.

REM Check if pyinstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo Cleaning old build files...
if exist build rmdir /s /q build
if exist dist\ASoul-Little-Bun.exe del /q dist\ASoul-Little-Bun.exe

echo.
echo Starting packaging...
pyinstaller build.spec --clean

if errorlevel 1 (
    echo.
    echo Packaging failed!
    pause
    exit /b 1
)

echo.
echo Copying resource files...
if not exist dist\img mkdir dist\img
xcopy /E /I /Y img dist\img

REM Copy global config file if exists
if exist global_config.json copy /Y global_config.json dist\

REM Copy version file if exists
if exist version.json copy /Y version.json dist\

echo.
echo ========================================
echo Packaging completed!
echo Executable location: dist\ASoul-Little-Bun.exe
echo Resource files copied to: dist\img\
echo Config files copied: global_config.json, version.json
echo ========================================
echo.
echo You can rename the dist folder and distribute it
pause
