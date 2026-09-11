import io
from pathlib import Path

from app import startup


class _Response:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.payload


def test_port_owner_recognizes_existing_outreach(monkeypatch):
    monkeypatch.setattr(startup.request, "urlopen", lambda *_a, **_k: _Response(
        b'{"app":"mcvisual-outreach-tool"}'))
    assert startup.port_owner() == "outreach"


def test_port_owner_reports_other_listener(monkeypatch):
    monkeypatch.setattr(startup.request, "urlopen",
                        lambda *_a, **_k: (_ for _ in ()).throw(OSError("not http")))
    monkeypatch.setattr(startup.socket, "create_connection",
                        lambda *_a, **_k: io.BytesIO())
    assert startup.port_owner() == "other"


def test_port_owner_reports_free_port(monkeypatch):
    monkeypatch.setattr(startup.request, "urlopen",
                        lambda *_a, **_k: (_ for _ in ()).throw(OSError("down")))
    monkeypatch.setattr(startup.socket, "create_connection",
                        lambda *_a, **_k: (_ for _ in ()).throw(OSError("refused")))
    assert startup.port_owner() == "free"


def test_wait_for_outreach_tolerates_startup_delay(monkeypatch):
    owners = iter(("free", "free", "outreach"))
    monkeypatch.setattr(startup, "port_owner", lambda: next(owners))
    monkeypatch.setattr(startup.time, "monotonic", lambda: 0.0)
    monkeypatch.setattr(startup.time, "sleep", lambda _seconds: None)
    assert startup.wait_for_outreach(timeout=30) is True


def test_wait_for_outreach_stops_for_a_foreign_listener(monkeypatch):
    monkeypatch.setattr(startup, "port_owner", lambda: "other")
    assert startup.wait_for_outreach(timeout=30) is False


def test_all_supported_windows_launchers_use_the_checked_runner():
    root = Path(__file__).resolve().parents[2]
    for name in ("start.bat", "start_online.bat"):
        source = (root / name).read_text(encoding="utf-8")
        assert "scripts\\run_server.py" in source
        assert "python -m uvicorn" not in source
        assert "from app.startup import wait_for_outreach" in source
