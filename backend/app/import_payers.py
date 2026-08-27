"""Companies that have already paid, taken from bank credit advices.

The five payers on the advices Allen sent over were not in the customer book at all —
not one. People who have wired him money were missing from the record of who his
customers are, which is a strange gap to have and worth more than any cold lead.

Two judgements this makes, because importing all five as "customers" would be wrong:

**A freight forwarder is not the buyer.** Shiryu Trading and Squalo's Cargo Moving are
logistics operators; the advice from Squalo's even says "PAGO PROVEEDOR POR COMPRA DE
CABLES LEDS" — paying a supplier on someone else's behalf. Cold-emailing them "we
manufacture LED panels" would be addressed to the wrong company. They are recorded as
what they are, and kept out of the sequences.

**They are already customers, not prospects.** Stage is `won` and the email channel is
marked as already contacted, so tomorrow's cold opener cannot go to someone who has
bought — the exact mistake docs/54 exists to prevent.

Nothing from the advices beyond the company name and address is stored: no account
numbers, no bank references.

Run:  python -m app.import_payers            # preview
      python -m app.import_payers --apply
"""
from __future__ import annotations

import datetime as dt
import sys

from app import relationship_events, repository as repo
from app.db import connect

# Paid, and a company that actually uses LED displays.
CUSTOMERS = [
    {
        "company_en": "Big Screen Solutions",
        "country": "Australia",
        "city": "Melbourne",
        "website": "bigledscreen.com.au",
        "email": "info@bigledscreen.com.au",
        "phone": "1300 600 222",
        "business": "LED 屏供应与租赁（活动、零售、转播）。墨尔本 8/57 Willandra Drive, "
                    "Epping VIC 3076；悉尼 3/10 Sailfind Place, Somersby NSW 2250。",
        "paid": ("2026-08-12", 1483),
    },
    {
        "company_en": "Sitour Česká republika s.r.o.",
        "country": "Czech Republic",
        "city": "Praha",
        "website": "sitour.cz",
        "email": "milan.jurdik@sitour.eu",
        "phone": "+420 724 114 115",
        "contact_name": "Milan Jurdík",
        "title": "jednatel（董事）",
        "business": "山地度假区的户外广告与信息系统，捷克/欧洲滑雪场网络。"
                    "注册地 U Cikánky 158/2, 155 00 Praha 5，IČO 64578496，1995 年成立。",
        "paid": ("2026-07-10", 10818),
    },
]

# Paid, but the payment was made for somebody else. Recorded so the money is traceable
# to a name, and kept out of every sending path.
FORWARDERS = [
    {
        "company_en": "Shiryu Trading LLC",
        "country": "USA",
        "city": "Miami",
        "website": "shiryutrading.com",
        "business": "国际货代（空运/海运/陆运/清关），999 Brickell Ave Ste 410, Miami FL "
                    "33131。这笔款是替真正的买家付的，买家是谁要查你自己的订单。",
        "paid": ("2026-08-10", 9898),
    },
    {
        "company_en": "Squalo's Cargo Moving S.R.L.",
        "country": "Bolivia",
        "city": "La Paz",
        "business": "玻利维亚货运与搬迁公司。汇款附言写着 PAGO PROVEEDOR POR COMPRA DE "
                    "CABLES LEDS —— 替客户付给供应商，所以真正的买家不是它。",
        "paid": ("2026-08-26", 22860),
    },
]


def _existing(conn, row: dict) -> int | None:
    return repo.find_duplicate(conn, website=row.get("website")) or conn.execute(
        "SELECT no FROM leads WHERE lower(company_en)=lower(?)",
        (row["company_en"],)).fetchone() is not None and conn.execute(
        "SELECT no FROM leads WHERE lower(company_en)=lower(?)",
        (row["company_en"],)).fetchone()["no"] or None


def _add(conn, row: dict, *, buyer: bool) -> int | None:
    if _existing(conn, row) is not None:
        return None
    no = repo.insert_lead(conn, {
        "company_en": row["company_en"], "country": row.get("country"),
        "city": row.get("city"), "website": row.get("website"),
        "email": row.get("email"), "phone": row.get("phone"),
        "business": row.get("business"),
    })
    paid_on, amount = row["paid"]
    repo.update_lead(conn, no, {
        "contact_name": row.get("contact_name"), "title": row.get("title"),
        # Already a customer: `won` keeps them out of the cold pipeline's idea of a
        # fresh lead, and a forwarder is marked never-contact because a cold pitch to
        # them is addressed to the wrong company entirely.
        "stage": "won" if buyer else "lost",
        "do_not_contact": 0 if buyer else 1,
        "next_action": "确认这笔款对应的订单和联系人" if not buyer else None,
    })
    # The email channel is marked as touched so tomorrow's opener cannot introduce us
    # to someone who has already paid us (docs/54 R1).
    for channel in ("email", "whatsapp"):
        conn.execute(
            "INSERT INTO outreach(lead_no, channel, status, touch_count, message_sent_date)"
            " VALUES (?,?,'messaged',1,?)"
            " ON CONFLICT(lead_no, channel) DO NOTHING", (no, channel, paid_on))
    relationship_events.record(
        conn, no, "fact",
        f"银行到账 USD {amount:,}（{paid_on}）"
        + ("" if buyer else " —— 这笔是货代代付，真正的买家另有其人"),
        source="import", detail={"amount": amount, "on": paid_on,
                                 "role": "buyer" if buyer else "forwarder"})
    conn.commit()
    return no


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    apply_changes = "--apply" in sys.argv
    with connect("outreach.db") as conn:
        print("=== 已付款的客户 ===")
        for row in CUSTOMERS:
            here = _existing(conn, row)
            print(f"  {row['company_en'][:34]:36} {row.get('country',''):16}"
                  f" {'已在库 #' + str(here) if here else '待新增'}")
            print(f"      {row.get('email') or row.get('phone') or ''}"
                  f"  USD {row['paid'][1]:,} ({row['paid'][0]})")
        print("\n=== 货代（代付，不是买家）===")
        for row in FORWARDERS:
            here = _existing(conn, row)
            print(f"  {row['company_en'][:34]:36} {row.get('country',''):16}"
                  f" {'已在库 #' + str(here) if here else '待新增'}")
        if not apply_changes:
            print("\n确认没问题就加 --apply 写入")
            return
        added = [_add(conn, r, buyer=True) for r in CUSTOMERS]
        added += [_add(conn, r, buyer=False) for r in FORWARDERS]
        made = [n for n in added if n]
        print(f"\n已写入 {len(made)} 家：{made}")


if __name__ == "__main__":
    main()
