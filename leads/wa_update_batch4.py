"""
After running wa_send_batch4.ps1, run this script to update the pipeline.

Usage:
    python output/leads/wa_update_batch4.py
    python output/leads/wa_update_batch4.py --exclude 131,132,133   # mark specific nos as excluded (not on WA)
"""
import json, sys, datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent
PROSPECTS_FILE = BASE / "pipeline/whatsapp/prospects.json"
TODAY = datetime.date.today().isoformat()  # 2026-05-18

# nos sent in batch4 -- Brazil 3 + Mexico 16
BATCH4 = {
    462: "Allen from Shenzhen - LED manufacturer. Panel rental and sales across Ceara for events - what pixel pitch are clients asking for on outdoor stages right now, P3.9 or something tighter?",
    463: "Allen from Shenzhen - LED manufacturer. LED panels plus pyro effects for events in RS and SC is a creative combo. What screen sizes do you typically run for stage backdrops?",
    465: "Hi, Allen from Shenzhen - LED manufacturer. Full event production - panels, projection, audio, stage structure - out of Paraiba. What pitch and size do you run for stage LED backdrops?",
    131: "Allen from Shenzhen - LED manufacturer. 10+ years in giant LED screen wholesale in Mexico is a long run. What pixel pitch is selling fastest right now - outdoor P4, P6, or bigger?",
    132: "Allen from Shenzhen - LED manufacturer. 10+ years wholesaling large-scale LED screens - what specs are clients requesting most from you right now?",
    133: "Allen from Shenzhen - LED manufacturer. Curved, outdoor, and mobile LED with full engineering support - are clients asking for curved more for indoor retail or outdoor advertising?",
    134: "Allen from Shenzhen - LED manufacturer. LED manufacturing plus outdoor digital advertising - what pitch range do your OOH billboard clients spec most?",
    135: "Allen from Shenzhen - LED manufacturer. LED display solutions - what pixel pitch range is moving most for your clients right now?",
    136: "Allen from Shenzhen - LED manufacturer. Offices across CDMX, Queretaro, and Guadalajara - what's driving most business right now, indoor installs, outdoor, or rental?",
    137: "Allen from Shenzhen - LED manufacturer. LED screens plus AV for events - what indoor pixel pitch do clients ask for most on stage events in Mexico?",
    138: "Allen from Shenzhen - LED manufacturer. LED signage in Mexico - what's the split between outdoor advertising and indoor corporate installs for your clients?",
    139: "Allen from Shenzhen - LED manufacturer. LED screen solutions in CDMX - are you focused more on events and rental or permanent installs?",
    140: "Allen from Shenzhen - LED manufacturer. Distributing LED displays in Mexico - what pixel pitch range are clients requesting most right now?",
    141: "Allen from Shenzhen - LED manufacturer. LED display and digital signage in Mexico - more demand from corporate clients or outdoor advertising?",
    142: "Allen from Shenzhen - LED manufacturer. LED screen solutions in Mexico - what's more common for your clients, retail signage or large video walls?",
    315: "Allen from Shenzhen - LED manufacturer. Event LED rental from Leon to CDMX, Guadalajara, Monterrey, and Cancun - what pixel pitch do you run for outdoor stages, P3.9 or tighter?",
    355: "Allen from Shenzhen - LED manufacturer. 20+ years making large-format LED for advertising and stadiums - what pitch are stadium clients specifying most right now?",
    356: "Allen from Shenzhen - LED manufacturer. Indoor/outdoor video walls plus event displays - what's heavier in your order mix right now, permanent installs or rental?",
    357: "Allen from Shenzhen - LED manufacturer. 15 years integrating video walls for corporate, events, and signage - what indoor pixel pitch do you specify most for corporate installs?",
}

# nos to always mark excluded regardless of --exclude flag
# duplicates + confirmed landlines that were not attempted
ALWAYS_EXCLUDE = {
    # duplicates
    358: "duplicate of no:140 (SAP LED, same phone)",
    370: "duplicate of no:315 (Fenix Evolution, same phone)",
    # Brazil landlines
    1: "landline_number",
    2: "landline_number",
    3: "landline_number",
    4: "landline_number",
    7: "landline_number",
    8: "landline_number",
    9: "landline_number",
    10: "landline_number",
    12: "landline_number",
    13: "landline_number",
    15: "landline_number",
    18: "landline_number",
    19: "landline_number",
    20: "landline_number",
    24: "landline_number",
    281: "landline_number",
    282: "landline_number",
    349: "landline_number",
    369: "landline_number",
    381: "landline_number",
    # Chile (all +56 2 prefix = landline)
    41: "landline_number",
    42: "landline_number",
    43: "landline_number",
    44: "landline_number",
    45: "landline_number",
    47: "landline_number",
    284: "landline_number",
    285: "landline_number",
    322: "landline_number",
    # Colombia (601 prefix = Bogota landline)
    35: "landline_number",
    212: "landline_number",
    214: "landline_number",
    218: "landline_number",
    # Peru (landlines)
    72: "landline_number",
    75: "landline_number",
    # Argentina (landlines)
    88: "landline_number",
    89: "landline_number",
    92: "landline_number",
    93: "landline_number",
    95: "landline_number",
    387: "landline_number",
    422: "landline_number",
}

def main():
    # Parse --exclude argument
    exclude_nos = set()
    if "--exclude" in sys.argv:
        idx = sys.argv.index("--exclude")
        if idx + 1 < len(sys.argv):
            exclude_nos = {int(x) for x in sys.argv[idx + 1].split(",")}
            print(f"User-specified excludes: {exclude_nos}")

    with open(PROSPECTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    messaged_count = 0
    excluded_count = 0

    for p in data:
        no = p.get("no")
        if no is None:
            continue

        # Always-exclude (landlines, duplicates)
        if no in ALWAYS_EXCLUDE:
            if p.get("status") != "excluded":
                p["status"] = "excluded"
                p["exclude_reason"] = ALWAYS_EXCLUDE[no]
                excluded_count += 1
            continue

        # User-specified not-on-WA Mexico numbers
        if no in exclude_nos:
            if p.get("status") != "excluded":
                p["status"] = "excluded"
                p["exclude_reason"] = "not_on_whatsapp"
                excluded_count += 1
            continue

        # Mark batch4 as messaged
        if no in BATCH4:
            if p.get("status") != "messaged":
                p["status"] = "messaged"
                p["touch_count"] = 1
                p["message_sent_date"] = TODAY
                p["message_text"] = BATCH4[no]
                messaged_count += 1

    with open(PROSPECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Updated pipeline: {messaged_count} messaged, {excluded_count} excluded")
    print(f"File: {PROSPECTS_FILE}")

    # Print summary
    from collections import Counter
    statuses = Counter(p.get("status") for p in data)
    print(f"Pipeline totals: {dict(statuses)}")

if __name__ == "__main__":
    main()
