"""docs/128 — the channel table nobody called, and what Playwright is worth on each channel."""
import pytest

from app import discovery, discovery_sources as ds
from app import scrape_browser, scrape_runner


# ------------------------------------------------------- R1 the table gets called

def test_keyword_search_asks_the_channel_table(monkeypatch, conn):
    """Before this spec `run_discovery` called DuckDuckGo directly and the table sat unused."""
    asked: list[tuple] = []

    def fake_gather(queries, limit_per_query=20, only=None, engine=None):
        asked.append((tuple(queries), limit_per_query, only, engine))
        return {"candidates": [{"domain": "pst24.co.kr", "source": "naver-web"}], "sources": []}

    monkeypatch.setattr(ds, "gather", fake_gather)
    out = discovery.run_discovery(conn, "LED 전광판 유통업체", 5,
                                  enrich_fn=lambda d: {"country": "South Korea"})
    assert asked and asked[0][0] == ("LED 전광판 유통업체",)
    assert [c["domain"] for c in out] == ["pst24.co.kr"]


def test_a_candidate_keeps_the_channel_that_found_it(monkeypatch, conn):
    """Which channel produces buyers is unanswerable if every row says 「搜索」."""
    monkeypatch.setattr(ds, "gather", lambda *a, **k: {
        "candidates": [{"domain": "pst24.co.kr", "source": "naver-web"},
                       {"domain": "arrow.com", "source": "duckduckgo"}], "sources": []})
    out = discovery.run_discovery(conn, "led", 5, enrich_fn=lambda d: {})
    assert {c["domain"]: c["source"] for c in out} == {
        "pst24.co.kr": "naver-web", "arrow.com": "duckduckgo"}


def test_an_unattended_search_never_reaches_a_channel_that_opens_a_window(monkeypatch):
    """docs/126 R5 lives in `gather`, so wiring a caller must not be able to undo it."""
    opened: list[str] = []
    for name, source in ds.SOURCES.items():
        monkeypatch.setitem(ds.SOURCES, name, source)
        for engine, reader in source.readers.items():
            def spy(q, lim, _n=name, _r=reader):
                opened.append(_n)
                return []
            source.readers[engine] = spy
    ds.gather(["led"], 5)
    assert all(ds.SOURCES[n].unattended for n in opened), opened


# --------------------------------------------------- R2 a wall is not zero companies

def test_a_wall_is_recognised_by_what_it_actually_said():
    """The exact strings measured on 2026-09-11, jina and Playwright and real Chrome."""
    assert scrape_runner.blocked_reason(
        "Our systems have detected unusual traffic from your computer network.")
    assert scrape_runner.blocked_reason("我们的系统检测到您的计算机网络中存在异常流量")
    assert scrape_runner.blocked_reason("This page maybe requiring CAPTCHA")
    assert not scrape_runner.blocked_reason(
        "LED display distributor - 10 results for unusual companies")


def test_a_blocked_channel_reports_the_wall_instead_of_zero_companies(monkeypatch):
    def walled(*a, **k):
        raise scrape_browser.Blocked("Google 判定本机为异常流量")

    source = ds.SOURCES["google"]
    monkeypatch.setitem(source.readers, "playwright", walled)
    report = ds.gather(["led"], 5, only=["google"], engine="playwright")
    row = report["sources"][0]
    assert row["status"] == "失败"
    assert "异常流量" in row["reason"]


# ------------------------------------------------------- R3 a collecting identity

def test_collecting_never_opens_the_profile_that_sends():
    from app import playwright_engine

    sending = str(playwright_engine.DATA_DIR).lower()
    assert not str(scrape_browser.SCRAPE_DIR).lower().startswith(sending)
    assert not str(scrape_browser.profile_dir("instagram")).lower().startswith(sending)


# ------------------------------------------- R4 instagram / facebook are registered

def test_instagram_is_registered_and_says_how_to_turn_it_on(monkeypatch):
    monkeypatch.setattr(scrape_browser, "logged_in", lambda channel: False)
    row = {r["name"]: r for r in ds.status()}["instagram"]
    assert row["engines"] == ["playwright"]
    assert row["available"] is False
    assert "未启用" in row["reason"] and "采集" in row["reason"]
    assert row["optional"] and row["unattended"] is False


# ------------------------------- R4 facebook needs no account: the pages are public

def test_facebook_needs_no_login_and_may_therefore_run_unattended(monkeypatch):
    """Measured 2026-09-11: a logged-out browser reads facebook.com/<page>/about."""
    monkeypatch.setattr(scrape_browser, "logged_in", lambda channel: False)
    row = {r["name"]: r for r in ds.status()}["facebook"]
    assert row["available"] is True, row["reason"]
    assert row["unattended"] is True, "headless、无账号、不弹窗的渠道没有理由被挡在调度器外"


def test_facebook_pages_are_found_outside_facebook(monkeypatch):
    """FB's own search is dead logged out, so the finding step is a normal web search."""
    seen: list[str] = []

    def fake_search(query, limit=10, **kw):
        seen.append(query)
        return ["https://www.facebook.com/gcled",
                "https://www.facebook.com/groups/1813353365557599",
                "https://www.facebook.com/Techledwall/videos/-we-are/339327871633141",
                "https://secure.facebook.com",
                "https://example.com/not-facebook"]

    import app.search
    monkeypatch.setattr(app.search, "search_urls", fake_search)
    monkeypatch.setattr(scrape_browser, "read_pages",
                        lambda channel, handles, limit=20: [
                            {"handle": h, "domain": "gcled-usa.com"} for h in handles])
    out = ds.facebook_public_pages("LED display distributor", 5)
    assert "site:facebook.com" in seen[0]
    assert [c["facebook"] for c in out] == ["gcled"]
    assert out[0]["domain"] == "gcled-usa.com"


def test_a_page_with_no_website_is_not_a_candidate(monkeypatch):
    """docs/124 R1: the domain is the only field that crosses, so no domain, no row."""
    monkeypatch.setattr(ds, "_facebook_page_urls",
                        lambda q, limit=10: ["https://www.facebook.com/gcled"])
    monkeypatch.setattr(scrape_browser, "read_pages",
                        lambda channel, handles, limit=20: [{"handle": "gcled", "domain": ""}])
    assert ds.facebook_public_pages("led", 5) == []


def test_the_about_tab_gives_up_the_site_the_page_links_to():
    """The strings are from the real pages read on 2026-09-11."""
    assert scrape_runner.site_from_about(
        "GCL Electronics 3.7K followers Contact info +1 469-686-1719 Mobile "
        "info@gcled-usa.com Email https://gcled-usa.com/ Website Electronics") == "gcled-usa.com"
    assert scrape_runner.site_from_about(
        "LED3 Contact info clare@led3.us Email www.led3.us Website") == "led3.us"
    # A page that is restricted or gone says so, and that is not a website.
    assert scrape_runner.site_from_about(
        "This content isn't available right now Go to Feed Visit Help Centre") == ""
    # Facebook's own links, and the login form, never count as the company's site.
    assert scrape_runner.site_from_about(
        "Log In Forgot Account? facebook.com/help messenger.com") == ""


def test_a_handle_is_only_worth_the_domain_it_leads_to():
    """docs/126 R2 again: what crosses the line is a domain, never a handle."""
    assert scrape_runner.handles_from_hrefs(
        ["https://www.instagram.com/ledworld_mx/", "https://www.instagram.com/p/C123/",
         "https://www.instagram.com/explore/tags/led/"], "instagram") == ["ledworld_mx"]
    assert scrape_runner.external_host(
        ["https://www.instagram.com/ledworld_mx/", "https://help.instagram.com/x",
         "https://ledworld.mx/contacto"], "instagram") == "ledworld.mx"
    assert scrape_runner.external_host(["https://www.facebook.com/x"], "facebook") == ""


# --------------------------------------------------- R5 the reader must be declared

def test_a_channel_declares_its_readers_cheapest_first():
    assert ds.SOURCES["duckduckgo"].engines == ("http",)
    assert ds.SOURCES["google"].engines == ("playwright", "browser")
    assert ds.SOURCES["naver-blog"].engines == ("browser",)


def test_asking_a_channel_for_a_reader_it_never_declared_is_refused():
    with pytest.raises(ValueError):
        ds.SOURCES["duckduckgo"].fetch("led", 5, engine="browser")


# ------------------------------------------------------------- what does not go in

def test_bing_is_not_a_channel():
    """Measured 2026-09-11: it answers a question you did not ask, without saying so.

    `LED screen reseller Mexico` and `LED 전광판 유통업체` both returned the same ten
    encyclopaedia pages about the diode, twice running, in a fresh context each time.
    """
    assert "bing" not in ds.SOURCES


# ------------------------------------------------------------- the API side of R5

def _client(tmp_path):
    import app.main as main
    import app.api.discover as disc
    from app.db import connect, init_schema
    from fastapi.testclient import TestClient

    db = str(tmp_path / "t.db")
    c = connect(db)
    init_schema(c)
    c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    disc.DB_PATH = db
    disc.SEARCH_FN = None
    disc.ENRICH_FN = lambda d: {"domain": d}
    return TestClient(main.app)


def test_the_api_refuses_a_reader_the_channel_never_declared(tmp_path):
    client = _client(tmp_path)
    r = client.post("/api/discover", json={"query": "led", "channels": ["duckduckgo"],
                                           "engine": "browser"})
    assert r.status_code == 400
    assert "http" in r.json()["detail"]


def test_the_api_refuses_a_channel_that_does_not_exist(tmp_path):
    client = _client(tmp_path)
    r = client.post("/api/discover", json={"query": "led", "channels": ["bing"]})
    assert r.status_code == 400


def test_a_channel_that_is_not_switched_on_is_refused_before_the_job_exists(tmp_path):
    """docs/124 R5: an unconfigured channel is something to say now, not a job that
    finishes empty."""
    client = _client(tmp_path)
    r = client.post("/api/discover", json={"query": "led", "channels": ["instagram"]})
    assert r.status_code == 400
    assert "未启用" in r.json()["detail"]


def test_what_each_channel_reported_travels_with_the_result(tmp_path, monkeypatch):
    from app import jobs

    jobs.clear()
    monkeypatch.setattr(ds, "gather", lambda q, lim, only=None, engine=None: {
        "candidates": [{"domain": "pst24.co.kr", "source": "naver-web"}],
        "sources": [{"name": "naver-web", "found": 1, "status": "ok", "reason": ""},
                    {"name": "google", "found": 0, "status": "失败",
                     "reason": "google 把我们挡下来了：unusual traffic"}]})
    client = _client(tmp_path)
    job_id = client.post("/api/discover", json={"query": "led"}).json()["job_id"]
    result = client.get(f"/api/discover/jobs/{job_id}").json()["result"]
    walled = [s for s in result["sources"] if s["name"] == "google"][0]
    assert walled["status"] == "失败" and "unusual traffic" in walled["reason"]


# ------------------------------------------- R5 handing over the collecting account

def _cookie_db(profile, host: str, name: str):
    """A Chromium profile that has actually been logged in, as far as disk is concerned."""
    import sqlite3

    path = profile / "Default" / "Network"
    path.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path / "Cookies")
    db.execute("CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT)")
    db.execute("INSERT INTO cookies VALUES (?,?,?)", (host, name, "x"))
    db.commit()
    db.close()


def test_a_browser_that_merely_opened_is_not_a_login(tmp_path, monkeypatch):
    """The first version called any non-empty directory a login — and Chromium writes
    `Default/` the moment it starts, so every profile looked logged in."""
    monkeypatch.setattr(scrape_browser, "SCRAPE_DIR", tmp_path)
    (tmp_path / "instagram" / "Default").mkdir(parents=True)
    (tmp_path / "instagram" / "Default" / "Preferences").write_text("{}", encoding="utf-8")
    assert scrape_browser.logged_in("instagram") is False


def test_a_session_cookie_is_what_counts_as_logged_in(tmp_path, monkeypatch):
    monkeypatch.setattr(scrape_browser, "SCRAPE_DIR", tmp_path)
    _cookie_db(tmp_path / "instagram", ".instagram.com", "sessionid")
    assert scrape_browser.logged_in("instagram") is True


def test_another_sites_cookie_is_not_a_login_here(tmp_path, monkeypatch):
    monkeypatch.setattr(scrape_browser, "SCRAPE_DIR", tmp_path)
    _cookie_db(tmp_path / "instagram", ".example.com", "sessionid")
    assert scrape_browser.logged_in("instagram") is False


def test_the_login_window_opens_the_collecting_profile_and_no_other(tmp_path, monkeypatch):
    from app import playwright_engine

    class FakeWindow:
        def poll(self):
            return None

    monkeypatch.setattr(scrape_browser, "SCRAPE_DIR", tmp_path)
    monkeypatch.setattr(scrape_browser, "_LOGIN_WINDOWS", {})
    started: list[list[str]] = []
    monkeypatch.setattr(scrape_browser, "_spawn", lambda argv: started.append(argv) or FakeWindow())
    scrape_browser.start_login("instagram")
    argv = started[0]
    assert "--login" in argv
    profile = argv[argv.index("--profile-dir") + 1]
    assert profile.lower().startswith(str(tmp_path).lower())
    assert not profile.lower().startswith(str(playwright_engine.DATA_DIR).lower())


def test_a_login_that_has_no_window_to_open_is_refused(monkeypatch):
    """Facebook collecting needs no account, so offering to log one in is a lie."""
    with pytest.raises(ValueError):
        scrape_browser.start_login("facebook")


def test_the_panel_can_see_which_collecting_accounts_are_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(scrape_browser, "_LOGIN_WINDOWS", {})
    monkeypatch.setattr(scrape_browser, "SCRAPE_DIR", tmp_path)
    client = _client(tmp_path)
    rows = client.get("/api/channels/scrape").json()["channels"]
    ig = [r for r in rows if r["name"] == "instagram"][0]
    assert ig["logged_in"] is False
    assert "小号" in ig["hint"]
    assert [r["name"] for r in rows] == ["instagram"], "只有真的需要登录的渠道才该出现在这里"


def test_pressing_login_opens_a_window_rather_than_asking_for_a_password(tmp_path, monkeypatch):
    opened: list[str] = []
    monkeypatch.setattr(scrape_browser, "start_login", lambda ch: opened.append(ch))
    client = _client(tmp_path)
    assert client.post("/api/channels/scrape/instagram/login").json()["status"] == "等待登录"
    assert opened == ["instagram"]


def test_a_failed_navigation_does_not_take_the_login_window_with_it():
    """Measured 2026-09-11: the first launch got ERR_HTTP_RESPONSE_CODE_FAILURE from
    Instagram and every launch after it got 200 — and that one failure closed the
    window, which is all Allen saw of it."""
    class Page:
        calls = 0

        def goto(self, url, **kw):
            Page.calls += 1
            raise RuntimeError("net::ERR_HTTP_RESPONSE_CODE_FAILURE at https://x/")

    reason = scrape_runner.open_login_page(Page(), "https://www.instagram.com/")
    assert Page.calls == 2, "一次偶发失败值得重试一次"
    assert "ERR_HTTP_RESPONSE_CODE_FAILURE" in reason, "窗口留着，但要说得出为什么是错误页"


def test_a_navigation_that_works_is_not_retried():
    class Page:
        calls = 0

        def goto(self, url, **kw):
            Page.calls += 1

    assert scrape_runner.open_login_page(Page(), "https://www.instagram.com/") == ""
    assert Page.calls == 1


# ------------------------------ R5 a window that says "I am a robot" gets no captcha

class FakePlay:
    """Stands in for sync_playwright()'s chromium, remembering how it was launched."""

    def __init__(self, fail_channels=(), fail_once=False):
        self.calls: list[dict] = []
        self.fail_channels = fail_channels
        self.fail_once = fail_once
        self.chromium = self

    def launch_persistent_context(self, profile, **kw):
        self.calls.append({"profile": profile, **kw})
        if kw.get("channel") in self.fail_channels:
            raise RuntimeError("Executable doesn't exist: chrome")
        if self.fail_once and len(self.calls) == 1:
            raise RuntimeError("ProcessSingleton: profile is already in use")
        return f"ctx{len(self.calls)}"


def test_a_headed_window_is_a_real_chrome_with_the_automation_flag_off():
    """Measured 2026-09-11: Playwright's own Chromium reports navigator.webdriver=true
    and brands itself Chromium, and Meta answered Allen's login with a captcha page that
    never drew the captcha. Real Chrome with --enable-automation removed reports false
    and brands itself Google Chrome."""
    play = FakePlay()
    scrape_runner.launch_quiet(play, "C:/prof", headless=False)
    call = play.calls[0]
    assert call["channel"] == "chrome"
    assert "--enable-automation" in call["ignore_default_args"]
    assert any("AutomationControlled" in a for a in call["args"])
    assert call["headless"] is False


def test_a_machine_without_chrome_still_gets_a_window():
    play = FakePlay(fail_channels=("chrome",))
    scrape_runner.launch_quiet(play, "C:/prof", headless=False)
    assert [c.get("channel") for c in play.calls] == ["chrome", None]


def test_the_headless_readers_keep_the_browser_they_were_measured_with():
    """Facebook's public pages are read headless today and work; nothing to fix there."""
    play = FakePlay()
    scrape_runner.launch_quiet(play, "C:/prof", headless=True)
    assert play.calls[0].get("channel") is None


def test_a_leftover_window_holding_the_profile_is_cleared_and_the_launch_retried(monkeypatch):
    """The sending engine already carries this scar: an orphan keeps the profile locked
    and every later launch dies (`playwright_engine._kill_stale_browser`)."""
    killed: list[str] = []
    monkeypatch.setattr(scrape_runner, "kill_stale", lambda prof: killed.append(prof))
    monkeypatch.setattr(scrape_runner.time, "sleep", lambda *_: None)
    play = FakePlay(fail_once=True)
    assert scrape_runner.launch_quiet(play, "C:/prof", headless=False) == "ctx2"
    assert killed == ["C:/prof"]
