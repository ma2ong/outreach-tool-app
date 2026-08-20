# WhatsApp Web batch sender — 2026-05-14 Batch 1 (Brazil)
# 每隔 15 秒自动开一个 Chrome 标签页，消息已预填，切换到 Chrome 点 Send 即可

$contacts = @(
    @{ company="LedWave";                phone="5511304446091"; msg="B Corp certification in the LED space is a real differentiator with ESG-focused corporate clients — not many suppliers in Brazil can say that. We're a Shenzhen manufacturer, mostly fine-pitch panels for rental and corporate installs. Curious what's driving most of your volume right now — the rental fleet, OOH media, or direct panel sales?" }
    @{ company="Crialed Visual Productions"; phone="5511229100031"; msg="18 years in LED events and productions means you've seen every panel generation come through. We're on the manufacturing side out of Shenzhen — mostly P2.5 to P3.91 for rental setups. What cabinet system are you running for outdoor stages now — aluminum or carbon fiber — and are you seeing demand shift toward lighter builds?" }
    @{ company="LED 10";                  phone="5511211530091"; msg="15 years in LED sales and rental in Sao Paulo means your pipeline covers a wide spec range. We're a Shenzhen-based panel supplier focused on rental and fixed install. What's pulling the most demand right now — indoor fine pitch for corporate installs, or outdoor advertising setups?" }
    @{ company="P1LED / Prime LED";       phone="5511262624690"; msg="15 years in retail and commercial LED with a reseller program means you see what end users actually spec — not just what gets ordered. We're on the manufacturing side in Shenzhen. What pixel pitch is your reseller network moving most of right now, and is indoor fine pitch starting to pull ahead of outdoor?" }
    @{ company="The LED";                 phone="5511989404332"; msg="Leading LED visual communications in Brazil with your own distributor network means you're setting the pace for what the market buys. We manufacture in Shenzhen — fine pitch mostly P1.5 to P2.5. Curious what the Brazilian market is asking for on indoor right now: still P2.5 range, or has sub-2mm started to move?" }
    @{ company="Dshow";                   phone="5511997144969"; msg="Flexible LED alongside standard indoor and outdoor is still a niche in Brazil — not many companies run all three. We're a Shenzhen manufacturer, mostly standard panels but growing into flex. What's driving your flex panel inquiries — building facades, curved event stages, or something else?" }
)

Write-Host "=== WhatsApp Batch 1 — Brazil (6 contacts) ===" -ForegroundColor Cyan
Write-Host "每 15 秒自动开一个标签页，切到 Chrome 点 Send 即可" -ForegroundColor Yellow
Write-Host ""

$i = 1
foreach ($c in $contacts) {
    $encoded = [System.Uri]::EscapeDataString($c.msg)
    $url = "https://web.whatsapp.com/send?phone=$($c.phone)&text=$encoded"
    Write-Host "[$i/6] $($c.company)  +$($c.phone)" -ForegroundColor Cyan
    Start-Process "chrome" -ArgumentList $url
    if ($i -lt $contacts.Count) {
        Write-Host "      等待 15 秒后开下一个..." -ForegroundColor DarkGray
        Start-Sleep -Seconds 15
    }
    $i++
}

Write-Host ""
Write-Host "=== 全部标签页已打开，在 Chrome 里逐一点 Send ===" -ForegroundColor Green
