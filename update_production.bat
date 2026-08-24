@echo off
setlocal
net session >nul 2>&1
if %errorlevel% neq 0 (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\update_production.ps1"
set "CODE=%errorlevel%"
echo.
if not "%CODE%"=="0" echo Deployment failed. Please send the last screen to ChatGPT.
pause
exit /b %CODE%
