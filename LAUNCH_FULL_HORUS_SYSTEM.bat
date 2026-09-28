@echo off
title HORUS SYSTEM - FULL MISSION LAUNCH
set PROJECT_ROOT=%~dp0
cd /d "%PROJECT_ROOT%"

echo [1/4] Terminating existing Python processes...
taskkill /f /im python.exe /t >nul 2>&1

echo [2/4] Starting Electronic Warfare & SIGINT Sensors...
cd /d "%PROJECT_ROOT%\mcdis"
start "HORUS_SENSORS" python run_sensors.py

echo [3/4] Starting HORUS Command Dashboard (Vision Engine)...
cd /d "%PROJECT_ROOT%\mcdis\dashboard"
start "HORUS_SERVER" python app.py

echo [4/4] Opening Tactical Interface...
timeout /t 5 >nul
start http://localhost:5001

echo.
echo =======================================================
echo    HORUS SYSTEM ACTIVE - MISSION READY
echo =======================================================
echo.
pause
