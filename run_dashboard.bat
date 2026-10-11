@echo off
title Smart Traffic Management System Dashboard
cd /d "%~dp0"
echo Starting Smart Traffic Simulator Dashboard...
".venv\Scripts\python.exe" gui_app.py
pause
