"""写着他们做过什么的那一页（docs/94）。

不联网：`enrich_domain` 收一个 fetch 函数，测试用一张假站点表。
"""
import pytest

from app import enrich, social_watch


def _site(pages: dict):
    """把一张 {url片段: 正文} 表变成 fetch 函数。命中不了的 URL 抛错。"""
    fetched = []

    def fetch(url):
        fetched.append(url)
        for key, text in pages.items():
            if key in url:
                return text
        raise RuntimeError(f"404 {url}")

    fetch.fetched = fetched
    return fetch


HOME = ("# Verum AV\n"
        "Indoor P2.5 panels for hire.\n"
        "[Products](https://verum.com/products)\n"
        "[About us](https://verum.com/about)\n"
        "[Case studies](https://verum.com/case-studies)\n"
        "[Blog](https://verum.com/blog)\n"
        "hello@verum.com · Lisbon, Portugal\n")


def test_a_case_page_is_read_even_when_the_pitch_is_already_known(  # docs/94 R2
        ):
    """首页就写了 P2.5 —— 旧规则到此为止，案例页永远打不开。"""
    fetch = _site({
        "/case-studies": "We supplied the main screen for the arena in Lisbon.",
        "/products": "P2.5 P3.9 panels",
        "/about": "Founded 2004",
        "/blog": "Latest post",
        "verum.com": HOME,
    })

    enrich.enrich_domain("verum.com", fetch=fetch)

    assert any("/case-studies" in u for u in fetch.fetched), fetch.fetched


def test_case_pages_do_not_compete_with_product_pages_for_slots():
    """验收 2：各有各的名额。"""
    fetch = _site({
        "/case-studies": "Arena screen, Lisbon.",
        "/projects": "Stadium install, Porto.",
        "/products": "P2.5 panels",
        "/catalog": "catalogue",
        "/about": "Founded 2004",
        "verum.com": HOME + "[Projects](https://verum.com/projects)\n"
                            "[Catalog](https://verum.com/catalog)\n",
    })

    enrich.enrich_domain("verum.com", fetch=fetch)

    got = " ".join(fetch.fetched)
    assert "/case-studies" in got or "/projects" in got, fetch.fetched


def test_a_blog_link_is_followed():
    """验收 3：blog 上写的是「最近在忙什么」，和 news 同一类。"""
    fetch = _site({
        "/blog": "August 2026 — we finished the arena job.",
        "/products": "P2.5",
        "/about": "Founded 2004",
        "/case-studies": "cases",
        "verum.com": HOME,
    })

    enrich.enrich_domain("verum.com", fetch=fetch)

    assert any("/blog" in u for u in fetch.fetched), fetch.fetched


def test_a_country_named_on_a_case_page_does_not_move_the_company():
    """验收 4：一家葡萄牙公司的案例页上全是迪拜，公司还在葡萄牙（R5）。"""
    fetch = _site({
        "/case-studies": ("Dubai Expo main screen. Dubai, United Arab Emirates. "
                          "Our Dubai office. Dubai Dubai Dubai United Arab Emirates."),
        "/products": "P2.5",
        "/about": "Founded 2004",
        "/blog": "posts",
        "verum.com": HOME,
    })

    out = enrich.enrich_domain("verum.com", fetch=fetch)

    assert out["country"] != "United Arab Emirates", out["country"]


def test_two_years_is_the_line_for_recent_activity():
    """验收 5：Allen 给的线是两年。"""
    assert social_watch.STALE_AFTER_DAYS == 730


def test_the_social_daily_limit_is_not_touched_by_this_spec():
    """验收 6：官网可以放开，社媒不行 —— 封号不会回来。"""
    assert social_watch.DAILY_LIMIT == 20
