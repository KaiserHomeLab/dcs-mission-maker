@echo off
rem One-time setup; run it again after updating. Creates .venv, installs the Python
rem packages and downloads the pinned mission scripts, airfield data, fonts and drawings.
setlocal
cd /d "%~dp0.."

py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo Python 3.12 isn't installed. Get it from https://www.python.org/downloads/
  echo ^(keep "py launcher" ticked in the installer^), then run this again.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  echo Creating the Python environment in .venv ...
  py -3.12 -m venv .venv || goto :failed
)
echo Installing Python packages ...
.venv\Scripts\python -m pip install --disable-pip-version-check -q --upgrade pip || goto :failed
.venv\Scripts\python -m pip install --disable-pip-version-check -r requirements.txt || goto :failed
echo Downloading mission scripts, airfield data and fonts ...
.venv\Scripts\python tools\fetch_vendor.py || goto :failed
if not exist drawings\index.json (
  echo Downloading the 3-view drawings. Wikimedia rate-limits, so this takes a few minutes ...
  .venv\Scripts\python tools\fetch_drawings.py drawings.json drawings
)
if not exist .env (
  copy .env.example .env >nul
  echo Created .env from .env.example: open it in Notepad to set your options.
)
echo.
echo Done. Start the app with windows\start.bat
pause
exit /b 0

:failed
echo.
echo Setup failed: see the messages above.
pause
exit /b 1
