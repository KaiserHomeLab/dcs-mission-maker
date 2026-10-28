@echo off
rem Starts the app whenever you log on to this PC (a Task Scheduler task for your user).
schtasks /create /tn "DCS Mission Maker" /tr "\"%~dp0start.bat\"" /sc onlogon /rl limited /f || (pause & exit /b 1)
echo The app now starts when you log on. Undo with autostart-off.bat
pause
