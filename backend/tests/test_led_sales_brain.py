import datetime as dt

from app import contacts, opportunities, sales_intelligence
from app.agent import customer360, led_playbook, opportunity_coach, proposals, world
from app.db import connect, init_schema


TODAY = dt.date(2026, 8, 21)


def test_existing_opportunity_table_migrates_additively(tmp_path):
    db = str(tmp_path / "legacy.db")
    c = connect(db)
    init_schema(c)
    c.executescript("""
        CREATE TABLE opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_no INTEGER NOT NULL,
            title TEXT NOT NULL,
            stage TEXT NOT NULL DEFAULT 'qualified',
            amount REAL,
            currency TEXT NOT NULL DEFAULT 'USD',
            probability INTEGER NOT NULL DEFAULT 20,
            expected_close_date TEXT,
            next_action TEXT,
            next_action_date TEXT,
            use_case TEXT,
            indoor_outdoor TEXT,
            width_m REAL,
            height_m REAL,
            quantity INTEGER NOT NULL DEFAULT 1,
            pixel_pitch TEXT,
            destination TEXT,
            incoterm TEXT,
            competitor TEXT,
            loss_reason TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_activity_at TEXT NOT NULL
        );
    """)
    c.commit()

    opportunities.ensure_schema(c)
    columns = {r["name"] for r in c.execute("PRAGMA table_info(opportunities)")}
    assert set(opportunities.QUALIFICATION_COLUMNS).issubset(columns)
    assert "viewing_distance_m" in columns
    assert "control_system" in columns


def test_rental_playbook_asks_viewing_distance_before_logistics():
    q = led_playbook.qualification({
        "use_case": "Rental",
        "indoor_outdoor": "Indoor",
        "width_m": 8,
        "height_m": 4,
    })
    assert q["application"] == "Rental"
    assert q["missing"][0]["key"] == "viewing_distance_m"
    assert "多远" in q["next_question"]


def test_outdoor_project_prioritizes_brightness_after_environment_known():
    q = led_playbook.qualification({
        "use_case": "Fixed Installation",
        "indoor_outdoor": "Outdoor",
        "width_m": 10,
        "height_m": 5,
    })
    assert q["missing"][0]["key"] == "brightness_nits"


def test_new_led_qualification_fields_persist(conn):
    opp = opportunities.create(conn, 1, {
        "title": "Rental wall",
        "stage": "requirements",
        "use_case": "Rental",
        "indoor_outdoor": "Indoor",
        "width_m": 8,
        "height_m": 4,
        "viewing_distance_m": 3.5,
        "refresh_rate_hz": 7680,
        "maintenance_access": "front",
        "cabinet_size": "500x500 / 500x1000",
        "control_system": "4K input with backup",
        "project_timing": "install in October",
    })
    loaded = opportunities.get(conn, opp["id"])
    assert loaded["viewing_distance_m"] == 3.5
    assert loaded["refresh_rate_hz"] == 7680
    assert loaded["maintenance_access"] == "front"
    assert loaded["control_system"] == "4K input with backup"


def test_title_can_support_authority_coverage_without_mutating_role(conn):
    person = contacts.create(conn, 1, {
        "name": "Jane",
        "title": "Purchasing Manager",
        "email": "jane@alpha.com",
        "role": "other",
    })
    coverage = opportunity_coach.contact_coverage(conn, 1, {"use_case": "Rental"})
    assert coverage["commercial_authority"] is True
    assert contacts.get(conn, person["id"])["role"] == "other"
    assert coverage["project_authority"] is False


def test_quoted_opportunity_without_dated_next_step_is_high_risk(conn):
    opp = opportunities.create(conn, 1, {
        "title": "Quoted indoor wall",
        "stage": "quoted",
        "amount": 25000,
        "use_case": "Fixed Installation",
        "next_action": "Confirm technical details with buyer",
    })
    coached = opportunity_coach.coach_opportunity(conn, opp, today=TODAY)
    assert coached["health"] < 65
    assert coached["severity"] in ("critical", "high")
    assert "下一步没有日期" in coached["risks"]
    assert coached["contact_coverage"]["commercial_authority"] is False
    assert "确定日期" in coached["next_best_action"]


def test_opportunity_coach_safety_net_is_idempotent(conn):
    opportunities.create(conn, 1, {
        "title": "Unqualified rental project",
        "stage": "requirements",
        "use_case": "Rental",
    })
    first = opportunity_coach.safety_net(conn, today=TODAY, limit=3)
    second = opportunity_coach.safety_net(conn, today=TODAY, limit=3)
    assert first["proposed"] == 1
    assert second["proposed"] == 0
    pending = proposals.list_proposals(conn, status="pending", kind="create_task")
    assert any("商机体检" in p["title"] for p in pending)


def test_existing_open_opportunity_task_prevents_duplicate_coach_task(conn):
    opp = opportunities.create(conn, 1, {
        "title": "Owned project",
        "stage": "requirements",
        "use_case": "Retail",
        "next_action": "Ask for exact dimensions",
        "next_action_date": "2026-08-25",
    })
    coached = opportunity_coach.coach_opportunity(conn, opp, today=TODAY)
    assert coached["open_task"] is not None
    assert opportunity_coach.safety_net(conn, today=TODAY, limit=3)["proposed"] == 0


def test_customer360_joins_existing_crm_truths(conn):
    contacts.create(conn, 1, {
        "name": "Alex",
        "title": "Technical Director",
        "email": "alex@alpha.com",
        "role": "technical",
    })
    opp = opportunities.create(conn, 1, {
        "title": "XR stage",
        "stage": "requirements",
        "use_case": "XR virtual production",
        "indoor_outdoor": "Indoor",
        "width_m": 12,
        "height_m": 5,
    })
    sales_intelligence.create_signal(conn, 1, {
        "signal_type": "project",
        "headline": "New studio expansion",
        "evidence": "Company announced a new production studio",
        "source_url": "https://alpha.com/news/studio",
        "occurred_at": "2026-08-20",
        "confidence": 85,
        "use_case": "Virtual Production",
        "suggested_angle": "Ask whether the studio needs a new XR LED stage",
    })

    view = customer360.build(conn, 1)
    assert view["account"]["company_en"] == "Alpha AV"
    assert any(o["id"] == opp["id"] for o in view["opportunities"])
    assert view["buying_signals"][0]["headline"] == "New studio expansion"
    assert view["opportunity_coaching"][0]["qualification"]["application"] == "Virtual Production"
    assert view["contact_coverage"]["project_authority"] is True
    assert view["next_best_actions"]


def test_world_exposes_compact_opportunity_coaching(conn):
    opportunities.create(conn, 1, {
        "title": "Live LED project",
        "stage": "requirements",
        "use_case": "Retail",
    })
    state = world.build(conn)
    assert state["opportunity_coaching"]
    row = state["opportunity_coaching"][0]
    assert row["title"] == "Live LED project"
    assert "qualification_pct" in row
    assert row["next_best_action"]
