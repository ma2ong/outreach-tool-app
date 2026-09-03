"""邮箱的出处（docs/89）。

退信按「谁见过这个地址」分层：官网上抓到的 4.9%，说不出出处的 19.7%。而 MX 校验
分不出这两类 —— 待发池里 482 个无出处地址有 267 个 `email_status='valid'`，
和历史上退掉的那批是同一个成分。DNS 回答的是「这个域名收不收信」，
回答不了「这个具体地址存不存在」；后者只有公司自己的页面能回答。

所以这里做的事很小：把一个说不出来历的地址，拿回它公司的官网上对一遍。

**它不挡任何一封信。** 这是 Allen 09-03 定的（docs/89 R2）：研究归研究，
读到有用的就入库，读不到就什么都不写，发信量一封都不因为研究而少。
在官网上找到一个不一样的地址就换掉 —— 那是在不减量的前提下把退信降下来，
和「因为说不出出处就不发」是两件事。
"""
from __future__ import annotations

import sqlite3

from app import enrich
from app.jina import fetch as jina_fetch

# 一轮扫描最多抓几家。抓取要联网，慢，且每家都是一次外部请求。
SWEEP_LIMIT = 40


def unsourced(conn: sqlite3.Connection, limit: int = SWEEP_LIMIT) -> list[dict]:
    """有邮箱、说不出出处、还没写过信的公司。

    有官网的排前面：那些是这一轮真能学到东西的。没官网的一样留在列表里，
    但它们只会得到一个 `no_website`，不写库、也不挡信。
    """
    return [dict(r) for r in conn.execute(
        "SELECT no, company_en, email, website FROM leads"
        " WHERE COALESCE(email,'') <> '' AND COALESCE(email_source,'') = ''"
        "   AND COALESCE(do_not_contact,0) = 0"
        "   AND COALESCE(email_status,'') <> 'invalid'"
        "   AND no NOT IN (SELECT lead_no FROM send_log WHERE channel='email')"
        " ORDER BY CASE WHEN COALESCE(website,'') = '' THEN 1 ELSE 0 END, no"
        " LIMIT ?", (limit,))]


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
        # 读不到就什么都不写。一条「去补联系方式」的任务对 483 家来说是 483 条噪音，
        # 而这个地址照样会发出去 —— 那条任务不改变任何事。
        return {"outcome": "no_website", "lead_no": lead_no}

    info = enrich.enrich_domain(website, fetch=fetch or jina_fetch)
    found = info.get("email")
    source = info.get("email_source")
    if not found or not source:
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
