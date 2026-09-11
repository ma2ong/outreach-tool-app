import app.main as main
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path):
    db = str(tmp_path / "t.db")
    c = connect(db)
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, website, email, phone, stage) VALUES
            (1, 'Ara System', 'South Korea', 'arasystem.kr', 'i@arasystem.kr', '+827048950794', 'new'),
            (2, 'GLD LED', 'South Korea', 'gldled.com', NULL, '+8613809866355', 'new'),
            (3, 'Alibaba', 'China', 'alibaba.com', NULL, NULL, 'new');
    """)
    c.commit()
    c.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    return TestClient(main.app), db


def test_scan_endpoint(tmp_path):
    client, _ = _client(tmp_path)
    r = client.get("/api/health/scan").json()
    assert r["issues"]["peer"][0]["no"] == 2
    assert r["issues"]["directory"][0]["no"] == 3
    assert r["total"] >= 2


def test_fix_endpoint_suppresses(tmp_path):
    client, db = _client(tmp_path)
    r = client.post("/api/health/fix", json={"issues": ["peer", "directory"]})
    assert r.json() == {"peer": 1, "directory": 1}
    conn = connect(db)
    dnc = {x["no"] for x in conn.execute("SELECT no FROM leads WHERE do_not_contact=1")}
    assert dnc == {2, 3}
    # scanning again finds nothing to suppress
    assert "peer" not in client.get("/api/health/scan").json()["issues"]


def test_seed_loads_templates_and_sequences(tmp_path):
    client, _ = _client(tmp_path)
    r = client.post("/api/seeds/load").json()
    assert r["templates"] > 0 and len(r["sequence_ids"]) == 6  # 3 types x 2 langs
    email_tpls = client.get("/api/templates?channel=email").json()
    assert any("冷邮件 · 中性版" in t["name"] for t in email_tpls)
    # Korea gets Korean, every other market gets English — and nothing else ships.
    assert {t["lang"] for t in email_tpls} == {"en", "ko"}
    wa = client.get("/api/templates?channel=whatsapp").json()
    # DM rule: do not mention the recipient company name.
    assert wa and "Maxcolor" not in wa[0]["body"]
    assert "manufactur" in wa[0]["body"] or "make" in wa[0]["body"] or "supply" in wa[0]["body"]
    seqs = client.get("/api/sequences").json()
    assert len(seqs) == 6  # Rental / Install / General x 2 languages
    for s in seqs:
        offsets = [st["day_offset"] for st in s["steps"]]
        # One letter, or three a fortnight apart. English Install and General stop after
        # the opener; Rental and Korean variants retain the existing follow-up cadence.
        assert offsets in ([0], [0, 14, 28]), f"{s['name']} 的节奏是 {offsets}"
    ko = next(s for s in seqs if "韩语·General" in s["name"])
    en = next(s for s in seqs if "英语·Rental" in s["name"])
    # Raw sequence copy delegates the whole first line to the country-aware renderer.
    assert "{greeting}" in ko["steps"][0]["body"]
    assert "{contact}님" not in ko["steps"][0]["body"]
    assert "LED" in ko["steps"][0]["subject"]
    # The Korean copy is natural business Korean and renders safely with no contact name.
    from app.personalize import render
    for step in ko["steps"]:
        rendered = render(step["body"], {"company_en": "Ara System",
                                         "country": "South Korea", "contact_name": None})
        assert rendered.startswith("안녕하세요.")
        assert "{contact}" not in rendered and ", 님" not in rendered
        assert "Kakaotalk" in rendered and "WhatsApp" not in rendered
    # Neither language carries an opt-out paragraph; suppression comes from the reply.
    for s_ in seqs:
        for step in s_["steps"]:
            assert "unsubscribe" not in step["body"].lower()
            assert "수신거부" not in step["body"]
    # Every opener puts a real pixel pitch in front of the reader, in both languages.
    import re
    for opener in (ko["steps"][0]["body"], en["steps"][0]["body"]):
        assert re.search(r"P\d", opener)
    # No subject names the company.
    for s_ in seqs:
        for step in s_["steps"]:
            assert "{company}" not in (step["subject"] or "")


def test_seeded_greeting_never_says_hi_there(tmp_path):
    """The greeting has to survive a lead with no contact name — most of them."""
    from app.personalize import render
    from app import seeds
    body = next(b for n, l, s_, b in seeds.EMAIL_TEMPLATES if l == "en")
    named = render(body, {"company_en": "Acme", "country": "USA", "contact_name": "Dave Miller"})
    bare = render(body, {"company_en": "Acme", "country": "USA", "contact_name": None})
    assert named.startswith("Hi Dave,")
    assert bare.startswith("Hi,")          # not "Hi there," and not "Hi ,"
    assert "there" not in bare.splitlines()[0]


def test_seed_is_idempotent(tmp_path):
    client, _ = _client(tmp_path)
    first = client.post("/api/seeds/load").json()
    second = client.post("/api/seeds/load").json()
    assert second["templates"] == 0 and second["sequence_ids"] == []
    assert len(client.get("/api/templates").json()) == first["templates"]
    assert len(client.get("/api/sequences").json()) == 6
