@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "backend\auth_password.txt" (
  echo [X] 未设置访问密码，拒绝上线（公网裸奔 = 客户库对外敞开）。
  echo     请先在 backend\auth_password.txt 里写一行密码，再运行本脚本。
  pause
  exit /b 1
)

if not exist "bin\cloudflared.exe" (
  echo [i] 首次使用：正在下载 cloudflared（Cloudflare 官方隧道客户端，约 40MB）…
  if not exist "bin" mkdir bin
  powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'bin\cloudflared.exe'"
  if not exist "bin\cloudflared.exe" (
    echo [X] 下载失败，请检查网络后重试。
    pause
    exit /b 1
  )
)

echo [i] 启动本地服务（端口 8000）…
start "outreach-tool-server" cmd /c "python scripts\run_server.py"
cd backend
python -c "from app.startup import wait_for_outreach; raise SystemExit(0 if wait_for_outreach(30) else 1)"
if errorlevel 1 (
  cd ..
  echo [X] 端口 8000 未运行 outreach-tool，已停止公网隧道。
  echo     请检查 backend\logs\last-crash.txt。
  pause
  exit /b 1
)
cd ..

echo.
echo ============================================================
echo  下面会打印一个 https://xxxx.trycloudflare.com 网址
echo  = 你的公网网址，手机/同事浏览器打开，输密码即可用。
echo  关闭本窗口 = 下线（本地 127.0.0.1:8000 不受影响）。
echo  免费隧道每次重启网址会变；要固定网址需自备域名。
echo ============================================================
echo.
bin\cloudflared.exe tunnel --url http://127.0.0.1:8000
