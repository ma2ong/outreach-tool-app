# WhatsApp Web batch sender -- 2026-05-18 Batch 4
# Brazil (3 confirmed mobile) + Mexico (16 prospects, unverified)
# Total: 19 contacts -- within 20/batch limit
#
# HOW TO USE:
#   1. Make sure WhatsApp Web is logged in on Chrome (web.whatsapp.com)
#   2. Run this script in PowerShell
#   3. Each tab opens with pre-filled message -- click SEND in each tab
#   4. A new tab opens every 60 seconds -- don't rush ahead
#   5. Mexico numbers showing "not registered on WhatsApp" = skip & close tab
#   6. After finishing, run: python output\leads\wa_update_batch4.py

$contacts = @(
    # ===== BRAZIL -- confirmed mobile =====
    @{
        country = "Brazil"
        no      = 462
        company = "LED Eart"
        phone   = "5585994324544"
        msg     = "Allen from Shenzhen - LED manufacturer. Panel rental and sales across Ceara for events - what pixel pitch are clients asking for on outdoor stages right now, P3.9 or something tighter?"
    }
    @{
        country = "Brazil"
        no      = 463
        company = "CIA do LED"
        phone   = "5551992314663"
        msg     = "Allen from Shenzhen - LED manufacturer. LED panels plus pyro effects for events in RS and SC is a creative combo. What screen sizes do you typically run for stage backdrops?"
    }
    @{
        country = "Brazil"
        no      = 465
        company = "Projeta Producoes"
        phone   = "5583988648221"
        msg     = "Hi, Allen from Shenzhen - LED manufacturer. Full event production - panels, projection, audio, stage structure - out of Paraiba. What pitch and size do you run for stage LED backdrops?"
    }
    # ===== MEXICO -- unverified, skip if "not on WhatsApp" =====
    @{
        country = "Mexico"
        no      = 131
        company = "RGB Tronics"
        phone   = "528117724695"
        msg     = "Allen from Shenzhen - LED manufacturer. 10+ years in giant LED screen wholesale in Mexico is a long run. What pixel pitch is selling fastest right now - outdoor P4, P6, or bigger?"
    }
    @{
        country = "Mexico"
        no      = 132
        company = "DMX Technologies"
        phone   = "525556622600"
        msg     = "Allen from Shenzhen - LED manufacturer. 10+ years wholesaling large-scale LED screens - what specs are clients requesting most from you right now?"
    }
    @{
        country = "Mexico"
        no      = 133
        company = "iLED Mexico"
        phone   = "528111015015"
        msg     = "Allen from Shenzhen - LED manufacturer. Curved, outdoor, and mobile LED with full engineering support - are clients asking for curved more for indoor retail or outdoor advertising?"
    }
    @{
        country = "Mexico"
        no      = 134
        company = "Medios Mexico"
        phone   = "525552932000"
        msg     = "Allen from Shenzhen - LED manufacturer. LED manufacturing plus outdoor digital advertising - what pitch range do your OOH billboard clients spec most?"
    }
    @{
        country = "Mexico"
        no      = 135
        company = "HPMLED Grupo Vision"
        phone   = "528111585800"
        msg     = "Allen from Shenzhen - LED manufacturer. LED display solutions - what pixel pitch range is moving most for your clients right now?"
    }
    @{
        country = "Mexico"
        no      = 136
        company = "Pixel Window Mexico"
        phone   = "524424564968"
        msg     = "Allen from Shenzhen - LED manufacturer. Offices across CDMX, Queretaro, and Guadalajara - what's driving most business right now, indoor installs, outdoor, or rental?"
    }
    @{
        country = "Mexico"
        no      = 137
        company = "Showco Mexico"
        phone   = "525550009480"
        msg     = "Allen from Shenzhen - LED manufacturer. LED screens plus AV for events - what indoor pixel pitch do clients ask for most on stage events in Mexico?"
    }
    @{
        country = "Mexico"
        no      = 138
        company = "MAX Signage Mexico"
        phone   = "525550213584"
        msg     = "Allen from Shenzhen - LED manufacturer. LED signage in Mexico - what's the split between outdoor advertising and indoor corporate installs for your clients?"
    }
    @{
        country = "Mexico"
        no      = 139
        company = "Luft Screen"
        phone   = "525523353227"
        msg     = "Allen from Shenzhen - LED manufacturer. LED screen solutions in CDMX - are you focused more on events and rental or permanent installs?"
    }
    @{
        country = "Mexico"
        no      = 140
        company = "SAP LED"
        phone   = "524442100824"
        msg     = "Allen from Shenzhen - LED manufacturer. Distributing LED displays in Mexico - what pixel pitch range are clients requesting most right now?"
    }
    @{
        country = "Mexico"
        no      = 141
        company = "Eyecatch Mexico"
        phone   = "525610046498"
        msg     = "Allen from Shenzhen - LED manufacturer. LED display and digital signage in Mexico - more demand from corporate clients or outdoor advertising?"
    }
    @{
        country = "Mexico"
        no      = 142
        company = "MMP Screen"
        phone   = "525554120445"
        msg     = "Allen from Shenzhen - LED manufacturer. LED screen solutions in Mexico - what's more common for your clients, retail signage or large video walls?"
    }
    @{
        country = "Mexico"
        no      = 315
        company = "Fenix-Evolution LED"
        phone   = "524771255013"
        msg     = "Allen from Shenzhen - LED manufacturer. Event LED rental from Leon to CDMX, Guadalajara, Monterrey, and Cancun - what pixel pitch do you run for outdoor stages, P3.9 or tighter?"
    }
    @{
        country = "Mexico"
        no      = 355
        company = "DMX Technologies (large-format)"
        phone   = "525533169827"
        msg     = "Allen from Shenzhen - LED manufacturer. 20+ years making large-format LED for advertising and stadiums - what pitch are stadium clients specifying most right now?"
    }
    @{
        country = "Mexico"
        no      = 356
        company = "HPMLED"
        phone   = "528111580000"
        msg     = "Allen from Shenzhen - LED manufacturer. Indoor/outdoor video walls plus event displays - what's heavier in your order mix right now, permanent installs or rental?"
    }
    @{
        country = "Mexico"
        no      = 357
        company = "Mundo Videowall"
        phone   = "525575838168"
        msg     = "Allen from Shenzhen - LED manufacturer. 15 years integrating video walls for corporate, events, and signage - what indoor pixel pitch do you specify most for corporate installs?"
    }
)

Write-Host ""
Write-Host "=== WhatsApp Batch 4 -- Brazil (3) + Mexico (16) = 19 contacts ===" -ForegroundColor Cyan
Write-Host "One tab opens every 60 seconds. Click SEND in each tab before next one opens." -ForegroundColor Yellow
Write-Host "Mexico numbers showing 'not registered on WhatsApp' -- just close the tab." -ForegroundColor Yellow
Write-Host ""

$sent = @()
$i = 1
foreach ($c in $contacts) {
    $encoded = [System.Uri]::EscapeDataString($c.msg)
    $url = "https://web.whatsapp.com/send?phone=$($c.phone)&text=$encoded"

    Write-Host "[$i/$($contacts.Count)] [$($c.country)] $($c.company)  +$($c.phone)" -ForegroundColor Cyan
    Write-Host "  MSG: $($c.msg.Substring(0, [Math]::Min(80, $c.msg.Length)))..." -ForegroundColor Gray

    Start-Process "chrome" -ArgumentList $url
    $sent += $c.no

    if ($i -lt $contacts.Count) {
        Write-Host "  -- Click SEND, then waiting 60s for next... --" -ForegroundColor DarkYellow
        Start-Sleep -Seconds 60
    }
    $i++
}

Write-Host ""
Write-Host "=== All 19 tabs opened ===" -ForegroundColor Green
Write-Host "After you finish clicking Send in all tabs, run:" -ForegroundColor White
Write-Host "  python output\leads\wa_update_batch4.py" -ForegroundColor Green
Write-Host ""
Write-Host "Pass --exclude <no1,no2,...> to mark specific Mexico numbers as excluded (not on WA)." -ForegroundColor Gray
