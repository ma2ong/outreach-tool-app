@echo off
REM Launch the outreach tool: start the server and open the dashboard. Double-click to run.
setlocal
cd /d "%~dp0backend"

if not exist "..\frontend\dist\index.html" (
  echo Dashboard not built yet. Please run setup.bat first.
  pause
  exit /b 1
)

echo Starting the outreach tool at http://127.0.0.1:8000 ...
start "outreach-tool-server" cmd /c "python ..\scripts\run_server.py"

REM wait for schema/backup startup, then open only the verified application
python -c "from app.startup import wait_for_outreach; raise SystemExit(0 if wait_for_outreach(30) else 1)"
if errorlevel 1 (
  echo [X] Port 8000 did not start outreach-tool. Check backend\logs\last-crash.txt.
  pause
  exit /b 1
)
start "" "http://127.0.0.1:8000"

echo.
echo The dashboard should now be open in your browser.
echo Keep the "outreach-tool-server" window open while you work.
echo Close that window to stop the tool.
