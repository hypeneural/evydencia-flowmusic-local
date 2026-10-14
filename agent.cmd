@echo off
setlocal
cd /d "%~dp0"
if /I "%~1"=="test" (
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\doctor.ps1
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\mvp.ps1 -Mode check
)
exit /b %ERRORLEVEL%
