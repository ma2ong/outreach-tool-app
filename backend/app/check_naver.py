"""Is the Naver channel actually working? (docs/70)

Run this after setting the keys, before trusting a day's prospecting to it. It asks one
real query and shows what came back, so a wrong key or a truncated secret shows up here
rather than as a quiet zero in tomorrow's report.

Run:  python -m app.check_naver
      python -m app.check_naver "LED 전광판 시공"
"""
from __future__ import annotations

import sys

from app import discovery_sources as sources

DEFAULT_QUERY = "LED 전광판 렌탈 업체"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    query = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUERY

    naver = sources.SOURCES["naver"]
    if not naver.available():
        print(f"✗ 还不能用：{naver.unavailable()}")
        print("  老的开发者中心（Client ID / Client Secret）对新应用已经关闭，")
        print("  搜索 API 迁到了 Naver Cloud Platform 的 API Hub，密钥换了名字。")
        return

    print(f"查询：{query}")
    try:
        found = naver.fetch(query, 20)
    except Exception as exc:  # noqa: BLE001
        detail = str(exc)
        print(f"✗ 调用失败：{detail[:200]}")
        # Naver's own error code says which problem it is; the HTTP status does not.
        # "Scopes are Empty" arrives as a 401 with the same code as a bad key, and it
        # means the opposite thing: the credentials are fine, the application simply has
        # no API enabled on it. Reading it as "wrong key" sends you re-copying a secret
        # that was never the problem.
        if "Scopes are Empty" in detail:
            print("  → 这是老开发者中心的密钥，它对搜索已经没有权限了。")
            print("    新密钥在 Naver Cloud Platform → API Hub，字段名也不一样。")
        elif "401" in detail:
            print("  → 密钥不对。API Hub 控制台里的 API Key ID 和 API Key，两个都要。")
        elif "403" in detail:
            print("  → 这个 Key 没订阅搜索服务。去 API Hub 里把 검색 加进这个应用。")
        elif "429" in detail:
            print("  → 超额度了。免费额度是 77.5 万次/月，正常用不该撞到。")
        return

    print(f"✓ 返回 {len(found)} 家公司（已滤掉博客、社媒和平台页）\n")
    for row in found[:12]:
        print(f"  {row['domain'][:38]:40} {row.get('title', '')[:34]}")
    if not found:
        print("  接口通了但没有公司站 —— 这个词搜出来的多半是博客和 cafe，换个更像"
              "公司名的关键词试试。")


if __name__ == "__main__":
    main()
