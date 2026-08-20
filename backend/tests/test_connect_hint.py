from app.api.channels import _connect_hint


def test_a_missing_browser_says_so_and_gives_the_command():
    """The old message blamed a leftover browser window for every failure. When
    Playwright's chromium was simply absent, that sent Allen hunting for windows that
    did not exist while the fix was one command."""
    exc = Exception(
        "BrowserType.launch_persistent_context: Executable doesn't exist at "
        r"C:\Users\x\AppData\Local\ms-playwright\chromium-1217\chrome-win64\chrome.exe"
        "\nPlease run the following command to download new browsers:\n"
        "    playwright install")
    hint = _connect_hint(exc)
    assert "python -m playwright install chromium" in hint
    assert "不用重新扫码" in hint
    assert "占着登录数据" not in hint


def test_a_locked_profile_still_gets_the_window_advice():
    hint = _connect_hint(Exception("ProcessSingleton: profile is already in use"))
    assert "占着登录数据" in hint
    assert "playwright install" not in hint


def test_a_timeout_says_it_timed_out():
    hint = _connect_hint(Exception("Timeout 30000ms exceeded"))
    assert "超时" in hint


def test_an_unrecognised_failure_is_passed_through_not_guessed_at():
    hint = _connect_hint(Exception("something nobody has seen before"))
    assert "something nobody has seen before" in hint
    assert "占着登录数据" not in hint


def test_a_very_long_error_is_trimmed():
    assert len(_connect_hint(Exception("x" * 5000))) < 400


def test_the_readiness_centre_flags_a_missing_browser(conn, monkeypatch):
    """Before this, a missing chromium was invisible until a 502 on the connect button."""
    from app import readiness
    monkeypatch.setattr(readiness, "browser_installed", lambda: False)
    check = next(c for c in readiness.build(conn)["checks"] if c["id"] == "browser")
    assert check["status"] == "blocked"
    assert "playwright install chromium" in check["detail"]


def test_an_installed_browser_raises_no_check(conn, monkeypatch):
    from app import readiness
    monkeypatch.setattr(readiness, "browser_installed", lambda: True)
    assert not [c for c in readiness.build(conn)["checks"] if c["id"] == "browser"]
