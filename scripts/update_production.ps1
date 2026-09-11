param([switch]$SkipTests)

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

Write-Host "`n[1/8] Update main" -ForegroundColor Green
git -C $repo fetch origin
Assert-LastExit 'git fetch'
git -C $repo switch main
Assert-LastExit 'git switch main'
git -C $repo pull --ff-only origin main
Assert-LastExit 'git pull --ff-only'
$sha = (git -C $repo rev-parse HEAD).Trim()
Assert-LastExit 'git rev-parse HEAD'
Write-Host "HEAD: $sha"

Write-Host "`n[2/8] Backend dependencies" -ForegroundColor Green
python -m pip install -r "$repo\backend\requirements.txt"
Assert-LastExit 'Python dependency install'

Write-Host "`n[3/8] Frontend install and audit" -ForegroundColor Green
npm --prefix "$reporontend" ci
Assert-LastExit 'npm ci'
npm --prefix "$reporontend" run audit:production
Assert-LastExit 'production npm audit'
npm --prefix "$reporontend" run audit:all
Assert-LastExit 'full npm audit'

# On 2026-09-11 a commit whose tests were red reached production, because every step up
# to here installs and builds but none of them proves anything. One of those failures
# was Korean customers vanishing from the DM queue without an error, in the market this
# product is mostly aimed at. Building is not proving, and vite build does not typecheck
# either. Both gates run before the service is touched, so a red tree stops here with
# production still serving the last known good version.
Write-Host "`n[4/8] Prove it: backend tests and frontend typecheck" -ForegroundColor Green
if ($SkipTests) {
    Write-Host 'SKIPPED by -SkipTests. Nothing below has been proven.' -ForegroundColor Yellow
} else {
    Push-Location "$repoackend"
    python -m pytest -q
    $testExit = $LASTEXITCODE
    Pop-Location
    if ($testExit -ne 0) {
        throw "Backend tests failed (exit $testExit). Nothing was deployed; production still runs the previous version."
    }
    npm --prefix "$reporontend" run typecheck
    Assert-LastExit 'frontend typecheck'
}

Write-Host "`n[5/8] Frontend build" -ForegroundColor Green
npm --prefix "$reporontend" run build
Assert-LastExit 'frontend build'

Write-Host "`n[6/8] Restart local service" -ForegroundColor Green
# The task is configured to restart on failure, so killing its process makes Task
# Scheduler bring a new one up on its own. A blind sleep here then races that restart:
# both processes reach for port 8000, the loser exits with WinError 10048, and the
# deployment fails on a port that a healthy process is holding. So: wait for the port to
# actually be free before starting, and wait for it to actually be taken afterwards.
function Wait-Port8000([bool]$wantListening, [int]$seconds) {
    for ($i = 0; $i -lt $seconds; $i++) {
        $listening = [bool](Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
        if ($listening -eq $wantListening) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -like '*run_server.py*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
if (-not (Wait-Port8000 $false 30)) {
    throw 'Port 8000 is still held after 30s. Something outside this script owns it.'
}
Start-ScheduledTask -TaskName $taskName
# 120s, not 60: on 2026-09-09 the service bound the port a moment after the 60s window
# closed, so a healthy deployment reported 'Service failed to start' and skipped its own
# acceptance step. Waiting longer costs nothing when the service is up: the loop returns
# as soon as the port is taken, and a service that is genuinely dead is still caught.
if (-not (Wait-Port8000 $true 120)) {
    Write-Host 'Service did not bind within 60s. Last lines of the server log:' -ForegroundColor Yellow
    $log = Join-Path $repo ("backend\logs\server-{0:yyyy-MM-dd}.log" -f (Get-Date))
    if (Test-Path $log) { Get-Content $log -Tail 25 | ForEach-Object { Write-Host "  $_" } }
    throw 'Service failed to start.'
}

Write-Host "`n[7/8] Backup and runtime acceptance" -ForegroundColor Green
Push-Location "$repo\backend"
try {
    python ".\production_acceptance.py"
    Assert-LastExit 'backup/health/worker acceptance'
}
finally {
    Pop-Location
}

Write-Host "`n[8/8] Port acceptance" -ForegroundColor Green
$portOk = (Test-NetConnection 127.0.0.1 -Port 8000 -WarningAction SilentlyContinue).TcpTestSucceeded
Write-Host "PORT 8000 = $portOk"
if (-not $portOk) {
    throw '127.0.0.1:8000 is not listening. Deployment acceptance failed.'
}

Write-Host "`nDEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "Version: $sha"
Write-Host 'Cloudflare Tunnel configuration was not changed. Refresh the browser with Ctrl+F5.'
