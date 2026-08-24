$ErrorActionPreference = 'Stop'

function Assert-LastExit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step 失败（exit $LASTEXITCODE）" }
}

$repo = Split-Path -Parent $PSScriptRoot
$taskName = 'Maxcolor Outreach Tool'

Write-Host "`n===== MCVISUAL 安全部署 =====" -ForegroundColor Cyan
Write-Host "仓库: $repo"

$dirty = git -C $repo status --porcelain
Assert-LastExit '读取 Git 状态'
if ($dirty) {
    Write-Host $dirty -ForegroundColor Yellow
    throw '项目目录有未提交文件。为避免覆盖本机改动，部署已停止。'
}

Write-Host "`n[1/6] 更新 main" -ForegroundColor Green
git -C $repo fetch origin
Assert-LastExit 'git fetch'
git -C $repo switch main
Assert-LastExit 'git switch main'
git -C $repo pull --ff-only origin main
Assert-LastExit 'git pull --ff-only'
$sha = (git -C $repo rev-parse HEAD).Trim()
Assert-LastExit '读取 HEAD'
Write-Host "HEAD: $sha"

Write-Host "`n[2/6] 后端依赖" -ForegroundColor Green
python -m pip install -r "$repo\backend\requirements.txt"
Assert-LastExit 'Python 依赖安装'

Write-Host "`n[3/6] 前端锁定依赖 + 安全审计 + build" -ForegroundColor Green
npm --prefix "$repo\frontend" ci
Assert-LastExit 'npm ci'
npm --prefix "$repo\frontend" run audit:production
Assert-LastExit '生产依赖 audit'
npm --prefix "$repo\frontend" run audit:all
Assert-LastExit '完整依赖 audit'
npm --prefix "$repo\frontend" run build
Assert-LastExit '前端 build'

Write-Host "`n[4/6] 重启本机服务" -ForegroundColor Green
Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 3
Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 12

Write-Host "`n[5/6] 数据恢复边界 + Worker 健康" -ForegroundColor Green
Push-Location "$repo\backend"
try {
    python -c "from app import backup,production_health,runtime; from app.db import connect; from app.main_deps import DB_PATH; b=backup.ensure_daily_backup(DB_PATH); c=connect(DB_PATH); h=production_health.status(c,DB_PATH); r=runtime.status(c); print('BACKUP=',b['status'],' verified=',b['verified'],' date=',b['date']); print('HEALTH=',h['status'],' critical=',h['critical'],' warnings=',h['warnings']); print('WORKER_ACTIVE=',bool(r.get('lease'))); c.close(); raise SystemExit(0 if b.get('verified') and h.get('status') in ('ok','degraded') and r.get('lease') else 2)"
    Assert-LastExit '备份/健康/Worker 验证'
}
finally {
    Pop-Location
}

Write-Host "`n[6/6] 端口验证" -ForegroundColor Green
$portOk = (Test-NetConnection 127.0.0.1 -Port 8000 -WarningAction SilentlyContinue).TcpTestSucceeded
Write-Host "PORT 8000 = $portOk"
if (-not $portOk) { throw '127.0.0.1:8000 未监听，部署验收失败。' }

Write-Host "`n部署完成 ✓" -ForegroundColor Green
Write-Host "版本: $sha"
Write-Host 'Cloudflare Tunnel 配置未修改；浏览器 Ctrl+F5 即可。'
