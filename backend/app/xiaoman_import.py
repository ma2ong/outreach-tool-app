"""Turn four years of sent mail into customer records, using the mail as the evidence.

`xiaoman_raw/sent.json` holds 3031 messages Allen sent between 2022-09 and today, to 1153
addresses across 316 domains. That log is a better record of who he has a relationship
with than the CRM's own customer list, most of which was filled by Xiaoman's prospecting
tool and never written to.

Two things this has to get right:

**Who is a customer.** A domain Allen wrote to 37 times (barco.com) is a company; a
freight forwarder he emailed about a shipment is not, and neither is a platform
notification address. Company domains become one lead with several contacts; the
free-mail addresses (naver.com is 80 of them — Korean buyers use it) cannot be grouped
that way, so each becomes its own record.

**When it was contacted.** The date comes from the mail itself, never from today. That
is what stops these records from being treated as fresh leads and sent a first cold email
three years into the relationship (`docs/54` R1).

Run:  python -m app.xiaoman_import            # preview only
      python -m app.xiaoman_import --apply    # write
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from app import import_customers
from app.db import connect

DB = "outreach.db"
SENT = Path("xiaoman_raw") / "sent.json"

# Addresses that are not a customer relationship, however many mails went to them.
_NOT_A_CUSTOMER = (
    "alibaba.com", "linkedin.com", "xiaoman.cn", "okki.com", "qiye.163.com",
    "maxcolorvisual.com", "mcvisualled.com", "allenma2ong@", "noreply", "no-reply",
    "donotreply",
    "notification", "notice@", "service@service", "mailer-daemon", "postmaster",
)
# Freight forwarders and other suppliers Allen mails about his own shipments.
_SUPPLIER_HINT = ("mjlog", "canairsea", "logistics", "freight", "forwarder", "shipping")
# Domains that identify a person, not a company, so they cannot be grouped into one lead.
_FREE_MAIL = {
    "gmail.com", "googlemail.com", "naver.com", "hanmail.net", "daum.net", "nate.com",
    "outlook.com", "hotmail.com", "live.com", "msn.com", "yahoo.com", "yahoo.co.jp",
    "yahoo.com.br", "ymail.com", "icloud.com", "me.com", "aol.com", "protonmail.com",
    "proton.me", "gmx.com", "gmx.de", "zoho.com", "mail.com", "163.com", "126.com",
    "qq.com", "foxmail.com", "sina.com", "yeah.net", "hotmail.co.uk", "web.de",
    "libero.it", "orange.fr", "wanadoo.fr", "terra.com.br", "uol.com.br", "bol.com.br",
}


def _addresses(field: str | None) -> list[str]:
    """Every address in a To/Cc field, which may hold a display name and several entries."""
    found = re.findall(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", field or "")
    return [a.strip().lower() for a in found]


def _is_customer(address: str) -> bool:
    low = address.lower()
    if any(word in low for word in _NOT_A_CUSTOMER):
        return False
    return not any(word in low for word in _SUPPLIER_HINT)


def _company_from_domain(domain: str) -> str:
    label = domain.split(".")[0].replace("-", " ").replace("_", " ")
    return " ".join(word.capitalize() for word in label.split())


def build_rows(sent: list[dict]) -> list[dict]:
    """One row per company (or per person, for free-mail), with its real contact dates."""
    by_address: dict[str, dict] = {}
    for message in sent:
        when = (message.get("receive_time") or "")[:10]
        for address in _addresses(message.get("receiver")):
            if not _is_customer(address):
                continue
            entry = by_address.setdefault(address, {"count": 0, "last": "", "subject": ""})
            entry["count"] += 1
            if when > entry["last"]:
                entry["last"] = when
                entry["subject"] = message.get("subject") or ""

    grouped: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for address, entry in by_address.items():
        grouped[address.split("@")[-1]].append((address, entry))

    rows: list[dict] = []
    for domain, members in grouped.items():
        if domain in _FREE_MAIL:
            # No company to group by, so each address stands alone. The name is the
            # address itself: inventing a company from "babo2861" would be a guess.
            for address, entry in members:
                rows.append({
                    "company_en": address, "email": address,
                    "last_contact": entry["last"],
                    "status": "已联系",
                    "business": f"小满邮件往来 {entry['count']} 封，最后一次：{entry['subject'][:80]}",
                })
            continue
        members.sort(key=lambda kv: (-kv[1]["count"], kv[0]))
        primary, entry = members[0]
        total = sum(m[1]["count"] for m in members)
        others = "；其他联系人：" + "、".join(a for a, _ in members[1:6]) if len(members) > 1 else ""
        rows.append({
            "company_en": _company_from_domain(domain),
            "email": primary,
            "website": domain,
            "last_contact": max(m[1]["last"] for m in members),
            "status": "已联系",
            "business": f"小满邮件往来 {total} 封（{len(members)} 位联系人），"
                        f"最后一次：{entry['subject'][:80]}{others}",
        })
    rows.sort(key=lambda r: r["last_contact"], reverse=True)
    return rows


def main(apply_it: bool) -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not SENT.exists():
        print(f"找不到 {SENT}，先运行 python -m app.xiaoman_fetch")
        return
    sent = json.loads(SENT.read_text(encoding="utf-8"))
    rows = build_rows(sent)
    conn = connect(DB)
    plan = import_customers.preview(conn, rows)

    print(f"从 {len(sent)} 封已发送邮件里，整理出 {len(rows)} 家客户/联系人")
    print(f"  新建 {plan['created']}，补充已有 {plan['merged']}，跳过 {plan['skipped']}")
    print("\n最近联系过的 12 家：")
    for row in rows[:12]:
        print(f"  {row['last_contact']}  {row['company_en'][:32]:34} {row['email']}")
    print("\n全部按「已触达」入库，不会再收到首封开发信；联系日期用邮件里的真实日期。")
    if not apply_it:
        print("预览模式，未写入。加 --apply 执行")
        return
    result = import_customers.apply(conn, rows)
    print(f"\n已导入：新建 {result['created']}，补充 {result['merged']}，跳过 {result['skipped']}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
