$ErrorActionPreference = 'Stop'

function Assert-LastExit([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw ("{0} failed (exit {1})" -f $Step, $LASTEXITCODE)
    }
}

$repo = Split-Path -Parent $PSScriptRoot
$taskName = 'Maxcolor Outreach Tool'

Write-Host "`n===== MCVISUAL SAFE DEPLOY =====" -ForegroundColor Cyan
Write-Host "Repo: $repo"

$dirty = git -C $repo status --porcelain
Assert-LastExit 'git status'
if ($dirty) {
    Write-Host $dirty -ForegroundColor Yellow
    throw 'Working tree is not clean. Deployment stopped to protect local changes.'
}

Write-Host "`n[1/6] Update main" -ForegroundColor Green
git -C $repo fetch origin
Assert-LastExit 'git fetch'
git -C $repo switch main
Assert-LastExit 'git switch main'
git -C $repo pull --ff-only origin main
Assert-LastExit 'git pull --ff-only'
$sha = (git -C $repo rev-parse HEAD).Trim()
Assert-LastExit 'git rev-parse HEAD'
Write-Host "HEAD: $sha"

Write-Host "`n[2/6] Backend dependencies" -ForegroundColor Green
python -m pip install -r "$repo\backend\requirements.txt"
Assert-LastExit 'Python dependency install'

Write-Host "`n[3/6] Frontend install, audit, build" -ForegroundColor Green
npm --prefix "$repo\frontend" ci
Assert-LastExit 'npm ci'
npm --prefix "$repo\frontend" run audit:production
Assert-LastExit 'production npm audit'
npm --prefix "$repo\frontend" run audit:all
Assert-LastExit 'full npm audit'
npm --prefix "$repo\frontend" run build
Assert-LastExit 'frontend build'

Write-Host "`n[4/6] Restart local service" -ForegroundColor Green
Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 3
Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 12

Write-Host "`n[5/6] Backup and runtime acceptance" -ForegroundColor Green
Push-Location "$repo\backend"
try {
    python ".\production_acceptance.py"
    Assert-LastExit 'backup/health/worker acceptance'
}
finally {
    Pop-Location
}

Write-Host "`n[6/6] Port acceptance" -ForegroundColor Green
$portOk = (Test-NetConnection 127.0.0.1 -Port 8000 -WarningAction SilentlyContinue).TcpTestSucceeded
Write-Host "PORT 8000 = $portOk"
if (-not $portOk) {
    throw '127.0.0.1:8000 is not listening. Deployment acceptance failed.'
}

Write-Host "`nDEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "Version: $sha"
Write-Host 'Cloudflare Tunnel configuration was not changed. Refresh the browser with Ctrl+F5.'
