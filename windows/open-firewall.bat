@echo off
rem Lets other PCs (your friends, Discord links) reach the app on TCP port 8080.
rem Run as administrator. Changed PORT in .env? Change 8080 below too.
net session >nul 2>&1
if errorlevel 1 (
  echo Right-click this file and choose "Run as administrator".
  pause
  exit /b 1
)
netsh advfirewall firewall delete rule name="DCS Mission Maker" >nul 2>&1
netsh advfirewall firewall add rule name="DCS Mission Maker" dir=in action=allow protocol=TCP localport=8080
pause
