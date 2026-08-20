"""The durable assignment the sales Agent wakes up to every day."""
from __future__ import annotations

import datetime as dt
import json
import re

from app import settings

_KEY = "agent_sales_mission"
MINIMUM_SAFE_FIT = 75
MAX_DAILY_LEADS = 20
MARKET_EVIDENCE_MIN = 25

DEFAULT = {
    "target_markets": ["USA", "South Korea"],
    "daily_qualified_leads": 5,
    "minimum_fit_score": MINIMUM_SAFE_FIT,
    "auto_enroll": True,
}

_SEARCHES = (
    "LED screen rental company stage events",
    "AV integrator LED video wall installation",
    "digital signage company LED display installer",
    "LED display reseller distributor",
)


def _int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize(value: dict | None) -> dict:
    raw = value if isinstance(value, dict) else {}
    markets: list[str] = []
    for item in raw.get("target_markets", DEFAULT["target_markets"]):
        market = str(item).strip()
        if market and market not in markets:
            markets.append(market)
    if not markets:
        markets = list(DEFAULT["target_markets"])
    daily = max(0, min(MAX_DAILY_LEADS,
                       _int(raw.get("daily_qualified_leads"),
                            DEFAULT["daily_qualified_leads"])))
    fit = max(MINIMUM_SAFE_FIT, min(100,
              _int(raw.get("minimum_fit_score"), DEFAULT["minimum_fit_score"])))
    return {
        "target_markets": markets[:8],
        "daily_qualified_leads": daily,
        "minimum_fit_score": fit,
        "auto_enroll": bool(raw.get("auto_enroll", DEFAULT["auto_enroll"])),
    }


def get(conn) -> dict:
    raw = settings.get(conn, _KEY)
    try:
        parsed = json.loads(raw) if raw else {}
    except (TypeError, json.JSONDecodeError):
        parsed = {}
    return normalize(parsed)


def set_mission(conn, value: dict) -> dict:
    clean = normalize(value)
    settings.set_value(conn, _KEY, json.dumps(clean, ensure_ascii=False))
    return clean


def progress(conn) -> dict:
    """Qualified contactable accounts added today, from any legitimate path."""
    rows = conn.execute(
        "SELECT target_fit, email_status FROM leads"
        " WHERE date(created_at, 'localtime')=date('now', 'localtime')"
        "   AND COALESCE(email,'') != ''"
    ).fetchall()
    assignment = get(conn)
    minimum = assignment["minimum_fit_score"]
    count = 0
    for row in rows:
        match = re.search(r"\((\d{1,3})\)\s*$", row["target_fit"] or "")
        if (row["email_status"] != "invalid" and match
                and int(match.group(1)) >= minimum):
            count += 1
    target = assignment["daily_qualified_leads"]
    return {"qualified_leads_imported_today": count,
            "daily_target": target, "remaining": max(0, target - count)}


def choose_market(conn, markets: list[str]) -> str:
    """Explore under-sampled markets, then use observed reply rate once comparable."""
    from app import campaigns

    ordered = markets or list(DEFAULT["target_markets"])
    stats = {row["country"]: row for row in campaigns.country_stats(conn, min_touched=0)}
    performance = [{"country": market, "order": i,
                    "touched": int(stats.get(market, {}).get("touched") or 0),
                    "reply_rate": float(stats.get(market, {}).get("reply_rate") or 0)}
                   for i, market in enumerate(ordered)]
    under_sampled = [row for row in performance if row["touched"] < MARKET_EVIDENCE_MIN]
    if under_sampled:
        return min(under_sampled, key=lambda row: (row["touched"], row["order"]))["country"]
    return max(performance,
               key=lambda row: (row["reply_rate"], -row["touched"], -row["order"]))["country"]


def fallback_discovery(conn, state: dict) -> dict | None:
    """Create one safe search action when the model returned no usable work."""
    assignment = state.get("mission") or DEFAULT
    progress_state = state.get("mission_progress") or {}
    if assignment.get("daily_qualified_leads", 0) <= 0:
        return None
    if progress_state.get("remaining", 0) <= 0:
        return None
    if state.get("pending_replies"):
        return None
    if any(p.get("kind") == "discover_run" for p in state.get("already_pending") or []):
        return None
    markets = assignment.get("target_markets") or DEFAULT["target_markets"]
    ordinal = dt.date.today().toordinal()
    market = choose_market(conn, markets)
    offset = ordinal % len(_SEARCHES)
    queries = [_SEARCHES[offset], _SEARCHES[(offset + 1) % len(_SEARCHES)]]
    return {
        "kind": "discover_run", "lead_no": None,
        "title": f"补足今日合格新客目标：{market}",
        "why": (f"任务书兜底：今日还差 {progress_state.get('remaining', 0)} 家合格新客，"
                "模型没有给出可执行动作，因此只启动找客，不绕过后续质量门。"),
        "risk": "low",
        "payload": {"queries": queries, "country": market},
    }
