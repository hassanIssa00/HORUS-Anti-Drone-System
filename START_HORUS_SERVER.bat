@echo off
title HORUS SYSTEM V1 - Live Server
color 0A
echo ========================================================
echo   HORUS SYSTEM V1
echo   Starting Backend Server...
echo ========================================================
cd /d "%~dp0"
python app.py
pause
