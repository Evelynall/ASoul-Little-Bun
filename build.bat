@echo off
chcp 65001 >nul
echo 开始打包桌面宠物...
echo.

REM 检查是否安装了 pyinstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo 正在安装 PyInstaller...
    pip install pyinstaller
)

echo 清理旧的构建文件...
if exist build rmdir /s /q build
if exist dist\ASoul_Little_Bun.exe del /q dist\ASoul_Little_Bun.exe

echo.
echo 开始打包...
pyinstaller build.spec --clean

if errorlevel 1 (
    echo.
    echo 打包失败！
    pause
    exit /b 1
)

echo.
echo 复制资源文件...
if not exist dist\img mkdir dist\img
xcopy /E /I /Y img dist\img

REM 复制全局配置文件（如果存在）
if exist global_config.json copy /Y global_config.json dist\

echo.
echo ========================================
echo 打包完成！
echo 可执行文件位置: dist\ASoul_Little_Bun.exe
echo 资源文件已复制到: dist\img\
echo ========================================
echo.
echo 你可以将 dist 文件夹重命名并分发
pause
