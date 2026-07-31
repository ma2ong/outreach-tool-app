@echo off
chcp 65001 >nul
REM 让工具开机自动在后台运行，不用再手动双击 start.bat。
REM 再次双击本文件 = 重新安装（会覆盖旧设置）。要取消请双击 uninstall_autostart.bat。
cd /d "%~dp0"

if not exist "frontend\dist\index.html" (
  echo [X] 界面还没构建过，请先双击 setup.bat。
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\autostart.ps1" -Root "%~dp0"
pause
