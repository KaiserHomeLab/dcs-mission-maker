@echo off
rem Stops the app starting at logon.
schtasks /delete /tn "DCS Mission Maker" /f
pause
