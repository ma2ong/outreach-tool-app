@echo off
chcp 65001 >nul
REM 取消开机自动运行（不影响手动双击 start.bat）。
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unregister-ScheduledTask -TaskName 'Maxcolor Outreach Tool' -Confirm:$false; Write-Output '[OK] 已取消开机自启。'"
pause
