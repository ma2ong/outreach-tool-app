import pytest

from app.playwright_engine import PlaywrightEngine


class FakePage:
    def __init__(self, closed=False):
        self._closed = closed

    def is_closed(self):
        return self._closed


class DeadContext:
    """A closed Playwright context: `.pages` answers with an empty list rather than
    raising, which is why checking it was never a liveness test."""

    pages: list = []

    def new_page(self):
        raise RuntimeError("Target page, context or browser has been closed")


class LiveContext:
    def __init__(self, pages=None):
        self.pages = pages or []
        self.opened = 0

    def new_page(self):
        self.opened += 1
        return FakePage()


def _engine(monkeypatch, launches):
    """An engine whose _launch hands back the given contexts in order.

    `_ctx` is created on the worker thread in production, so the test creates it here.
    """
    eng = PlaywrightEngine()
    eng._ctx = {}
    seq = list(launches)
    monkeypatch.setattr(eng, "_launch", lambda prof: seq.pop(0))
    return eng


def test_a_dead_cached_context_is_replaced_instead_of_reused(monkeypatch, tmp_path):
    """Instagram sat unusable this way: the dead context stayed cached, so every retry
    failed the same way and reconnecting could never work."""
    monkeypatch.setattr("app.playwright_engine.DATA_DIR", tmp_path)
    live = LiveContext()
    eng = _engine(monkeypatch, [live])
    eng._ctx["instagram"] = DeadContext()
    page = eng._page("instagram")
    assert isinstance(page, FakePage)
    assert eng._ctx["instagram"] is live


def test_an_existing_open_page_is_reused(monkeypatch, tmp_path):
    monkeypatch.setattr("app.playwright_engine.DATA_DIR", tmp_path)
    open_page = FakePage()
    ctx = LiveContext(pages=[open_page])
    eng = _engine(monkeypatch, [])
    eng._ctx["whatsapp"] = ctx
    assert eng._page("whatsapp") is open_page
    assert ctx.opened == 0


def test_a_closed_page_is_not_handed_back(monkeypatch, tmp_path):
    monkeypatch.setattr("app.playwright_engine.DATA_DIR", tmp_path)
    ctx = LiveContext(pages=[FakePage(closed=True)])
    eng = _engine(monkeypatch, [])
    eng._ctx["whatsapp"] = ctx
    page = eng._page("whatsapp")
    assert not page.is_closed() and ctx.opened == 1


def test_a_browser_that_will_not_start_still_reports_the_reason(monkeypatch, tmp_path):
    monkeypatch.setattr("app.playwright_engine.DATA_DIR", tmp_path)
    eng = _engine(monkeypatch, [DeadContext(), DeadContext()])
    with pytest.raises(RuntimeError, match="has been closed"):
        eng._page("facebook")


def test_the_relaunch_is_attempted_once_not_forever(monkeypatch, tmp_path):
    monkeypatch.setattr("app.playwright_engine.DATA_DIR", tmp_path)
    launches = []

    eng = PlaywrightEngine()
    eng._ctx = {}

    def launch(prof):
        launches.append(prof)
        return DeadContext()

    monkeypatch.setattr(eng, "_launch", launch)
    with pytest.raises(RuntimeError):
        eng._page("instagram")
    assert len(launches) == 2
