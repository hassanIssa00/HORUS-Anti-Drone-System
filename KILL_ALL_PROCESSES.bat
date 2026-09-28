@echo off
echo [SYSTEM] Closing all Horus and MCDIS processes...
taskkill /F /IM python.exe /T
taskkill /F /IM cmd.exe /FI "WINDOWTITLE eq HORUS_SERVER"
echo [OK] All processes terminated.
pause
