import datetime as dt

from app import contacts, decision_maker_radar, opportunities, people_detector, search
from app.agent import customer360, proposals


TODAY = dt.date(2026, 8, 21)


def test_people_detector_requires_named_person_and_relevant_title():
    assert people_detector.detect_page(
        "https://alpha.com/about", "Our Purchasing Manager handles all vendors.", "alpha.com"
    ) == []
    assert people_detector.detect_page(
        "https://alpha.com/team", "## Jane Smith\nAccountant\njane@alpha.com", "alpha.com"
    ) == []


def test_people_detector_keeps_source_and_direct_company_channel():
    text = """
    ## Jane Smith
    Purchasing Manager
    jane@alpha.com
    [LinkedIn](https://www.linkedin.com/in/jane-smith)
    """
    rows = people_detector.detect_page("https://alpha.com/team", text, "alpha.com")
    assert len(rows) == 1
    row = rows[0]
    assert row["name"] == "Jane Smith"
    assert row["role_kind"] == "commercial"
    assert row["email"] == "jane@alpha.com"
    assert row["linkedin"].startswith("https://www.linkedin.com/in/jane-smith")
    assert row["confidence"] >= 90
    assert row["source_url"] == "https://alpha.com/team"


def test_people_detector_does_not_attach_third_party_email():
    text = "## Jane Smith\nPurchasing Manager\njane@gmail.com"
    row = people_detector.detect_page("https://alpha.com/team", text, "alpha.com")[0]
    assert row["email"] is None
    assert row["confidence"] < decision_maker_radar.AUTO_PROMOTE_MIN


def test_search_urls_can_be_locked_to_customer_domain():
    fake = """
    [Team](https://duckduckgo.com/l/?uddg=https%3A%2F%2Falpha.com%2Fteam&rut=x)
    [LinkedIn](https://duckduckgo.com/l/?uddg=https%3A%2F%2Flinkedin.com%2Fin%2Fjane&rut=y)
    [Leadership](https://duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.alpha.com%2Fleadership&rut=z)
    """
    rows = search.search_urls("site:alpha.com purchasing", 10, fetch=lambda _: fake,
                              allowed_domain="alpha.com")
    assert rows == ["https://alpha.com/team", "https://www.alpha.com/leadership"]


def test_strong_commercial_candidate_auto_promotes_but_role_stays_unconfirmed(conn):
    result = decision_maker_radar.persist_candidates(conn, 1, [{
        "name": "Jane Smith", "title": "Purchasing Manager", "email": "jane@alpha.com",
        "linkedin": None, "role_kind": "commercial", "source_url": "https://alpha.com/team",
        "evidence": "Jane Smith | Purchasing Manager | jane@alpha.com", "confidence": 95,
    }])
    assert result["created"] == 1 and result["promoted"] == 1
    candidate = decision_maker_radar.list_candidates(conn, lead_no=1, status="promoted")[0]
    person = contacts.get(conn, candidate["promoted_contact_id"])
    assert person["name"] == "Jane Smith"
    assert person["role"] == "other"  # title is evidence; it is not silently rewritten as CRM truth
    assert person["source"] == "agent.public-site"


def test_project_candidate_cannot_become_first_default_contact_automatically(conn):
    result = decision_maker_radar.persist_candidates(conn, 2, [{
        "name": "Alex Kim", "title": "Technical Director", "email": "alex@beta.com",
        "linkedin": None, "role_kind": "project", "source_url": "https://beta.com/team",
        "evidence": "Alex Kim | Technical Director | alex@beta.com", "confidence": 95,
    }])
    assert result["promoted"] == 0
    assert contacts.list_all(conn, lead_no=2) == []
    assert decision_maker_radar.list_candidates(conn, lead_no=2)[0]["name"] == "Alex Kim"


def test_project_candidate_can_auto_add_as_secondary_when_company_already_has_contact(conn):
    contacts.create(conn, 2, {
        "name": "Pat Lee", "title": "Owner", "email": "pat@beta.com", "role": "other",
    })
    result = decision_maker_radar.persist_candidates(conn, 2, [{
        "name": "Alex Kim", "title": "Technical Director", "email": "alex@beta.com",
        "linkedin": None, "role_kind": "project", "source_url": "https://beta.com/team",
        "evidence": "Alex Kim | Technical Director | alex@beta.com", "confidence": 95,
    }])
    assert result["promoted"] == 1
    people = contacts.list_all(conn, lead_no=2)
    assert len(people) == 2
    tech = next(p for p in people if p["name"] == "Alex Kim")
    assert tech["is_primary"] is False
    assert tech["role"] == "other"


def test_scan_reads_only_company_owned_results_and_stages_weaker_candidate(conn):
    searched = []
    fetched = []

    def fake_search(query, limit):
        searched.append(query)
        return ["https://evil.example/people", "https://alpha.com/leadership"]

    def fake_fetch(url):
        fetched.append(url)
        return "## Jane Smith\nPurchasing Manager"

    result = decision_maker_radar.scan(
        conn, 1, role_kinds={"commercial"}, search_fn=fake_search, fetch_fn=fake_fetch)
    assert result["pages_checked"] == 1
    assert fetched == ["https://alpha.com/leadership"]
    assert searched and "site:alpha.com" in searched[0]
    assert result["promoted"] == 0
    assert result["candidates"][0]["name"] == "Jane Smith"
    assert result["candidates"][0]["confidence"] < 90


def test_due_accounts_respects_research_cooldown(conn):
    opportunities.create(conn, 1, {
        "title": "Retail wall", "stage": "requirements", "use_case": "Retail",
    })
    due = decision_maker_radar.due_accounts(conn, today=TODAY, limit=2)
    assert due and due[0]["lead_no"] == 1

    decision_maker_radar.scan(
        conn, 1, role_kinds={"commercial"}, search_fn=lambda q, n: [], fetch_fn=lambda u: "")
    assert not any(row["lead_no"] == 1 for row in
                   decision_maker_radar.due_accounts(conn, today=TODAY, limit=2))


def test_sweep_surfaces_unverified_candidate_once(conn):
    opportunities.create(conn, 1, {
        "title": "Retail wall", "stage": "requirements", "use_case": "Retail",
    })

    def fake_search(query, limit):
        return ["https://alpha.com/team"]

    def fake_fetch(url):
        return "## Jane Smith\nPurchasing Manager"

    first = decision_maker_radar.sweep(
        conn, today=TODAY, limit=1, search_fn=fake_search, fetch_fn=fake_fetch)
    second = decision_maker_radar.sweep(
        conn, today=TODAY, limit=1, search_fn=fake_search, fetch_fn=fake_fetch)
    assert first["checked"] == 1 and first["proposed"] == 1
    assert second["checked"] == 0 and second["proposed"] == 0
    pending = proposals.list_proposals(conn, status="pending", kind="create_task")
    assert any("审核关键联系人候选" in row["title"] for row in pending)


def test_customer360_includes_contact_candidate_pool(conn):
    decision_maker_radar.persist_candidates(conn, 1, [{
        "name": "Jane Smith", "title": "Purchasing Manager", "email": None,
        "linkedin": None, "role_kind": "commercial", "source_url": "https://alpha.com/team",
        "evidence": "Jane Smith | Purchasing Manager", "confidence": 81,
    }])
    view = customer360.build(conn, 1)
    assert view["contact_candidates"][0]["name"] == "Jane Smith"
    assert any(item["source"] == "contact_candidate" for item in view["next_best_actions"])


def test_manual_promotion_is_explicit_override_for_staged_candidate(conn):
    created = decision_maker_radar.persist_candidates(conn, 2, [{
        "name": "Alex Kim", "title": "Technical Director", "email": None,
        "linkedin": None, "role_kind": "project", "source_url": "https://beta.com/team",
        "evidence": "Alex Kim | Technical Director", "confidence": 81,
    }], auto_promote=False)
    candidate_id = created["ids"][0]
    promoted = decision_maker_radar.promote_candidate(conn, candidate_id, manual=True)
    assert promoted["status"] == "promoted"
    person = contacts.get(conn, promoted["promoted_contact_id"])
    assert person["name"] == "Alex Kim" and person["role"] == "other"
