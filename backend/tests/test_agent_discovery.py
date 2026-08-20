import json

from app.agent import proposals


def _candidates(*names):
    """The shape discovery actually returns: keyed on `domain`, named by `title`."""
    return [{"domain": f"{n.lower()}.com", "title": n, "email": f"a@{n.lower()}.com",
             "country": "USA", "excluded": False} for n in names]


def test_the_candidates_survive_the_run(conn, monkeypatch):
    """They used to be counted and thrown away, while the result line sent Allen to a
    page that had never received them."""
    monkeypatch.setattr("app.discovery.run_discovery",
                        lambda c, q, limit=10: _candidates("Alpha", "Beta"))
    p = proposals.create(conn, "discover_run", title="找美国经销商",
                         payload={"queries": ["LED distributor"], "country": "USA"})
    done = proposals.approve(conn, p["id"])
    assert done["status"] == "executed"
    found = done["payload"]["found"]
    assert [c["title"] for c in found] == ["Alpha", "Beta"]
    assert "展开勾选导入" in done["execution_result"]


def test_the_same_company_from_two_queries_is_kept_once(conn, monkeypatch):
    monkeypatch.setattr("app.discovery.run_discovery",
                        lambda c, q, limit=10: _candidates("Alpha"))
    p = proposals.create(conn, "discover_run", title="两条关键词",
                         payload={"queries": ["a", "b"], "country": None})
    done = proposals.approve(conn, p["id"])
    assert len(done["payload"]["found"]) == 1


def test_nothing_is_imported_by_running_a_search(conn, monkeypatch):
    before = conn.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"]
    monkeypatch.setattr("app.discovery.run_discovery",
                        lambda c, q, limit=10: _candidates("Alpha", "Beta"))
    p = proposals.create(conn, "discover_run", title="搜索",
                         payload={"queries": ["x"], "country": None})
    proposals.approve(conn, p["id"])
    assert conn.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"] == before


def test_excluded_candidates_are_kept_but_not_counted_as_usable(conn, monkeypatch):
    cands = _candidates("Alpha")
    cands.append({"domain": "peer.cn", "title": "Shenzhen Peer", "excluded": True,
                  "exclude_reason": "中国同行"})
    monkeypatch.setattr("app.discovery.run_discovery", lambda c, q, limit=10: cands)
    p = proposals.create(conn, "discover_run", title="搜索",
                         payload={"queries": ["x"], "country": None})
    done = proposals.approve(conn, p["id"])
    assert len(done["payload"]["found"]) == 2
    assert "2 个候选（其中 1 个可用）" in done["execution_result"]


def test_a_search_that_finds_nothing_says_so(conn, monkeypatch):
    monkeypatch.setattr("app.discovery.run_discovery", lambda c, q, limit=10: [])
    p = proposals.create(conn, "discover_run", title="搜索",
                         payload={"queries": ["x"], "country": None})
    done = proposals.approve(conn, p["id"])
    assert done["status"] == "executed"
    assert done["payload"]["found"] == []
    assert "0 个候选" in done["execution_result"]


def test_a_candidate_without_a_domain_is_not_silently_dropped(conn, monkeypatch):
    """Keying on the wrong field once dropped every result and reported zero found."""
    monkeypatch.setattr("app.discovery.run_discovery", lambda c, q, limit=10: [
        {"domain": "alpha.com", "title": None, "email": "a@alpha.com", "excluded": False},
    ])
    p = proposals.create(conn, "discover_run", title="搜索",
                         payload={"queries": ["x"], "country": None})
    done = proposals.approve(conn, p["id"])
    assert len(done["payload"]["found"]) == 1
    assert "1 个候选（其中 1 个可用）" in done["execution_result"]
