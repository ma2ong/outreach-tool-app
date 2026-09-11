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
    assert row["optional"]


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
    assert scrape_runner.bio_host(
        ["https://www.instagram.com/ledworld_mx/", "https://help.instagram.com/x",
         "https://ledworld.mx/contacto"]) == "ledworld.mx"


# --------------------------------------------------- R5 the reader must be declared

def test_a_channel_declares_its_readers_cheapest_first():
    assert ds.SOURCES["duckduckgo"].engines == ("http",)
    assert ds.SOURCES["google"].engines == ("playwright", "browser")
    # docs/128 R7: the prose was never behind the browser, so the free reader goes first.
    assert ds.SOURCES["naver-blog"].engines == ("http", "browser")


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


def test_a_channel_that_is_not_switched_on_is_refused_before_the_job_exists(tmp_path, monkeypatch):
    """docs/124 R5: an unconfigured channel is something to say now, not a job that
    finishes empty."""
    monkeypatch.setattr(scrape_browser, "logged_in", lambda channel: False)
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
    monkeypatch.setattr(scrape_browser, "chrome_path", lambda: "C:/Chrome/chrome.exe")
    scrape_browser.start_login("instagram")
    argv = started[0]
    profile = [a for a in argv if a.startswith("--user-data-dir=")][0].split("=", 1)[1]
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


# ------------------------ R5 the login window is an ordinary Chrome, not a driven one

def test_the_login_window_is_a_plain_chrome_with_no_automation_attached(tmp_path, monkeypatch):
    """Measured 2026-09-11: Allen's own Chrome logs in on this machine and this IP, and
    a Playwright-driven one is answered with a captcha page that never draws its
    captcha — real Chrome build, navigator.webdriver false and all. What is left is CDP,
    and CDP is not a flag that can be turned off. So the login is not driven at all."""
    monkeypatch.setattr(scrape_browser, "SCRAPE_DIR", tmp_path)
    monkeypatch.setattr(scrape_browser, "_LOGIN_WINDOWS", {})
    monkeypatch.setattr(scrape_browser, "chrome_path", lambda: "C:/Chrome/chrome.exe")
    started: list[list[str]] = []

    class FakeWindow:
        def poll(self):
            return None

    monkeypatch.setattr(scrape_browser, "_spawn", lambda argv: started.append(argv) or FakeWindow())
    scrape_browser.start_login("instagram")
    argv = started[0]
    assert argv[0] == "C:/Chrome/chrome.exe"
    assert not any("scrape_runner" in a or "playwright" in a.lower() for a in argv), argv
    assert any(a.startswith("--user-data-dir=") for a in argv)
    profile = [a for a in argv if a.startswith("--user-data-dir=")][0]
    assert str(tmp_path).lower() in profile.lower()
    assert argv[-1].startswith("https://www.instagram.com")


def test_without_chrome_the_login_says_so_rather_than_opening_nothing(monkeypatch):
    monkeypatch.setattr(scrape_browser, "chrome_path", lambda: "")
    with pytest.raises(scrape_browser.Unavailable) as caught:
        scrape_browser.start_login("instagram")
    assert "Chrome" in str(caught.value)


def test_chrome_is_found_where_windows_actually_puts_it(monkeypatch):
    seen = {"C:/Program Files/Google/Chrome/Application/chrome.exe"}
    monkeypatch.setattr(scrape_browser.os.path, "isfile", lambda p: p.replace("\\", "/") in seen)
    assert scrape_browser.chrome_path().replace("\\", "/").endswith("chrome.exe")


# --------------------- R5 the other way in: a session made in Allen's own Chrome

def _chrome_tree(root, folders):
    """A Chrome User Data directory, as Windows lays it out."""
    import json as _json

    (root / "Default").mkdir(parents=True)
    info = {}
    for folder, name in folders.items():
        (root / folder / "Network").mkdir(parents=True, exist_ok=True)
        (root / folder / "Network" / "Cookies").write_bytes(b"cookiedb")
        info[folder] = {"name": name}
    (root / "Local State").write_text(
        _json.dumps({"profile": {"info_cache": info},
                     "os_crypt": {"encrypted_key": "x"}}), encoding="utf-8")
    return root


def test_the_chrome_profiles_are_listed_by_the_name_allen_gave_them(tmp_path, monkeypatch):
    root = _chrome_tree(tmp_path / "User Data", {"Default": "Allen", "Profile 3": "采集小号"})
    monkeypatch.setattr(scrape_browser, "chrome_user_data", lambda: root)
    assert {p["folder"]: p["name"] for p in scrape_browser.chrome_profiles()} == {
        "Default": "Allen", "Profile 3": "采集小号"}


def test_importing_a_profile_brings_the_session_and_the_key_that_decrypts_it(tmp_path, monkeypatch):
    """Measured 2026-09-11: a copied profile carries datr/mid/ig_did and Chrome still
    decrypts them — but only with `Local State`, which holds the key."""
    root = _chrome_tree(tmp_path / "User Data", {"Profile 3": "采集小号"})
    monkeypatch.setattr(scrape_browser, "chrome_user_data", lambda: root)
    monkeypatch.setattr(scrape_browser, "SCRAPE_DIR", tmp_path / "scrape")
    monkeypatch.setattr(scrape_browser, "chrome_is_running", lambda: False)

    scrape_browser.import_login("instagram", "Profile 3")
    target = scrape_browser.profile_dir("instagram")
    assert (target / "Default" / "Network" / "Cookies").read_bytes() == b"cookiedb"
    assert (target / "Local State").is_file(), "没有这把钥匙，cookie 解不开"


def test_importing_while_chrome_is_open_is_refused_rather_than_half_copied(tmp_path, monkeypatch):
    root = _chrome_tree(tmp_path / "User Data", {"Profile 3": "采集小号"})
    monkeypatch.setattr(scrape_browser, "chrome_user_data", lambda: root)
    monkeypatch.setattr(scrape_browser, "SCRAPE_DIR", tmp_path / "scrape")
    monkeypatch.setattr(scrape_browser, "chrome_is_running", lambda: True)
    with pytest.raises(scrape_browser.Unavailable) as caught:
        scrape_browser.import_login("instagram", "Profile 3")
    assert "关掉 Chrome" in str(caught.value)


def test_importing_an_unknown_profile_is_refused(tmp_path, monkeypatch):
    root = _chrome_tree(tmp_path / "User Data", {"Profile 3": "采集小号"})
    monkeypatch.setattr(scrape_browser, "chrome_user_data", lambda: root)
    monkeypatch.setattr(scrape_browser, "SCRAPE_DIR", tmp_path / "scrape")
    monkeypatch.setattr(scrape_browser, "chrome_is_running", lambda: False)
    for bad in ("Profile 9", "../../Windows", ""):
        with pytest.raises(ValueError):
            scrape_browser.import_login("instagram", bad)


def test_a_collecting_profile_never_offers_to_fill_a_password(tmp_path, monkeypatch):
    """Chrome saved a wrong password into the collecting profile and then filled it in
    on every attempt, so the account it kept submitting was not the one Allen meant."""
    monkeypatch.setattr(scrape_browser, "SCRAPE_DIR", tmp_path)
    monkeypatch.setattr(scrape_browser, "_LOGIN_WINDOWS", {})
    monkeypatch.setattr(scrape_browser, "chrome_path", lambda: "C:/Chrome/chrome.exe")
    monkeypatch.setattr(scrape_browser, "_spawn", lambda argv: None)
    scrape_browser.start_login("instagram")

    import json as _json
    prefs = _json.loads((scrape_browser.profile_dir("instagram") / "Default" / "Preferences")
                        .read_text(encoding="utf-8"))
    assert prefs["credentials_enable_service"] is False
    assert prefs["profile"]["password_manager_enabled"] is False
    assert prefs["autofill"]["profile_enabled"] is False


def test_seeding_leaves_a_profile_that_is_already_logged_in_alone(tmp_path, monkeypatch):
    """Rewriting the preferences of a working profile would be a way to break one."""
    monkeypatch.setattr(scrape_browser, "SCRAPE_DIR", tmp_path)
    monkeypatch.setattr(scrape_browser, "_LOGIN_WINDOWS", {})
    monkeypatch.setattr(scrape_browser, "chrome_path", lambda: "C:/Chrome/chrome.exe")
    monkeypatch.setattr(scrape_browser, "_spawn", lambda argv: None)
    monkeypatch.setattr(scrape_browser, "logged_in", lambda ch: True)
    target = scrape_browser.profile_dir("instagram") / "Default"
    target.mkdir(parents=True)
    (target / "Preferences").write_text('{"mine": 1}', encoding="utf-8")
    scrape_browser.start_login("instagram")
    assert (target / "Preferences").read_text(encoding="utf-8") == '{"mine": 1}'


# ---------------------------- R5 reading Instagram with the session Allen handed over

# Measured 2026-09-11 on the real profiles: the bio link is wrapped in Instagram's own
# redirector, and Meta's footer links sit on every page below it.
_REAL_HREFS = [
    "https://l.instagram.com/?u=https%3A%2F%2Fwww.pantallasledlemon.com%2F%3Futm_source"
    "%3Dig%26utm_medium%3Dsocial%26fbclid%3DPAcGRvZg&e=AUCzL-6ugMjXBqR2",
    "https://about.meta.com/", "https://developers.facebook.com/docs/instagram",
    "https://www.meta.ai/?utm_source=foa_web_footer", "https://muse.ai/",
    "https://www.threads.com/",
]


def test_the_bio_link_is_unwrapped_from_instagrams_redirector():
    assert scrape_runner.bio_host(_REAL_HREFS) == "pantallasledlemon.com"


def test_metas_own_footer_is_never_a_company():
    """about.meta.com, muse.ai and threads.com are on every profile page there is."""
    assert scrape_runner.bio_host(_REAL_HREFS[1:]) == ""


def test_the_search_reads_the_accounts_instagram_returned():
    payload = ('{"users": [{"user": {"username": "pantallasledlemon", "full_name": "LedLemon"}},'
               ' {"user": {"username": "pantallasledperu", "full_name": "Pantallas Led Peru"}}],'
               ' "places": [{"place": {"title": "x"}}]}')
    assert scrape_runner.instagram_users(payload, 5) == ["pantallasledlemon", "pantallasledperu"]


def test_a_search_that_matches_no_account_name_is_empty_not_broken():
    """Measured: Instagram matches account names, not descriptions — `led display
    distributor` returns nothing while `pantallas led` returns five real companies."""
    assert scrape_runner.instagram_users('{"users": []}', 5) == []


def test_being_rate_limited_is_reported_rather_than_returned_as_no_companies():
    """docs/128 R2: 429 is Instagram saying "not now", not the market saying "nobody"."""
    with pytest.raises(RuntimeError) as caught:
        scrape_runner.instagram_users("<!DOCTYPE html><html>...", 5, status=429)
    assert "429" in str(caught.value)


def test_a_chat_shortcut_in_the_bio_is_not_a_company_site():
    """Measured: `pantallas led` returned wa.link alongside two real company sites —
    a WhatsApp shortcut is a way to reach someone, not an address to enrich."""
    assert scrape_runner.bio_host(["https://l.instagram.com/?u=https%3A%2F%2Fwa.link%2Fabc"]) == ""
    assert scrape_runner.bio_host(["https://wa.me/34600111222"]) == ""


def test_an_account_arrives_carrying_the_handle_its_dms_would_go_to(monkeypatch):
    monkeypatch.setattr(scrape_browser, "read_search",
                        lambda channel, query, limit=20: {
                            "hosts": ["exctecled.com"],
                            "pages": [{"handle": "pantallasledperu", "domain": "exctecled.com"},
                                      {"handle": "noSite", "domain": ""}]})
    out = ds.instagram_accounts("pantallas led", 5)
    assert out == [{"domain": "exctecled.com", "website": "exctecled.com",
                    "source": "instagram", "instagram": "pantallasledperu"}]


# ================= docs/128 R7 — the two channels that no longer need a person

def test_the_blog_channel_reads_prose_without_opening_a_browser(monkeypatch):
    """Measured 2026-09-11: jina returns 85,749 characters of blog text in 12s and one
    DeepSeek call pulls the company names out of it in 1.6s. browser-use spent 85-121s
    and a visible window doing the same job."""
    monkeypatch.setattr(ds, "_blog_text", lambda query: "…한빛테크… 아바비젼 …")
    monkeypatch.setattr(ds, "_names_from_prose",
                        lambda text, limit: ["아바비젼", "키다LED"])
    monkeypatch.setattr(ds, "_domain_for_name",
                        lambda name: "avavision.co.kr" if name == "아바비젼" else "")
    assert ds.naver_blog_prose("LED 전광판 유통업체", 5) == [
        {"domain": "avavision.co.kr", "website": "avavision.co.kr",
         "country": "South Korea", "source": "naver-blog"}]


def test_the_blog_channel_declares_the_cheap_reader_first_and_may_run_alone():
    source = ds.SOURCES["naver-blog"]
    assert source.engines == ("http", "browser")
    assert source.unattended is True


def test_instagram_may_run_alone_because_headless_opens_no_window():
    """docs/126 R5 kept every logged-in reader attended on the assumption that it would
    pop a window. Measured: headless reads the same accounts and the same bio links."""
    assert ds.SOURCES["instagram"].unattended is True


def test_no_unattended_channel_defaults_to_a_reader_that_opens_a_window():
    """The invariant docs/126 R5 was protecting, stated in terms of what actually opens
    a window: browser-use always does, headless Playwright never does."""
    for source in ds.SOURCES.values():
        if source.unattended:
            assert source.engines[0] != "browser", f"{source.name} would pop a window on a timer"


def test_a_phrase_instagram_cannot_match_is_trimmed_to_one_it_can():
    """Measured: `LED video wall installer contact` matches no account at all; `led video
    wall` matches four and yields churchleds.com and distinctled.com."""
    assert ds.instagram_query("LED video wall installer contact") == "LED video wall"
    assert ds.instagram_query("pantallas led") == "pantallas led"
    assert ds.instagram_query("  led   wall  ") == "led wall"


def test_an_unattended_instagram_run_is_capped(monkeypatch):
    """A nightly run must not walk twenty profiles per keyword on a spare account."""
    asked: list[int] = []
    monkeypatch.setattr(scrape_browser, "read_search",
                        lambda channel, query, limit=20: asked.append(limit) or
                        {"hosts": [], "pages": []})
    ds.instagram_accounts("pantallas led", 20)
    assert asked == [ds.MAX_INSTAGRAM_PROFILES]


def test_the_nightly_keywords_are_short_terms_not_sentences():
    """docs/128 R7: a description matches no Instagram account and narrows every other
    channel too. The nightly fallback used four sentences; it now uses short terms."""
    from app.agent import mission

    for phrase in mission._SEARCHES:
        assert len(phrase.split()) <= 3, f"{phrase} 是一句描述，不是一个词"


def test_a_korean_keyword_does_not_get_an_english_market_stapled_to_it():
    """`led전광판 USA` is a query nobody wants: a Korean term already names its market."""
    from app.agent import executors

    assert executors.market_query("led display", "USA") == "led display USA"
    assert executors.market_query("led전광판", "USA") == "led전광판"
    assert executors.market_query("led display", None) == "led display"
