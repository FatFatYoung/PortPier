@echo off
chcp 65001 >nul
echo ========================================
echo PortPier Server - Build Script
echo ========================================

echo.
echo [1/4] Cleaning old files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec
echo [OK] Cleaned

echo.
echo [2/4] Installing dependencies...
pip install pyinstaller -q
echo [OK] Dependencies installed

echo.
echo [3/4] Building...
pyinstaller --onefile --windowed --name "portpier_server" ^
    --hidden-import i18n ^
    gui_server.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)
echo [OK] Build complete

echo.
echo [4/4] Copying config templates...
if not exist dist mkdir dist
echo [OK] Config templates ready

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Executable: dist\portpier_server.exe
echo.
echo Usage:
echo 1. Double-click tcp_server.exe
echo 2. Configure server settings
echo 3. Click Start to begin
echo.
echo ========================================

dir dist\portpier_server.exe
echo.
pause
