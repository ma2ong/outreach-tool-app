"""What last night actually did, and what it means (docs/69, docs/71).

The daily report says what happened. This says whether it worked — which is a different
question, and the one that decides what to build next.

It exists because of a specific moment: 113 letters went out on the second angle after
the first sent 361 for one reply, and until those land there is no honest basis for
choosing the next piece of work. Building a thirty-third agent module on an unmeasured
base would only make "which step is not working" harder to answer.

Run:  python -m app.morning_readout
      python -m app.morning_readout 7      # look back a week instead of a day
"""
from __future__ import annotations

import datetime as dt
import sys

from app import copy_experiments as ce
from app import relationship_events, settings, social_watch
from app.db import connect


def _line(title: str) -> None:
    print(f"\n■ {title}")


def _sending(conn, days: int) -> None:
    _line("发出去了多少")
    rows = conn.execute(
        "SELECT channel, COUNT(*) n, COUNT(DISTINCT lead_no) leads FROM send_log"
        " WHERE sent_at >= datetime('now', ?) GROUP BY channel ORDER BY n DESC",
        (f"-{days} days",)).fetchall()
    if not rows:
        print("  一封都没发出去。")
        print("  先看『邮件计划』页：是没有到期的，还是被额度或时区挡住了。")
        return
    for row in rows:
        print(f"  {row['channel']:10} {row['n']:4} 封，{row['leads']} 家")

    bounced = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE bounced_at >= datetime('now', ?)",
        (f"-{days} days",)).fetchone()[0]
    sent = sum(r["leads"] for r in rows)
    if bounced:
        rate = round(100.0 * bounced / sent, 1) if sent else 0
        print(f"  其中退信 {bounced} 家（{rate}%）—— 按你的规则不影响发送计划，"
              f"每封退信会变成一条『去找这家另一个联系人』的任务")


def _experiments(conn, days: int) -> None:
    _line("哪套话术管用")
    unmeasured = ce.unmeasured(conn, days)
    rows = ce.breakdown(conn, ("variant", "market"), days=days)
    if not rows:
        print("  还没有带记录的发送。")
        if unmeasured:
            print(f"  （{unmeasured} 封是记录这些字段之前发的，无法归入任何一套话术）")
        return

    for row in rows:
        print(f"  {str(row['variant'])[:24]:26} {str(row['market'] or '未知'):14}"
              f" 发 {row['sent']:4}  客户 {row['leads']:4}  回 {row['replied']:3}"
              f"  {row['reply_rate']}%")

    total_leads = sum(r["leads"] for r in rows)
    total_replied = sum(r["replied"] for r in rows)
    if total_replied == 0 and total_leads >= 40:
        # Saying this out loud matters: the instinct after a zero is to rewrite the
        # copy again, and that is only right if the copy is what failed.
        print(f"\n  {total_leads} 家零回复。够大的样本了，值得先问一句：")
        print("  是话术不行，还是这批名单本来就不通过冷邮件成交？")
        print("  这两件事要修的地方完全不同。")
    elif total_replied:
        print(f"\n  {total_replied} 个回复。按客户类型再切一刀看看哪种人会回：")
        for row in ce.breakdown(conn, ("audience",), days=days)[:6]:
            print(f"    {str(row['audience'] or '类型未知'):12}"
                  f" 发 {row['sent']:4} 回 {row['replied']:3}  {row['reply_rate']}%")


def _development(conn, days: int) -> None:
    _line("开发到了什么")
    new_leads = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE created_at >= datetime('now', ?)",
        (f"-{days} days",)).fetchone()[0]
    facts = relationship_events.recent(conn, kind="fact", days=days, limit=500)
    from_discovery = [f for f in facts if f["source"] == "discovery"]
    print(f"  新客户 {new_leads} 家")
    print(f"  给 {len({f['lead_no'] for f in from_discovery})} 家老客户补到新信息")
    for fact in from_discovery[:6]:
        print(f"    {str(fact['company_en'] or fact['lead_no'])[:24]:26} {fact['summary'][:44]}")

    looked = social_watch.DAILY_LIMIT - social_watch.remaining(conn)
    pending = social_watch.sending_pending(conn)
    if looked:
        print(f"  看了 {looked} 家社媒主页")
    elif pending:
        print(f"  社媒主页一个没看：今天还有 {pending} 条私信没发完（这是刻意的）")
    else:
        print("  社媒主页一个没看")


def _waiting(conn) -> None:
    _line("等你定的")
    queue = conn.execute(
        "SELECT COUNT(*) FROM social_dm_queue WHERE queue_date=date('now')"
        " AND status='ready'").fetchone()[0]
    replies = conn.execute(
        "SELECT COUNT(*) FROM inbox_messages WHERE kind='reply' AND handled_at IS NULL"
    ).fetchone()[0]
    if replies:
        print(f"  {replies} 封客户回复还没处理 —— 这是今天最值钱的事")
    if queue:
        print(f"  {queue} 条社媒私信备好了等你确认")
    if not replies and not queue:
        print("  没有")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    with connect("outreach.db") as conn:
        span = "昨天到现在" if days == 1 else f"最近 {days} 天"
        print(f"【{dt.date.today()} 读数 · {span}】")
        last = settings.get(conn, "autosend_last_result")
        if last:
            print(f"  上次自动发送：{last}")
        _sending(conn, days)
        _experiments(conn, days)
        _development(conn, days)
        _waiting(conn)
        print("\n看完这几组数再决定下一步做什么 —— 而不是先做，再想为什么没效果。")


if __name__ == "__main__":
    main()
