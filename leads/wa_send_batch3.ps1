# WhatsApp Web batch sender -- 2026-05-14 Batch 3
# Business-type targeted messages, pure ASCII only
# Every 15s a new Chrome tab opens -- switch to Chrome and click Send

$contacts = @(
    @{
        company = "NN LED"
        phone   = "5519997626990"
        type    = "rental/events"
        msg     = "Allen from Shenzhen - LED manufacturer. P4 rental for events plus LED robot installs is a creative combo. What outdoor stage sizes are you typically running for events in the Campinas area, and are clients asking for anything tighter than P4 now?"
    }
    @{
        company = "Mundo de LED"
        phone   = "5588996053355"
        type    = "distributor"
        msg     = "Hi, Allen from Shenzhen - LED panel manufacturer. Over 10 years distributing LED in Brazil covers a lot of market cycles. What pitch range is moving fastest for you right now on outdoor displays - P4, P6, or something in between?"
    }
    @{
        company = "LATINLED"
        phone   = "554891152071"
        type    = "wholesale"
        msg     = "Allen here from Shenzhen - LED manufacturer. Wholesale distribution from Florianopolis covering the south region is solid ground. Are your clients mostly buying for outdoor fixed installs or indoor, and what pitch do they ask for most?"
    }
    @{
        company = "All Trading"
        phone   = "5511984770223"
        type    = "importer"
        msg     = "Hi, Allen from Shenzhen - LED manufacturer. On the import and trading side you see what the market is actually buying, not just what gets listed. What specs are your customers requesting most right now - pixel pitch, brightness, or something else?"
    }
)

Write-Host "=== WhatsApp Batch 3 -- Brazil (4 contacts, targeted by business type) ===" -ForegroundColor Cyan
Write-Host "Every 15s a new tab opens. Switch to Chrome and click Send." -ForegroundColor Yellow
Write-Host ""

$i = 1
foreach ($c in $contacts) {
    $encoded = [System.Uri]::EscapeDataString($c.msg)
    $url = "https://web.whatsapp.com/send?phone=$($c.phone)&text=$encoded"
    Write-Host "[$i/$($contacts.Count)] $($c.company)  [$($c.type)]  +$($c.phone)" -ForegroundColor Cyan
    Start-Process "chrome" -ArgumentList $url
    if ($i -lt $contacts.Count) {
        Start-Sleep -Seconds 15
    }
    $i++
}

Write-Host ""
Write-Host "=== All tabs open -- click Send in each Chrome tab ===" -ForegroundColor Green
