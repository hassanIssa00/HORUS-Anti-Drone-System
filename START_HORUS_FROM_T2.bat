@echo off
title HORUS SYSTEM V1 - T2 STABLE
echo [SYSTEM] Initializing HORUS Tactical Dashboard (Shield Shape)...
taskkill /f /im python.exe /t >nul 2>&1
cd /d "c:\Users\hassa\Desktop\New folder (21)\T2\mcdis\dashboard"
start "HORUS_SERVER" python app.py
echo [SYSTEM] Dashboard launched on http://localhost:5001
echo [SYSTEM] You can close this window now.
pause
exit
