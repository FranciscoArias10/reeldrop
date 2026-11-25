@echo off
title ReelDrop - Descargador de Reels, Shorts y TikTok
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" pyw app.py 2>nul || py app.py
    exit /b 0
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" pythonw app.py 2>nul || python app.py
    exit /b 0
)

echo [ERROR] No se encontro Python instalado en el sistema.
pause

