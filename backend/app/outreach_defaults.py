"""Versioned system-owned outreach defaults and exact-match migration.

Only text that is still byte-for-byte the old shipped default may be upgraded. Anything
Allen edited is user content and is left alone.
"""
from __future__ import annotations

import sqlite3

from app import identity

MIGRATION_KEY = "outreach_default_copy_v3"

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

# The v2 text remains here so an untouched installed copy can be upgraded exactly once.
# Anything with even one user edit no longer matches and is preserved.
V2_EN_SUBJECT = "Indoor, rental and outdoor LED panels — full spec sheets"
V2_EN_BODY = f"""Hi {{contact}},

{{hook}}

I came across {{company}} while looking at LED / AV companies in your market.

We manufacture indoor and outdoor LED displays, including P1.86, P2.5, P3.91 and P10, and supply integrators and rental companies directly.

If you have a current project, send me the screen size, viewing distance and indoor/outdoor use. I'll organize only the relevant specs and project references.

{SIGNOFF}"""

# docs/83: the subject earns the open; the body offers one useful artefact and asks one
# low-friction question. Price and project inputs stay out of first contact.
EN_SUBJECT = "LED panel specs"
EN_BODY = f"""Hi {{contact}},

{{hook}}

I'm Allen, handling export sales for an LED display manufacturer in Shenzhen.

We cover indoor P2-P3 at 600-800 nits, rental P2.6-P4.8 die-cast, and outdoor P4-P10
at 5,500-8,000 nits.

Would a one-page comparison with cabinet weight, power and service access be useful to
{{company}}?

{SIGNOFF}"""

LEGACY_KO_SUBJECT = "한국 LED 디스플레이 납품 사례 공유드립니다"
LEGACY_KO_BODY = f"""안녕하세요~

최근 저희가 한국에 납품한 LED 디스플레이 설치사례를 공유드립니다.
P1.53, P1.86, P2.5, P3.91, P10 등 실내/실외 다양한 프로젝트를 진행했습니다.

혹시 최근 검토 중이거나 진행 예정인 프로젝트가 있으면 편하게 연락 주세요.
현장 조건에 맞는 제품 추천과 좋은 조건으로 견적 드리겠습니다.

좋은 기회로 함께 협력할 수 있기를 바랍니다!

{KO_SIGNOFF}"""

V2_KO_SUBJECT = "실내·렌탈·실외 LED 패널 사양서 보내드립니다"
V2_KO_BODY = f"""안녕하세요~

{{company}} 관련 내용을 확인하다가 연락드렸습니다.

최근 한국에 납품한 LED 디스플레이 설치사례가 있어 공유드립니다. P1.53, P1.86, P2.5, P3.91, P10 등 실내/실외 프로젝트를 진행하고 있습니다.

혹시 지금 검토 중이신 현장이 있거나 나중을 위해 공급처를 알아보시는 단계라면 알려주세요. 상황에 맞는 자료만 정리해서 보내드리겠습니다.

{KO_SIGNOFF}"""

KO_SUBJECT = "LED 패널 사양"
KO_BODY = f"""안녕하세요, {{contact}}님.

{{hook_ko}}

저는 선전의 LED 디스플레이 제조업체에서 해외영업을 담당하는 Allen입니다.

실내 P2-P3(600-800 nits), 렌탈 P2.6-P4.8 다이캐스팅, 실외
P4-P10(5,500-8,000 nits) 제품을 공급하고 있습니다.

캐비닛 무게, 소비전력, 유지보수 방식을 한눈에 볼 수 있는 비교표를 보내드리면
{{company}} 검토에 도움이 될까요?

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
    versions = (
        ("首次触达（英语）", "冷邮件 3 步跟进（英语）", EN_SUBJECT, EN_BODY, (
            (LEGACY_EN_SUBJECT, LEGACY_EN_BODY),
            (V2_EN_SUBJECT, V2_EN_BODY),
        )),
        ("首次触达（韩语）", "冷邮件 3 步跟进（韩语）", KO_SUBJECT, KO_BODY, (
            (LEGACY_KO_SUBJECT, LEGACY_KO_BODY),
            (V2_KO_SUBJECT, V2_KO_BODY),
        )),
    )
    for template_name, sequence_name, new_subject, new_body, old_versions in versions:
        for old_subject, old_body in old_versions:
            cur = conn.execute(
                "UPDATE templates SET subject=?, body=?"
                " WHERE name=? AND channel='email' AND subject=? AND body=?",
                (new_subject, new_body, template_name, old_subject, old_body),
            )
            template_count += cur.rowcount
            cur = conn.execute(
                "UPDATE sequence_steps SET subject=?, body=?"
                " WHERE step_order=0 AND subject=? AND body=?"
                " AND sequence_id IN (SELECT id FROM sequences WHERE name=? AND channel='email')",
                (new_subject, new_body, old_subject, old_body, sequence_name),
            )
            step_count += cur.rowcount

    conn.execute(
        "INSERT INTO settings(key,value) VALUES (?, '1')"
        " ON CONFLICT(key) DO UPDATE SET value='1'",
        (MIGRATION_KEY,),
    )
    conn.commit()
    return {"templates": template_count, "sequence_steps": step_count, "already": False}
