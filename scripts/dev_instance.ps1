# Start a preview server from a worktree, on its own port, that cannot send anything.
#
# The point of the worktrees is that two agents stop overwriting each other's files.
# The danger they introduce is subtler: a second server pointed at the live database
# with its schedulers running would send every customer a second copy of today's email
# and a second DM, because both instances would see the same due queue. The runtime
# lease guards concurrent *workers*, not a second process someone starts by hand.
#
# So every sender is off here. This instance renders the UI and answers reads; the one
# in C:\Users\Administrator\outreach-tool stays the only one that talks to customers.
#
#   .\scripts\dev_instance.ps1 -Port 8010
param([int]$Port = 8010)

$root = Split-Path -Parent $PSScriptRoot
$live = "C:\Users\Administrator\outreach-tool\backend\outreach.db"

if (-not (Test-Path $live)) { Write-Error "找不到主库：$live"; exit 1 }

# Read the same book Allen sees, so the preview shows real rows.
$env:OUTREACH_DB = $live
# Nothing in this process may reach a customer.
$env:OUTREACH_AUTOSEND_SCHEDULER = "0"   # 邮件序列自动发送
$env:OUTREACH_SOCIAL_QUEUE       = "0"   # 社媒私信队列与发送
$env:OUTREACH_AGENT              = "0"   # 自主销售 Agent
$env:OUTREACH_AUTO_POLL          = "0"   # 收信轮询
$env:OUTREACH_AUTO_SCAN          = "0"   # 社媒回复扫描
$env:OUTREACH_AUTO_RECHECK       = "0"   # 官网复检
$env:OUTREACH_AUTO_RESEARCH      = "0"   # 决策人调研

Write-Host "预览实例：$root  →  http://127.0.0.1:$Port"
Write-Host "库：$live（只读使用；发送、Agent、轮询全部关闭）" -ForegroundColor Yellow
Set-Location (Join-Path $root "backend")
python -m uvicorn app.main:app --port $Port
