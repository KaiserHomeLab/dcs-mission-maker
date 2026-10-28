@echo off
rem Builds the Windows app into "dist\DCS Mission Maker\", a .zip of it and, with Inno Setup 6
rem installed, the installer.
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
for /f %%v in ('.venv\Scripts\python -c "import app; print(app.__version__)"') do set VERSION=%%v
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\DCS Mission Maker' -DestinationPath 'dist\DCS-Mission-Maker-%VERSION%-windows.zip'" || goto :failed
echo.
echo Built: dist\DCS Mission Maker\DCS Mission Maker.exe
echo   and: dist\DCS-Mission-Maker-%VERSION%-windows.zip
set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if exist "%ISCC%" (
  "%ISCC%" /Q /DAppVersion=%VERSION% windows\installer.iss || goto :failed
  echo   and: dist\DCS-Mission-Maker-Setup-%VERSION%.exe
) else (
  echo For the installer too, install Inno Setup 6 from https://jrsoftware.org/isinfo.php and run this again.
)
pause
exit /b 0

:failed
echo.
echo Build failed: see the messages above.
pause
exit /b 1
