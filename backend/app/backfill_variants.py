"""把 08-27 之前那批信的文案版本从 campaign 列上读回来（docs/90 R1）。

`sequence_send` 从 2026-08-28 起写 `variant=sequence_name`。在那之前发出的 605 封
序列邮件只写了 `campaign='序列:<序列名>'` —— 同一个事实，另一列。

不是推断：`variant` 的定义就是序列名。所以这里只做一件事，去掉 `序列:` 前缀。
标签是日期的那些（`email 2026-07-23`、`每日社媒队列`）说的是哪天群发的，
不是哪一版文案，一律不碰 —— 硬塞会造出一个不存在的变体（docs/90 R1）。

Run:  python -m app.backfill_variants
      python -m app.backfill_variants --apply
"""
from __future__ import annotations

import sqlite3
import sys

PREFIX = "序列:"


def candidates(conn: sqlite3.Connection) -> list[dict]:
    """没有变体、但 campaign 上带着序列名的行。"""
    return [dict(r) for r in conn.execute(
        "SELECT id, campaign FROM send_log"
        " WHERE COALESCE(variant,'') = '' AND campaign LIKE ? || '%'"
        " ORDER BY id", (PREFIX,))]


def run(conn: sqlite3.Connection, apply: bool = True) -> dict:
    """回填。重复跑第二次改 0 行 —— 条件本身就排除了已经有变体的。"""
    rows = candidates(conn)
    by_variant: dict[str, int] = {}
    for row in rows:
        name = str(row["campaign"])[len(PREFIX):].strip()
        if not name:
            continue
        by_variant[name] = by_variant.get(name, 0) + 1
        if apply:
            conn.execute("UPDATE send_log SET variant=? WHERE id=?", (name, row["id"]))
    if apply:
        conn.commit()
    return {"updated": sum(by_variant.values()), "by_variant": by_variant}


def main() -> None:
    from app.db import connect
    from app.main_deps import DB_PATH

    apply = "--apply" in sys.argv
    conn = connect(DB_PATH)
    result = run(conn, apply=apply)
    print(("已回填 " if apply else "可回填 ") + f"{result['updated']} 行")
    for name, count in sorted(result["by_variant"].items(), key=lambda x: -x[1]):
        print(f"  {count:>4}  {name}")
    if not apply:
        print("\n加 --apply 才会写入。")


if __name__ == "__main__":
    main()
