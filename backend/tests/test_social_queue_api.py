"""The queue API: read, fix, send — and never send by itself."""
import app.main as main
from app.db import connect, init_schema
from fastapi.testclient import TestClient


def _client(tmp_path):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    init_schema(conn)
    rows = ", ".join(
        f"({i}, 'Co{i}', 'USA', 'ig{i}', '+1555000{i:04d}', 'Saw the P{i} video wall on your site.')"
        for i in range(1, 31))
    conn.executescript(
        "INSERT INTO leads(no, company_en, country, instagram, phone, hook)"
        f" VALUES {rows};")
    conn.commit()
    conn.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    # The send runs in a background task that opens its own connection by path.
    from app.api import send as send_api
    send_api.DB_PATH = db
    return TestClient(main.app), db


def test_building_the_queue_prepares_messages_and_sends_nothing(tmp_path, monkeypatch):
    from app.api import channels as channels_api

    client, _ = _client(tmp_path)
    monkeypatch.setattr(channels_api.ENGINE, "send_message",
                        lambda *a, **k: (_ for _ in ()).throw(
                            AssertionError("生成队列绝不允许发送")))
    built = client.post("/api/social-queue/build")
    assert built.status_code == 200 and built.json()["queued"] > 0

    listed = client.get("/api/social-queue").json()
    assert len(listed["items"]) == built.json()["queued"]
    first = listed["items"][0]
    assert "{" not in first["body"] and "video wall on your site" in first["body"]
    assert first["company_en"]  # 列表要能看出是发给谁的


def test_allen_can_fix_or_drop_a_line_before_sending(tmp_path):
    client, _ = _client(tmp_path)
    client.post("/api/social-queue/build")
    items = client.get("/api/social-queue").json()["items"]

    assert client.patch(f"/api/social-queue/{items[0]['id']}",
                        json={"body": "我自己改过的一句"}).status_code == 200
    assert client.delete(f"/api/social-queue/{items[1]['id']}").status_code == 200

    after = client.get("/api/social-queue").json()["items"]
    assert after[0]["body"] == "我自己改过的一句" and after[0]["edited"] == 1
    assert items[1]["id"] not in {r["id"] for r in after}


def test_sending_goes_out_one_written_message_per_company(tmp_path, monkeypatch):
    """Each line is its own sentence — the send path must not collapse them into one
    template, and must keep the pacing and bookkeeping of the manual panel."""
    from app import channel_outreach
    from app.api import channels as channels_api

    client, db = _client(tmp_path)
    client.post("/api/social-queue/build")
    items = client.get("/api/social-queue").json()["items"][:3]

    sent = []
    monkeypatch.setattr(channels_api.ENGINE, "send_message",
                        lambda channel, target, body, image: sent.append((channel, target, body)))
    monkeypatch.setattr(channel_outreach.time, "sleep", lambda *_: None)
    r = client.post("/api/social-queue/send", json={"ids": [i["id"] for i in items]})
    assert r.status_code == 200 and r.json()["will_send"] == 3

    job = client.get(f"/api/send/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "done" and job["result"]["sent"] == 3, job
    assert len({body for _, _, body in sent}) == 3, "三条正文必须各不相同"

    conn = connect(db)
    assert conn.execute("SELECT COUNT(*) c FROM send_log").fetchone()["c"] == 3
    assert conn.execute(
        "SELECT COUNT(*) c FROM social_dm_queue WHERE status='sent'").fetchone()["c"] == 3
    conn.close()


def test_a_sent_line_cannot_be_edited_or_resent(tmp_path, monkeypatch):
    from app import channel_outreach
    from app.api import channels as channels_api

    client, _ = _client(tmp_path)
    client.post("/api/social-queue/build")
    item = client.get("/api/social-queue").json()["items"][0]
    monkeypatch.setattr(channels_api.ENGINE, "send_message", lambda *a, **k: None)
    monkeypatch.setattr(channel_outreach.time, "sleep", lambda *_: None)
    client.post("/api/social-queue/send", json={"ids": [item["id"]]})

    assert client.patch(f"/api/social-queue/{item['id']}", json={"body": "x"}).status_code == 404
    assert client.post("/api/social-queue/send", json={"ids": [item["id"]]}).status_code == 400
