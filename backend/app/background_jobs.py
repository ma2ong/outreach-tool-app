"""Business job adapters used by the scheduler; execution order lives in scheduler.py."""
from __future__ import annotations

import datetime as dt
import functools
import os

from app.db import connect

RECHECK_PER_DAY = 20


def email_poll(db_path: str):
    if os.environ.get("OUTREACH_AUTO_POLL", "1") == "0":
        return {"status": "disabled"}
    from app import replies
    conn = connect(db_path)
    try:
        result = replies.poll_all_replies(conn)
        combined_errors = [*(result.get("errors") or []),
                           *(result.get("enrichment_errors") or [])]
        if combined_errors:
            result["errors"] = combined_errors
        result["processed"] = sum(int(result.get(key) or 0)
                                  for key in ("replies", "bounces", "unsubscribes"))
        return result
    finally:
        conn.close()


def social_scan(db_path: str):
    if os.environ.get("OUTREACH_AUTO_SCAN", "1") == "0":
        return {"status": "disabled"}
    from app import inbound
    from app.api.channels import ENGINE
    conn = connect(db_path)
    try:
        if not inbound.should_scan_today(conn):
            return {"status": "idle"}
        live = [channel for channel in inbound.CHANNELS if ENGINE.status(channel) == "connected"]
        if not live:
            return {"status": "not_configured"}
        result = inbound.scan_all(conn, ENGINE.scan_threads, channels=live)
        if result.get("errors"):
            detail = "; ".join(str(item.get("error") or item) for item in result["errors"][:5])
            raise RuntimeError(detail or "social scan reported errors")
        result["processed"] = int(result.get("threads") or 0)
        return result
    finally:
        conn.close()


def website_recheck(db_path: str):
    if os.environ.get("OUTREACH_AUTO_RECHECK", "1") == "0":
        return {"status": "disabled"}
    from app import recheck, settings
    conn = connect(db_path)
    try:
        today = dt.date.today().isoformat()
        if settings.get(conn, "recheck_last_run") == today:
            return {"status": "idle"}
        result = recheck.sweep(conn, limit=RECHECK_PER_DAY)
        result["processed"] = max(0, int(result.get("checked") or 0) - int(result.get("failed") or 0))
        if not result.get("failed"):
            settings.set_value(conn, "recheck_last_run", today)
        return result
    finally:
        conn.close()


def sequence_maintenance(db_path: str):
    from app import sequences
    conn = connect(db_path)
    try:
        processed = sequences.block_unsendable(conn) + sequences.reopen_sendable(conn)
        return {"processed": processed}
    finally:
        conn.close()


def email_send(db_path: str):
    if os.environ.get("OUTREACH_AUTOSEND_SCHEDULER", "1") == "0":
        return {"status": "disabled"}
    from app import autosend, settings
    from app.api import send as send_api
    conn = connect(db_path)
    try:
        if not autosend.should_run(conn):
            return {"status": "idle"}
        return autosend.run_once(conn, send_api.pick_sender(conn), send_api.DEFAULT_ATTACHMENT)
    except Exception as exc:
        try:
            settings.set_value(conn, "autosend_last_result",
                               f"{dt.datetime.now():%m-%d %H:%M} 自动发送启动失败：{str(exc)[:110]}")
        except Exception:  # noqa: BLE001 — capability recorder retains the primary error
            pass
        raise
    finally:
        conn.close()


def social_send(db_path: str):
    if os.environ.get("OUTREACH_SOCIAL_QUEUE", "1") == "0":
        return {"status": "disabled"}
    from app import social_autonomy, social_queue, social_watch
    from app.api import channels as channels_api
    conn = connect(db_path)
    try:
        built = social_queue.build_today(conn)
        sent = social_autonomy.run_due(conn)
        social_watch.watch(conn, channels_api.ENGINE, limit=3)
        processed = int(built.get("queued") or built.get("created") or 0)
        processed += sum(int(value or 0) for value in sent.get("channels", {}).values()
                         if isinstance(value, int))
        return {"processed": processed, "built": built, "sent": sent}
    finally:
        conn.close()


def agent(db_path: str):
    if os.environ.get("OUTREACH_AGENT", "1") == "0":
        return {"status": "disabled"}
    from app import decision_maker_radar
    from app.agent import account_brain, catchup, opportunity_coach
    from app.agent import run as agent_run
    conn = connect(db_path)
    try:
        result = agent_run.run_once(conn)
        catchup.run_if_due(conn)
        account_brain.safety_net(conn)
        opportunity_coach.safety_net(conn)
        if os.environ.get("OUTREACH_AUTO_RESEARCH", "1") != "0":
            research = decision_maker_radar.sweep(conn)
            if research.get("errors"):
                result.setdefault("errors", []).extend(research["errors"])
            result["decision_maker_research"] = {
                key: research.get(key) for key in ("checked", "promoted", "proposed")
            }
        if isinstance(result, dict) and "processed" not in result:
            result["processed"] = int(result.get("proposed") or result.get("executed") or 0)
        return result
    finally:
        conn.close()


def contact_names(db_path: str):
    """Name contacts without making the Web application a job dependency."""
    from app import contact_names as names
    conn = connect(db_path)
    try:
        result = names.run_if_due(conn)
        if result is None:
            return {"status": "idle"}
        return {**result, "processed": int(result.get("named") or 0)}
    finally:
        conn.close()


def ordered_stages(db_path: str):
    """The one authoritative business order for embedded and standalone Workers."""
    return (
        ("email_poll", functools.partial(email_poll, db_path)),
        ("social_scan", functools.partial(social_scan, db_path)),
        ("website_recheck", functools.partial(website_recheck, db_path)),
        ("sequence_maintenance", functools.partial(sequence_maintenance, db_path)),
        ("email_send", functools.partial(email_send, db_path)),
        ("social_send", functools.partial(social_send, db_path)),
        ("contact_names", functools.partial(contact_names, db_path)),
        ("agent", functools.partial(agent, db_path)),
    )


def run_cycle(db_path: str) -> bool:
    from app import scheduler

    return scheduler.run_cycle(db_path, ordered_stages(db_path))
