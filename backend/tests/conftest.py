import pytest
from app.db import connect, init_schema


@pytest.fixture(autouse=True)
def _never_touch_the_live_db(tmp_path, monkeypatch):
    """No test may reach the real outreach.db.

    DB_PATH defaults to a bare 'outreach.db' and pytest runs from backend/, so any code
    path that connects by DB_PATH instead of the injected connection lands on the live
    lead base. Overriding the module attributes (not just the env var) closes it for
    good, whatever a test forgets.
    """
    from app import main, main_deps
    sandbox = str(tmp_path / "sandbox.db")
    monkeypatch.setenv("OUTREACH_DB", sandbox)
    monkeypatch.setattr(main_deps, "DB_PATH", sandbox)
    monkeypatch.setattr(main, "DB_PATH", sandbox)


@pytest.fixture(autouse=True)
def _auth_disabled(tmp_path, monkeypatch):
    """Tests run in local no-password mode; test_auth.py opts back in via its own paths."""
    from app import auth
    monkeypatch.setattr(auth, "PASSWORD_FILE", str(tmp_path / "no_pw.txt"))
    monkeypatch.setattr(auth, "SESSION_KEY_FILE", str(tmp_path / ".session_key"))
    # Every external/background capability is disabled explicitly. Email polling is no
    # longer a master switch, and the durable runtime can also start an embedded leader,
    # so tests disable each source of live I/O/threading independently.
    monkeypatch.setenv("OUTREACH_AUTO_POLL", "0")
    monkeypatch.setenv("OUTREACH_AUTO_SCAN", "0")
    monkeypatch.setenv("OUTREACH_AUTO_RECHECK", "0")
    monkeypatch.setenv("OUTREACH_AUTO_RESEARCH", "0")
    monkeypatch.setenv("OUTREACH_AUTOSEND_SCHEDULER", "0")
    monkeypatch.setenv("OUTREACH_EMBEDDED_WORKER", "0")
    # never let a test reach a real model backend via the startup operating loop
    monkeypatch.setenv("OUTREACH_AGENT", "0")


@pytest.fixture(autouse=True)
def _never_call_a_live_model(monkeypatch):
    """AGENTS.md：测试永不调用真实模型。

    这条是 docs/97 把 `hook_writer` 接进 `social_watch` 之后才发现缺的 —— 两个社媒
    测试真的打了 DeepSeek 的接口，因为 `backend/deepseek_key.txt` 就在仓库里，而
    `complete_json` 找得到它。挡在 `_call_backend` 这一层：换掉 `complete_json` 的
    测试照常工作，忘了换的测试会拿到「后端不可用」，而不是一次真实调用。
    """
    from app.agent import llm

    def refuse(*args, **kwargs):
        raise llm.LLMUnavailable("测试里不调用真实模型")

    # 挡在最底下那三个真正发请求的函数上，不挡 `_call_backend` —— 后端选择和降级
    # 本身是有测试的，它们替换的正是这三个，替换发生在这条 fixture 之后，覆盖得掉。
    for transport in ("_call_cli", "_call_deepseek", "_call_api"):
        monkeypatch.setattr(llm, transport, refuse)


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        -- docs/89: a company whose address was read off its own site is the normal
        -- case; the seed says so, so tests about other things are not silently
        -- testing the provenance gate.
        INSERT INTO leads(no, company_en, country, website, instagram, email_source) VALUES
            (1, 'Alpha AV', 'USA', 'alpha.com', 'alphaig', 'site.contact-page'),
            (2, 'Beta Screens', 'USA', 'beta.com', NULL, 'site.contact-page'),
            (3, 'Gamma LED', 'Brazil', 'gamma.com', 'gammaig', 'site.contact-page');
        INSERT INTO outreach(lead_no, channel, status, touch_count, message_sent_date) VALUES
            (1, 'email', 'messaged', 1, '2026-07-01'),
            (2, 'email', 'prospect', 0, NULL),
            (1, 'instagram', 'messaged', 1, '2026-07-01'),
            (3, 'whatsapp', 'messaged', 1, '2026-06-30');
    """)
    c.commit()
    return c
