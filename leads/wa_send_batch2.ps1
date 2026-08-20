# WhatsApp Web batch sender — 2026-05-14 Batch 2 (Brazil mobile)
# 每隔 15 秒自动开一个 Chrome 标签页，消息已预填，切换到 Chrome 点 Send 即可

$contacts = @(
    @{ company="The LED";              phone="5511989404332"; msg="Allen here, Shenzhen LED manufacturer. You run the largest LED visual comms operation in Brazil — curious what pixel pitch your distributors are moving most right now. Still P2.5 or has sub-2mm started to come in?" }
    @{ company="Dshow";               phone="5511997144969"; msg="Hi, Allen from Shenzhen — LED panel manufacturer. Running flexible LED alongside standard indoor and outdoor is still rare in Brazil. What's driving your flex inquiries — building facades or event stages?" }
    @{ company="Rangel Panels";       phone="5511999956612"; msg="Allen from Shenzhen, LED manufacturer. 25+ years in LED advertising panels is a long track record. What pitch is your market asking for most on outdoor right now — P4, P6, or are clients pushing tighter?" }
    @{ company="Pantallas Brasil LED"; phone="5511976406060"; msg="Hi, Allen from Shenzhen — we make LED panels. You distribute indoor and outdoor across Brazil — what's the most common spec your customers are asking for on outdoor billboard displays right now?" }
    @{ company="Brasil Som Luz";      phone="554999941829"; msg="Allen from Shenzhen here — LED panel manufacturer. Running LED panels alongside full AV and sound in Santa Catarina is a solid setup. What pitch are you deploying most for outdoor events in the region?" }
    @{ company="Loja do Painel de LED"; phone="5511911516975"; msg="Hi, Allen from Shenzhen — LED manufacturer. You stock P2 through P10 which covers the full range. What's moving fastest for you right now — indoor fine pitch or outdoor?" }
)

Write-Host "=== WhatsApp Batch 2 — Brazil mobile (6 contacts) ===" -ForegroundColor Cyan
Write-Host "Every 15s a new Chrome tab opens — switch to Chrome and click Send" -ForegroundColor Yellow
Write-Host ""

$i = 1
foreach ($c in $contacts) {
    $encoded = [System.Uri]::EscapeDataString($c.msg)
    $url = "https://web.whatsapp.com/send?phone=$($c.phone)&text=$encoded"
    Write-Host "[$i/6] $($c.company)  +$($c.phone)" -ForegroundColor Cyan
    Start-Process "chrome" -ArgumentList $url
    if ($i -lt $contacts.Count) {
        Start-Sleep -Seconds 15
    }
    $i++
}

Write-Host ""
Write-Host "=== All tabs open — click Send in each Chrome tab ===" -ForegroundColor Green
