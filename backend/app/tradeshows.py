"""Source leads from a trade-show exhibitor directory (docs/57).

The harvesting already exists — `discovery.run_page_discovery` reads a directory page,
enriches each domain, scores it and drops peer factories. What a trade show adds is the
one sentence nobody else can write:

    看到你们在 InfoComm 2026 的展位

The lead book's worst habit is a shared opener: 579 leads once carried the same hook and
336 of them were word-for-word identical. An exhibitor line cannot collide, because it is
only true of companies actually on that list.

Which makes it a fact, and facts need a source (docs/45). The hook is written only for
domains that appeared on the page we fetched, only when that page names its year, and the
booth number is copied or omitted — never inferred, because a wrong booth number gives
the whole thing away on the first reply.

Run:  python -m app.tradeshows "<名录页 URL>" --show "InfoComm" --limit 40
      python -m app.tradeshows "<名录页 URL>" --show "InfoComm" --apply
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys

from app import repository as repo
from app.db import connect
from app.discovery import import_candidates, run_page_discovery

SOURCE = "展会名录"
# A show list is worth reading for a few seasons; older than this and "we saw your booth"
# invites the reply "that was three years ago".
MAX_AGE_YEARS = 3

# 2019–2039. A wider pattern matches phone fragments and product codes in page titles.
_YEAR = re.compile(r"\b(20[2-3]\d)\b")


def year_from(*sources: str | None) -> int | None:
    """The edition this directory belongs to, taken from the page — never from today.

    Today's date would label a 2023 exhibitor list as the 2026 show, and the opener
    becomes a claim the customer knows is false.
    """
    for text in sources:
        found = _YEAR.findall(str(text or ""))
        if found:
            # A page can mention several years ("2026 show, 2025 archive"); the newest
            # one is the edition it is about.
            return max(int(y) for y in found)
    return None


def hook_for(show: str, year: int, booth: str | None = None) -> str:
    """The opener. Booth appears only when the directory printed one."""
    where = f"{show} {year}"
    return f"看到你们在 {where} 的展位 {booth}。" if booth else f"看到你们在 {where} 的展位。"


def _too_old(year: int, today: dt.date | None = None) -> bool:
    return (today or dt.date.today()).year - year > MAX_AGE_YEARS


def prepare(candidates: list[dict], *, show: str, year: int | None, url: str,
            today: dt.date | None = None) -> dict:
    """Attach the exhibitor hook to the candidates that earned it.

    Returns the candidates plus a note about what was left alone, so the caller can say
    why rather than silently importing a batch of ordinary directory leads.
    """
    reason = None
    if not year:
        reason = "名录页上没有年份，不写展位开场白"
    elif _too_old(year, today):
        reason = f"{year} 年的名单太旧了（超过 {MAX_AGE_YEARS} 年），不写展位开场白"

    hooked = 0
    for cand in candidates:
        if reason:
            continue
        # Booth numbers arrive only if the harvester found one next to the domain; there
        # is no fallback, by design.
        cand["hook"] = hook_for(show, year, cand.get("booth"))
        cand["source"] = f"{SOURCE}：{show} {year}"
        existing = cand.get("source_urls") or []
        cand["source_urls"] = [*existing, url] if url not in existing else existing
        hooked += 1
    return {"candidates": candidates, "hooked": hooked, "skipped_reason": reason,
            "show": show, "year": year, "url": url}


def run(conn, url: str, *, show: str, limit: int = 40, year: int | None = None,
        apply_changes: bool = False, page_title: str = "") -> dict:
    """Harvest one exhibitor directory. Peer factories are dropped by the shared screen."""
    candidates = run_page_discovery(conn, url, limit=limit)
    # Half of an LED show's exhibitor list is Allen's own competition. run_page_discovery
    # already marks those excluded; importing one would hand a competitor his pitch.
    usable = [c for c in candidates if not c.get("excluded")]
    prepared = prepare(usable, show=show, year=year or year_from(url, page_title), url=url)

    result = {**prepared, "found": len(candidates), "usable": len(usable),
              "excluded": len(candidates) - len(usable)}
    if apply_changes:
        result["imported"] = import_candidates(conn, prepared["candidates"])
    return result


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="从展会展商名录页抓客户")
    parser.add_argument("url", help="展商名录页 URL")
    parser.add_argument("--show", required=True, help="展会名，例如 InfoComm / ISE")
    parser.add_argument("--year", type=int, default=None, help="不填就从页面 URL 里读")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--apply", action="store_true", help="写库；不加就是预览")
    args = parser.parse_args()

    with connect("outreach.db") as conn:
        out = run(conn, args.url, show=args.show, limit=args.limit, year=args.year,
                  apply_changes=args.apply)
    print(f"名录上抓到 {out['found']} 家，滤掉同行 {out['excluded']} 家，可用 {out['usable']} 家")
    if out["skipped_reason"]:
        print(f"⚠ {out['skipped_reason']}")
    else:
        print(f"写上展位开场白：{out['hooked']} 家 —— {hook_for(out['show'], out['year'])}")
    if args.apply:
        print(f"已导入：{out['imported']}")
    else:
        print("确认没问题就加 --apply 写入")


if __name__ == "__main__":
    main()
