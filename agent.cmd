@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\doctor.ps1
exit /b %ERRORLEVEL%
