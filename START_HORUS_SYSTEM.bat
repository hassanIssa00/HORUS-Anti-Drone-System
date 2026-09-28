@echo off
title HORUS ANTI-DRONE SYSTEM - TACTICAL C2
set PROJECT_ROOT=%~dp0
cd /d "%PROJECT_ROOT%"

echo ======================================================================
echo    HORUS (MCDIS) - MULTI-MODAL COUNTER-UAV COMMAND SYSTEM
echo ======================================================================
echo.
echo [1/3] Terminating any existing Python instances...
taskkill /f /im python.exe /t >nul 2>&1

echo [2/3] Initializing HORUS Tactical C2 Server...
start "HORUS_SERVER" python app.py

echo [3/3] Opening Tactical Command Interface...
timeout /t 3 >nul
start http://localhost:5000

echo.
echo System launched. Press any key to stop server processes.
pause
taskkill /f /im python.exe /t >nul 2>&1
