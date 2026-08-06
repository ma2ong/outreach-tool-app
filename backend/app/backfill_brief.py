"""Read the websites of leads already in the book, and write their brief and hook.

    python -m app.backfill_brief [--limit N] [--delay SECONDS] [--all]

The book has hundreds of companies collected before any of this existed, and each one
needs a live fetch of its own site — this is hours of network, not a migration. So it is
a resumable command Allen runs in batches rather than something that happens at startup:
by default it takes the 40 oldest untouched leads, and running it again picks up where it
stopped.

It writes through `recheck.run`, which already holds the rules that matter: fill what is
empty, report what disagrees, never overwrite. The one thing it adds is the selection —
leads that have never been read, oldest first.
"""
import argparse
import sys
import time

from app import recheck
from app.db import connect
from app.main_deps import DB_PATH

DEFAULT_LIMIT = 40
# Each lead is now up to seven fetches (contact pass plus product pages). Running eight
# sites back to back with no gap made jina start returning empties, which reads exactly
# like a site with nothing on it — so the gap is deliberate and generous. A fetch that
# fails anyway leaves the lead pending, and the next batch picks it up.
DEFAULT_DELAY = 5.0


def pending(conn, limit: int) -> list[dict]:
    """Leads with a website we have never got anything out of. A hook counts as getting
    something: plenty of sites earn one without earning a brief. `recheck_count` keeps a
    second run from re-reading the sites that legitimately produced neither."""
    rows = conn.execute(
        "SELECT no, company_en, website FROM leads"
        " WHERE COALESCE(website, '') != ''"
        "   AND COALESCE(brief, '') = '' AND COALESCE(hook, '') = ''"
        "   AND COALESCE(do_not_contact, 0) = 0"
        "   AND COALESCE(recheck_count, 0) = 0"
        " ORDER BY no LIMIT ?",
        (max(1, limit),),
    ).fetchall()
    return [dict(r) for r in rows]


def run(conn, limit: int = DEFAULT_LIMIT, delay: float = DEFAULT_DELAY,
        enrich_fn=None, out=sys.stdout) -> dict:
    leads = pending(conn, limit)
    total = len(leads)
    written = failed = 0
    for i, lead in enumerate(leads, 1):
        result = recheck.run(conn, lead["no"], enrich_fn=enrich_fn, first_read=True)
        row = conn.execute("SELECT brief, hook FROM leads WHERE no=?", (lead["no"],)).fetchone()
        if not result.get("ok"):
            failed += 1
            status = f"抓取失败 {result.get('error', '')[:60]}"
        elif row["brief"] or row["hook"]:
            written += 1
            status = (row["brief"] or "")[:70] or (row["hook"] or "")[:70]
        else:
            status = "官网没有可引用的内容"
        print(f"[{i}/{total}] #{lead['no']} {lead['company_en'][:28]:<28} {status}", file=out)
        out.flush()
        if delay and i < total:
            time.sleep(delay)
    remaining = len(pending(conn, 10**6))
    return {"checked": total, "written": written, "failed": failed, "remaining": remaining}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="回填客户简介和开场白")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="本批处理多少家")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="每家之间等待秒数")
    parser.add_argument("--all", action="store_true", help="不限批量，一次跑完（会很久）")
    args = parser.parse_args(argv)
    conn = connect(DB_PATH)
    try:
        limit = 100000 if args.all else args.limit
        summary = run(conn, limit=limit, delay=args.delay)
    finally:
        conn.close()
    print(f"\n本批 {summary['checked']} 家：写入简介/开场白 {summary['written']}，"
          f"抓取失败 {summary['failed']}，还剩 {summary['remaining']} 家没跑。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
