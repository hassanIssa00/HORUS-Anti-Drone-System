@echo off
title HORUS SYSTEM - DIAGNOSTIC TOOL
set PROJECT_ROOT=%~dp0
cd /d "%PROJECT_ROOT%"

echo =======================================================
echo    HORUS SYSTEM DIAGNOSTIC TOOL
echo =======================================================
echo.

echo [1/3] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    pause
    exit /b
)
python --version

echo.
echo [2/3] Checking required libraries...
python -c "import flask, flask_socketio, cv2, ultralytics, numpy, sqlite3" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Missing required libraries. Please run:
    echo pip install flask flask-socketio opencv-python ultralytics numpy
    pause
    exit /b
)
echo [SUCCESS] All core libraries found.

echo.
echo [3/3] Attempting to start app.py directly (to see errors)...
cd /d "%PROJECT_ROOT%\mcdis\dashboard"
python app.py

echo.
echo =======================================================
echo    DIAGNOSTIC COMPLETE
echo =======================================================
pause
