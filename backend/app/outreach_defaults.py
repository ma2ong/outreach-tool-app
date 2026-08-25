"""Versioned system-owned outreach defaults and exact-match migration.

Only text that is still byte-for-byte the old shipped default may be upgraded. Anything
Allen edited is user content and is left alone.
"""
from __future__ import annotations

import sqlite3

from app import identity

MIGRATION_KEY = "outreach_default_copy_v2"

# Who we are to a customer is decided in one place (app/identity.py) — the address, the
# company name and the quote header used to disagree with each other across four files.
SIGNOFF = identity.SIGNOFF
KO_SIGNOFF = identity.KO_SIGNOFF

LEGACY_EN_SUBJECT = "Recent LED Display Projects — Shenzhen Maxcolor Visual"
LEGACY_EN_BODY = f"""Hi {{contact}},

I'd like to share some recent LED display projects we delivered in Korea.

We have completed various indoor and outdoor projects including P1.86, P2.5, P3.91, and P10 LED displays.

If you have any upcoming projects, please feel free to contact me anytime. We would be happy to recommend suitable products and provide you with competitive pricing based on your project needs.

Hope we can have a good opportunity to work together!

{SIGNOFF}"""

EN_SUBJECT = "{company} — LED display supply"
EN_BODY = f"""Hi {{contact}},

{{hook}}

I came across {{company}} while looking at LED / AV companies in your market.

We manufacture indoor and outdoor LED displays, including P1.86, P2.5, P3.91 and P10, and supply integrators and rental companies directly.

If you have a current project, send me the screen size, viewing distance and indoor/outdoor use. I'll organize only the relevant specs and project references.

{SIGNOFF}"""

LEGACY_KO_SUBJECT = "한국 LED 디스플레이 납품 사례 공유드립니다"
LEGACY_KO_BODY = f"""안녕하세요~

최근 저희가 한국에 납품한 LED 디스플레이 설치사례를 공유드립니다.
P1.53, P1.86, P2.5, P3.91, P10 등 실내/실외 다양한 프로젝트를 진행했습니다.

혹시 최근 검토 중이거나 진행 예정인 프로젝트가 있으면 편하게 연락 주세요.
현장 조건에 맞는 제품 추천과 좋은 조건으로 견적 드리겠습니다.

좋은 기회로 함께 협력할 수 있기를 바랍니다!

{KO_SIGNOFF}"""

KO_SUBJECT = "{company} - LED 디스플레이 납품 사례"
KO_BODY = f"""안녕하세요~

{{company}} 관련 내용을 확인하다가 연락드렸습니다.

최근 한국에 납품한 LED 디스플레이 설치사례가 있어 공유드립니다. P1.53, P1.86, P2.5, P3.91, P10 등 실내/실외 프로젝트를 진행하고 있습니다.

혹시 지금 검토 중이신 현장이 있거나 나중을 위해 공급처를 알아보시는 단계라면 알려주세요. 상황에 맞는 자료만 정리해서 보내드리겠습니다.

{KO_SIGNOFF}"""


def _has_table(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def upgrade_legacy_defaults(conn: sqlite3.Connection) -> dict:
    """Upgrade only untouched system defaults; safe to call on every connection."""
    required = ("settings", "templates", "sequences", "sequence_steps")
    if not all(_has_table(conn, name) for name in required):
        return {"templates": 0, "sequence_steps": 0, "already": False}
    row = conn.execute("SELECT value FROM settings WHERE key=?", (MIGRATION_KEY,)).fetchone()
    if row and row["value"] == "1":
        return {"templates": 0, "sequence_steps": 0, "already": True}

    template_count = 0
    step_count = 0
    for name, old_subject, old_body, new_subject, new_body in (
        ("首次触达（英语）", LEGACY_EN_SUBJECT, LEGACY_EN_BODY, EN_SUBJECT, EN_BODY),
        ("首次触达（韩语）", LEGACY_KO_SUBJECT, LEGACY_KO_BODY, KO_SUBJECT, KO_BODY),
    ):
        cur = conn.execute(
            "UPDATE templates SET subject=?, body=?"
            " WHERE name=? AND channel='email' AND subject=? AND body=?",
            (new_subject, new_body, name, old_subject, old_body),
        )
        template_count += cur.rowcount

    for seq_name, old_subject, old_body, new_subject, new_body in (
        ("冷邮件 3 步跟进（英语）", LEGACY_EN_SUBJECT, LEGACY_EN_BODY, EN_SUBJECT, EN_BODY),
        ("冷邮件 3 步跟进（韩语）", LEGACY_KO_SUBJECT, LEGACY_KO_BODY, KO_SUBJECT, KO_BODY),
    ):
        cur = conn.execute(
            "UPDATE sequence_steps SET subject=?, body=?"
            " WHERE step_order=0 AND subject=? AND body=?"
            " AND sequence_id IN (SELECT id FROM sequences WHERE name=? AND channel='email')",
            (new_subject, new_body, old_subject, old_body, seq_name),
        )
        step_count += cur.rowcount

    conn.execute(
        "INSERT INTO settings(key,value) VALUES (?, '1')"
        " ON CONFLICT(key) DO UPDATE SET value='1'",
        (MIGRATION_KEY,),
    )
    conn.commit()
    return {"templates": template_count, "sequence_steps": step_count, "already": False}
