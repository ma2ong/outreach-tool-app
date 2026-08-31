from app import outreach_defaults
from app.db import connect, init_schema


def _legacy_rows(conn):
    conn.execute(
        "INSERT INTO templates(name,channel,subject,body,lang) VALUES (?,?,?,?,?)",
        ("首次触达（英语）", "email", outreach_defaults.LEGACY_EN_SUBJECT,
         outreach_defaults.LEGACY_EN_BODY, "en"),
    )
    conn.execute(
        "INSERT INTO templates(name,channel,subject,body,lang) VALUES (?,?,?,?,?)",
        ("我的自定义英语首封", "email", outreach_defaults.LEGACY_EN_SUBJECT,
         outreach_defaults.LEGACY_EN_BODY + "\nCUSTOM", "en"),
    )
    cur = conn.execute(
        "INSERT INTO sequences(name,channel,active,created_at) VALUES "
        "('冷邮件 3 步跟进（英语）','email',1,datetime('now'))"
    )
    conn.execute(
        "INSERT INTO sequence_steps(sequence_id,step_order,day_offset,subject,body)"
        " VALUES (?,?,?,?,?)",
        (cur.lastrowid, 0, 0, outreach_defaults.LEGACY_EN_SUBJECT,
         outreach_defaults.LEGACY_EN_BODY),
    )
    custom = conn.execute(
        "INSERT INTO sequences(name,channel,active,created_at) VALUES "
        "('我的自定义序列','email',1,datetime('now'))"
    )
    conn.execute(
        "INSERT INTO sequence_steps(sequence_id,step_order,day_offset,subject,body)"
        " VALUES (?,?,?,?,?)",
        (custom.lastrowid, 0, 0, outreach_defaults.LEGACY_EN_SUBJECT,
         outreach_defaults.LEGACY_EN_BODY + "\nCUSTOM"),
    )
    conn.commit()


def test_reconnect_upgrades_exact_system_defaults_only(tmp_path):
    path = str(tmp_path / "t.db")
    conn = connect(path)
    init_schema(conn)
    _legacy_rows(conn)
    conn.close()

    conn = connect(path)  # content migration runs on an existing DB connection
    default = conn.execute(
        "SELECT subject,body FROM templates WHERE name='首次触达（英语）'"
    ).fetchone()
    assert default["subject"] == outreach_defaults.EN_SUBJECT
    assert default["body"] == outreach_defaults.EN_BODY

    custom = conn.execute(
        "SELECT subject,body FROM templates WHERE name='我的自定义英语首封'"
    ).fetchone()
    assert custom["subject"] == outreach_defaults.LEGACY_EN_SUBJECT
    assert custom["body"].endswith("CUSTOM")

    system_step = conn.execute(
        "SELECT st.subject,st.body FROM sequence_steps st JOIN sequences s"
        " ON s.id=st.sequence_id WHERE s.name='冷邮件 3 步跟进（英语）' AND st.step_order=0"
    ).fetchone()
    assert system_step["subject"] == outreach_defaults.EN_SUBJECT
    assert system_step["body"] == outreach_defaults.EN_BODY

    custom_step = conn.execute(
        "SELECT st.subject,st.body FROM sequence_steps st JOIN sequences s"
        " ON s.id=st.sequence_id WHERE s.name='我的自定义序列' AND st.step_order=0"
    ).fetchone()
    assert custom_step["body"].endswith("CUSTOM")

    assert conn.execute(
        "SELECT value FROM settings WHERE key=?", (outreach_defaults.MIGRATION_KEY,)
    ).fetchone()["value"] == "1"
    conn.close()


def test_migration_is_idempotent(tmp_path):
    path = str(tmp_path / "t.db")
    conn = connect(path)
    init_schema(conn)
    _legacy_rows(conn)
    first = outreach_defaults.upgrade_legacy_defaults(conn)
    second = outreach_defaults.upgrade_legacy_defaults(conn)
    assert first["templates"] == 1
    assert first["sequence_steps"] == 1
    assert second["already"] is True
    conn.close()


def test_previous_v2_default_is_upgraded_but_an_edited_copy_is_not(conn):
    conn.execute(
        "INSERT INTO templates(name,channel,subject,body,lang) VALUES (?,?,?,?,?)",
        ("首次触达（英语）", "email", outreach_defaults.V2_EN_SUBJECT,
         outreach_defaults.V2_EN_BODY, "en"),
    )
    conn.execute(
        "INSERT INTO templates(name,channel,subject,body,lang) VALUES (?,?,?,?,?)",
        ("Allen 修改版", "email", outreach_defaults.V2_EN_SUBJECT,
         outreach_defaults.V2_EN_BODY + "\nAllen edit", "en"),
    )
    conn.commit()

    result = outreach_defaults.upgrade_legacy_defaults(conn)

    assert result["templates"] == 1
    system = conn.execute(
        "SELECT subject,body FROM templates WHERE name='首次触达（英语）'"
    ).fetchone()
    assert tuple(system) == (outreach_defaults.EN_SUBJECT, outreach_defaults.EN_BODY)
    custom = conn.execute(
        "SELECT subject,body FROM templates WHERE name='Allen 修改版'"
    ).fetchone()
    assert custom["body"].endswith("Allen edit")
