import datetime as dt

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app import case_library, opportunities
from app.agent import customer360, draft, opportunity_coach, product_advisor
from app.db import connect, init_schema


TODAY = dt.date(2026, 8, 21)


def _product(conn, *, approved=True, model="Indoor P1.86", env="Indoor",
             pitch="P1.86", brightness="800-1000 nits", refresh=3840,
             price="USD 9999"):
    cur = conn.execute(
        "INSERT INTO products(model,pixel_pitch,brightness,use_case,ref_price_sqm,"
        " indoor_outdoor,refresh_rate_hz,maintenance_access,cabinet_size,control_system,"
        " notes,agent_approved) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (model, pitch, brightness, "Retail / Fixed Installation", price, env, refresh,
         "front", "640x480mm", "NovaStar", "internal product note", int(approved)),
    )
    conn.commit()
    return cur.lastrowid


def _qualified_opportunity(conn, *, env="Indoor", pitch="P1.86", brightness=900,
                           refresh=3840):
    return opportunities.create(conn, 1, {
        "title": "Qualified retail wall",
        "stage": "requirements",
        "use_case": "Retail",
        "indoor_outdoor": env,
        "width_m": 8,
        "height_m": 3,
        "viewing_distance_m": 3,
        "pixel_pitch": pitch,
        "brightness_nits": brightness,
        "refresh_rate_hz": refresh,
        "maintenance_access": "front",
        "installation_type": "wall mount",
        "control_system": "NovaStar",
        "next_action": "Confirm final cabinet layout",
        "next_action_date": "2026-08-25",
    })


def test_legacy_product_table_gets_agent_columns_and_defaults_unapproved(tmp_path):
    db = str(tmp_path / "legacy-product.db")
    conn = connect(db)
    conn.execute("CREATE TABLE products (id INTEGER PRIMARY KEY AUTOINCREMENT, model TEXT NOT NULL, pixel_pitch TEXT, brightness TEXT, use_case TEXT, ref_price_sqm TEXT)")
    conn.execute("INSERT INTO products(model,pixel_pitch) VALUES ('Legacy P2.5','P2.5')")
    conn.commit()
    init_schema(conn)
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(products)")}
    assert {"indoor_outdoor", "refresh_rate_hz", "maintenance_access", "cabinet_size",
            "control_system", "notes", "agent_approved"}.issubset(columns)
    row = conn.execute("SELECT agent_approved FROM products WHERE model='Legacy P2.5'").fetchone()
    assert row["agent_approved"] == 0


def test_only_explicitly_approved_products_enter_advisor(conn):
    _product(conn, approved=False, model="Unapproved P1.86")
    approved_id = _product(conn, approved=True, model="Approved P1.86")
    opp = _qualified_opportunity(conn)
    advice = product_advisor.advise(conn, opp)
    assert advice["ready_to_recommend"] is True
    assert [r["product_id"] for r in advice["recommendations"]] == [approved_id]


def test_explicit_product_conflict_is_excluded_not_hand_waved(conn):
    _product(conn, approved=True, model="Indoor only", env="Indoor", pitch="P1.86")
    opp = _qualified_opportunity(conn, env="Outdoor", pitch="P1.86", brightness=6000)
    advice = product_advisor.advise(conn, opp)
    assert advice["recommendations"] == []
    assert advice["ready_to_recommend"] is False


def test_approved_but_vague_product_is_not_customer_recommendable(conn):
    conn.execute("INSERT INTO products(model,agent_approved) VALUES ('Bare approved model',1)")
    conn.commit()
    opp = _qualified_opportunity(conn)
    advice = product_advisor.advise(conn, opp)
    assert advice["status"] == "insufficient_product_evidence"
    assert advice["ready_to_recommend"] is False
    assert advice["recommendations"][0]["model"] == "Bare approved model"
    safe = product_advisor.customer_safe_context(advice)
    assert safe["products"] == []
    assert "Bare approved model" not in str(safe)


def test_customer_safe_product_context_strips_price_history_and_internal_notes(conn):
    _product(conn, approved=True, price="USD 8888")
    opp = _qualified_opportunity(conn)
    advice = product_advisor.advise(conn, opp)
    internal = str(advice)
    safe = product_advisor.customer_safe_context(advice)
    text = str(safe)
    assert "history" in internal
    assert "USD 8888" not in text
    assert "history" not in text
    assert "internal_rank" not in text
    assert "internal product note" not in text
    assert safe["products"][0]["facts"]["refresh_rate_hz"] == 3840


def test_case_is_private_by_default_and_shareable_requires_public_copy(conn):
    row = case_library.create(conn, {"internal_name": "Secret customer project"})
    assert row["shareable"] == 0
    assert case_library.customer_safe_matches(conn, {"use_case": "Retail"}) == []
    with pytest.raises(case_library.CaseValidation, match="公开标签"):
        case_library.update(conn, row["id"], {"shareable": True})


def test_shareable_case_never_exposes_internal_name(conn):
    row = case_library.create(conn, {
        "internal_name": "Customer X confidential pharmacy",
        "public_label": "Korea pharmacy indoor LED",
        "country": "Korea",
        "application": "Retail",
        "indoor_outdoor": "Indoor",
        "pixel_pitch": "P1.86",
        "width_m": 14.4,
        "height_m": 0.96,
        "public_summary": "Indoor P1.86 installation with a long-format main screen.",
        "source_url": "https://example.com/approved-project",
        "shareable": True,
    })
    matches = case_library.customer_safe_matches(conn, {
        "use_case": "Retail", "indoor_outdoor": "Indoor", "pixel_pitch": "P1.86",
    })
    assert matches and matches[0]["public_label"] == "Korea pharmacy indoor LED"
    assert "internal_name" not in matches[0]
    assert "Customer X" not in str(matches)
    assert case_library.get(conn, row["id"])["internal_name"].startswith("Customer X")


def test_shareable_but_unrelated_case_stays_out_of_auto_reply_context(conn):
    case_library.create(conn, {
        "internal_name": "Approved but generic case",
        "public_label": "Generic LED reference",
        "public_summary": "A completed LED display project.",
        "shareable": True,
    })
    internal = case_library.match(conn, {}, limit=3, shareable_only=True)
    assert internal and internal[0]["public_label"] == "Generic LED reference"
    assert internal[0]["match_score"] < case_library.MIN_CUSTOMER_MATCH_SCORE
    assert case_library.customer_safe_matches(conn, {}) == []


def test_reply_context_contains_only_approved_product_and_shareable_case(conn):
    _product(conn, approved=True, model="Approved P1.86", price="USD 7777")
    _qualified_opportunity(conn)
    case_library.create(conn, {
        "internal_name": "Private internal name",
        "public_label": "Korea retail P1.86",
        "application": "Retail",
        "indoor_outdoor": "Indoor",
        "pixel_pitch": "P1.86",
        "public_summary": "Indoor P1.86 retail installation.",
        "shareable": True,
    })
    case_library.create(conn, {
        "internal_name": "Never expose this project",
        "public_label": "Private label",
        "public_summary": "Private summary",
        "application": "Retail",
        "shareable": False,
    })
    message = {
        "id": 991, "lead_no": 1, "channel": "email", "subject": "Re: screen",
        "body": "We need P1.86 indoor for a retail wall.", "thread_json": None,
    }
    ctx = draft.build_context(conn, message)
    rendered = draft._render(ctx)
    assert "APPROVED PRODUCT FACTS" in rendered
    assert "Approved P1.86" in rendered
    assert "3840" in rendered
    assert "USD 7777" not in rendered
    assert "Korea retail P1.86" in rendered
    assert "Private internal name" not in rendered
    assert "Never expose this project" not in rendered
    assert "Private label" not in rendered


def test_opportunity_coach_flags_missing_approved_product_evidence(conn):
    opp = _qualified_opportunity(conn)
    coached = opportunity_coach.coach_opportunity(conn, opp, today=TODAY)
    assert coached["qualification"]["completeness"] >= 45
    assert coached["product_advice"]["status"] == "no_approved_products"
    assert any("产品库没有批准" in risk for risk in coached["risks"])


def test_customer360_exposes_product_and_approved_case_matches(conn):
    _product(conn, approved=True)
    opp = _qualified_opportunity(conn)
    case_library.create(conn, {
        "internal_name": "Internal retail project",
        "public_label": "Approved retail reference",
        "application": "Retail",
        "indoor_outdoor": "Indoor",
        "pixel_pitch": "P1.86",
        "public_summary": "P1.86 indoor retail display.",
        "shareable": True,
    })
    view = customer360.build(conn, 1)
    product_row = next(x for x in view["product_advice"] if x["opportunity_id"] == opp["id"])
    assert product_row["ready_to_recommend"] is True
    case_row = next(x for x in view["approved_case_matches"] if x["opportunity_id"] == opp["id"])
    assert case_row["cases"][0]["public_label"] == "Approved retail reference"


def test_product_and_case_apis_preserve_approval_boundaries(tmp_path):
    db = str(tmp_path / "api.db")
    conn = connect(db)
    init_schema(conn)
    conn.execute("INSERT INTO leads(no,company_en,country) VALUES (1,'API Buyer','USA')")
    conn.commit()
    opp = _qualified_opportunity(conn)
    conn.close()
    main.app.dependency_overrides[main.get_conn] = lambda: connect(db)
    client = TestClient(main.app)
    try:
        created = client.post("/api/products", json={
            "model": "API P1.86", "pixel_pitch": "P1.86", "brightness": "800-1000 nits",
            "use_case": "Retail", "indoor_outdoor": "Indoor", "refresh_rate_hz": 3840,
            "ref_price_sqm": "USD 12345",
        })
        assert created.status_code == 200 and not created.json()["agent_approved"]
        before = client.get(f"/api/opportunities/{opp['id']}/products").json()
        assert before["status"] == "no_approved_products"
        approved = client.patch(f"/api/products/{created.json()['id']}", json={"agent_approved": True})
        assert approved.status_code == 200 and approved.json()["agent_approved"] == 1
        after = client.get(f"/api/opportunities/{opp['id']}/products").json()
        assert after["recommendations"]
        assert "12345" not in str(product_advisor.customer_safe_context(after))

        bad_case = client.post("/api/cases", json={
            "internal_name": "Cannot publish yet", "shareable": True,
        })
        assert bad_case.status_code == 400
        private_case = client.post("/api/cases", json={
            "internal_name": "Private first", "public_label": "Public ref",
            "public_summary": "Approved public summary", "application": "Retail",
        })
        assert private_case.status_code == 200 and private_case.json()["shareable"] == 0
        published = client.patch(f"/api/cases/{private_case.json()['id']}", json={"shareable": True})
        assert published.status_code == 200 and published.json()["shareable"] == 1
    finally:
        main.app.dependency_overrides.pop(main.get_conn, None)
