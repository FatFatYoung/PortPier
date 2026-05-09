@echo off
chcp 65001 >nul
echo ========================================
echo PortPier Client - Build Script
echo ========================================
echo.

echo [1/4] Cleaning old files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist tcp_client.spec del /q tcp_client.spec
echo [OK] Cleaned

echo.
echo [2/4] Installing dependencies...
pip install pyinstaller -q
echo [OK] Dependencies installed

echo.
echo [3/4] Building...
pyinstaller --onefile --windowed --name "portpier_client" ^
    --hidden-import asyncio ^
    --hidden-import hashlib ^
    --hidden-import base64 ^
    --hidden-import struct ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --hidden-import tkinter.messagebox ^
    --hidden-import tkinter.scrolledtext ^
    --hidden-import i18n ^
    --exclude-module aiohttp ^
    --exclude-module aiohttp_retry ^
    --exclude-module aiohttp_socks ^
    --exclude-module numpy ^
    --exclude-module PIL ^
    --exclude-module pillow ^
    --exclude-module matplotlib ^
    --exclude-module pandas ^
    --exclude-module scipy ^
    --exclude-module PyQt5 ^
    --exclude-module PyQt6 ^
    --exclude-module wx ^
    gui_client.py

if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo [4/4] Copying config templates...
if not exist "dist\client_config.json" (
    echo {> "dist\client_config.json"
    echo   "server_host": "127.0.0.1",>> "dist\client_config.json"
    echo   "server_port": 8024,>> "dist\client_config.json"
    echo   "client_id": "mypc",>> "dist\client_config.json"
    echo   "token": "your_token_here">> "dist\client_config.json"
    echo }>> "dist\client_config.json"
    echo [OK] Created client_config.json
)

if not exist "dist\client_rules.json" (
    echo []> "dist\client_rules.json"
    echo [OK] Created client_rules.json
)

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Executable: dist\portpier_client.exe
echo.
if exist "dist\portpier_client.exe" (
    dir "dist\portpier_client.exe"
)
echo.
echo Usage:
echo 1. Double-click tcp_client.exe
echo 2. Click Settings to configure server
echo 3. Click Rules to add port mapping rules
echo 4. Click Connect to start
echo.
pause
