@echo off
rem Starts DCS Mission Maker on http://localhost:8080 (PORT in .env). Close the window to stop it.
cd /d "%~dp0.."
if not exist .venv\Scripts\python.exe (
  echo Run windows\setup.bat first.
  pause
  exit /b 1
)
title DCS Mission Maker
.venv\Scripts\python -X utf8 -m app
pause
