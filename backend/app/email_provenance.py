"""邮箱的出处（docs/89）。

退信按「谁见过这个地址」分层：官网上抓到的 4.9%，说不出出处的 19.7%。而 MX 校验
分不出这两类 —— 待发池里 482 个无出处地址有 267 个 `email_status='valid'`，
和历史上退掉的那批是同一个成分。DNS 回答的是「这个域名收不收信」，
回答不了「这个具体地址存不存在」；后者只有公司自己的页面能回答。

所以这里做的事很小：把一个说不出来历的地址，拿回它公司的官网上对一遍。
"""
from __future__ import annotations

import sqlite3

from app import activities, enrich
from app.jina import fetch as jina_fetch

TASK_TITLE = "补联系方式：%s 的邮箱在官网上找不到"

# 一轮扫描最多抓几家。抓取要联网，慢，且每家都是一次外部请求。
SWEEP_LIMIT = 40


def unsourced(conn: sqlite3.Connection, limit: int = SWEEP_LIMIT) -> list[dict]:
    """有邮箱、说不出出处、还没写过信的公司 —— 已经发过的不在其列（docs/89 R2）。"""
    return [dict(r) for r in conn.execute(
        "SELECT no, company_en, email, website FROM leads"
        " WHERE COALESCE(email,'') <> '' AND COALESCE(email_source,'') = ''"
        "   AND COALESCE(do_not_contact,0) = 0"
        "   AND COALESCE(email_status,'') <> 'invalid'"
        "   AND no NOT IN (SELECT lead_no FROM send_log WHERE channel='email')"
        " ORDER BY CASE WHEN COALESCE(website,'') = '' THEN 1 ELSE 0 END, no"
        " LIMIT ?", (limit,))]


def _task(conn, lead: dict, reason: str) -> None:
    """出处补不上是一件要人去做的活，不是一条要吞掉的错误。"""
    activities.create(conn, lead["no"], {
        "title": TASK_TITLE % (lead.get("company_en") or f"#{lead['no']}"),
        "type": "task", "priority": "normal",
        "note": f"{reason}。地址 {lead.get('email')} 没有任何出处，"
                f"这一类历史退信率 19.7%，所以不进发送队列（docs/89）。",
    })


def recover(conn: sqlite3.Connection, lead_no: int, fetch=None) -> dict:
    """回官网看一眼这个地址。返回 confirmed / replaced / unknown / no_website。

    三种结果各自的意思写在 docs/89 R1：官网上有它、官网上有别的、官网上什么都没有。
    """
    row = conn.execute(
        "SELECT no, company_en, email, website FROM leads WHERE no=?", (lead_no,)).fetchone()
    if row is None:
        return {"outcome": "missing", "lead_no": lead_no}
    lead = dict(row)
    current = str(lead.get("email") or "").strip().lower()
    website = str(lead.get("website") or "").strip()
    if not website:
        _task(conn, lead, "这家公司没有官网可读")
        return {"outcome": "no_website", "lead_no": lead_no}

    info = enrich.enrich_domain(website, fetch=fetch or jina_fetch)
    found = info.get("email")
    source = info.get("email_source")
    if not found or not source:
        _task(conn, lead, "官网读到了，但页面上没有邮箱")
        return {"outcome": "unknown", "lead_no": lead_no}

    # 直接写列，不走 repository.update_lead —— 那条路是「Allen 亲手改的」，
    # 会把出处盖成 manual，而 manual 恰好是退信率最高的那一类（25%）。
    if str(found).strip().lower() == current:
        conn.execute("UPDATE leads SET email_source=?, updated_at=datetime('now')"
                     " WHERE no=?", (source, lead_no))
        conn.commit()
        return {"outcome": "confirmed", "lead_no": lead_no,
                "email": current, "email_source": source}

    # 印在联系页上的地址，赢过一个猜出来的（docs/89 R1）。换了地址，
    # 旧地址的验证结果就不再适用，所以 email_status 清空等重新验。
    conn.execute("UPDATE leads SET email=?, email_source=?, email_status=NULL,"
                 " updated_at=datetime('now') WHERE no=?", (found, source, lead_no))
    conn.commit()
    return {"outcome": "replaced", "lead_no": lead_no,
            "email": found, "was": current, "email_source": source}


def sweep(conn: sqlite3.Connection, limit: int = SWEEP_LIMIT, fetch=None) -> dict:
    """跑一轮。计数按结果分开，这样「抓了多少」和「补回多少」不会混成一个数。"""
    counts = {"confirmed": 0, "replaced": 0, "unknown": 0, "no_website": 0, "missing": 0}
    for lead in unsourced(conn, limit):
        outcome = recover(conn, lead["no"], fetch=fetch)["outcome"]
        counts[outcome] = counts.get(outcome, 0) + 1
    counts["recovered"] = counts["confirmed"] + counts["replaced"]
    return counts
