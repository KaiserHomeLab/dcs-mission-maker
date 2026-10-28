@echo off
rem Builds the Windows app into "dist\DCS Mission Maker\" (and a .zip of it).
rem Needs what setup.bat installs; run setup.bat first.
setlocal
cd /d "%~dp0.."
if not exist .venv\Scripts\python.exe (
  echo Run windows\setup.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python -m pip install --disable-pip-version-check -q -r requirements-build.txt || goto :failed
.venv\Scripts\python -m PyInstaller --noconfirm windows\dcs-mission-maker.spec || goto :failed
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\DCS Mission Maker' -DestinationPath 'dist\DCS-Mission-Maker-windows.zip'" || goto :failed
echo.
echo Built: dist\DCS Mission Maker\DCS Mission Maker.exe
echo   and: dist\DCS-Mission-Maker-windows.zip
pause
exit /b 0

:failed
echo.
echo Build failed: see the messages above.
pause
exit /b 1
