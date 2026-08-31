"""Professional quality gate for every bundled outbound message (docs/83)."""
from __future__ import annotations

import re

import pytest

from app import message_guard, seed_sequences, seeds, social_queue
from app.copy_segments import SEGMENTS
from app.personalize import render


LEAD = {
    "no": 1,
    "company_en": "Verum Staging",
    "website": "verumstaging.com",
    "city": "Austin",
    "country": "USA",
    "contact_name": "Sam Rivera",
    "hook": "Saw the rental and event production work on your site.",
}

BAD_SHAPES = re.compile(
    r"i hope this email finds you well"
    r"|just following up"
    r"|looking forward to hearing"
    r"|hope we can have"
    r"|should i check back"
    r"|either way"
    r"|no rush"
    r"|no obligation"
    r"|same day"
    r"|worth a conversation"
    r"|in the pipeline"
    r"|spec-and-pricing contact"
    r"|no distributor in between"
    r"|not your area"
    r"|point me at"
    r"|please feel free"
    r"|tell me .{0,80}i(?:'|’)ll"
    r"|send me .{0,80}i(?:'|’)ll"
    r"|회신 기다리"
    r"|보통 당일"
    r"|담당이 아니시면"
    r"|알려주시면",
    re.I | re.S,
)


def _manual_copy():
    for name, lang, subject, body in seeds.EMAIL_TEMPLATES + seeds.ALLEN_STYLE_TEMPLATES:
        yield name, lang, "email", subject, body
    for name, lang, body in seeds.DM_TEMPLATES + seeds.ALLEN_STYLE_DM:
        for channel in ("whatsapp", "instagram"):
            yield name, lang, channel, "", body


def _social_copy():
    for body in social_queue._TEMPLATES:
        yield "hooked", body
    for segment, bodies in social_queue._GENERIC.items():
        for body in bodies:
            yield segment, body


def _render_social(body: str, *, hooked: bool) -> str:
    contact = LEAD["contact_name"]
    expanded = body.replace("{contact_comma}", f" {contact},")
    lead = LEAD if hooked else {**LEAD, "hook": ""}
    return render(expanded, lead).strip()


def test_all_66_bundled_messages_are_enumerable():
    sequence_count = sum(
        len(seed_sequences.steps_for(segment, korean))
        for korean in (False, True)
        for segment in SEGMENTS
    )
    assert sequence_count == 20  # docs/82 R10: 两个英语分段各删掉第 2、3 封
    assert len(list(_manual_copy())) == 22
    assert len(list(_social_copy())) == 20


@pytest.mark.parametrize("korean", [False, True])
@pytest.mark.parametrize("segment", SEGMENTS)
def test_every_sequence_renders_cleanly_and_passes_the_guard(segment, korean):
    for order, _offset, subject, body in seed_sequences.steps_for(segment, korean):
        rendered_subject = render(subject, LEAD)
        rendered_body = render(body, LEAD)
        assert "{" not in rendered_subject + rendered_body
        assert not BAD_SHAPES.search(rendered_subject + "\n" + rendered_body)
        verdict = message_guard.check(
            rendered_body,
            LEAD,
            subject=rendered_subject,
            channel="email",
            step_order=order,
        )
        assert not verdict.blocked, verdict.detail


def test_every_manual_template_renders_cleanly_and_passes_the_guard():
    for name, _lang, channel, subject, body in _manual_copy():
        rendered_subject = render(subject, LEAD)
        rendered_body = render(body, LEAD)
        text = rendered_subject + "\n" + rendered_body
        assert "{" not in text, name
        assert not BAD_SHAPES.search(text), name
        order = 1 if "跟进" in name else 0
        verdict = message_guard.check(
            rendered_body,
            LEAD,
            subject=rendered_subject,
            channel=channel,
            step_order=order,
        )
        assert not verdict.blocked, f"{name}: {verdict.detail}"


def test_every_social_variant_is_short_natural_and_guard_safe():
    for family, body in _social_copy():
        rendered = _render_social(body, hooked=family == "hooked")
        assert "{" not in rendered, family
        assert len(rendered) <= 320, (family, len(rendered))
        assert rendered.count("?") <= 1, family
        assert not BAD_SHAPES.search(rendered), (family, rendered)
        guarded_as = "email" if family == "hooked" else "facebook"
        verdict = message_guard.check(rendered, LEAD, channel=guarded_as)
        assert not verdict.blocked, f"{family}: {verdict.detail}"


@pytest.mark.parametrize("segment", SEGMENTS)
def test_english_first_touch_subjects_are_short(segment):
    subject = seed_sequences.steps_for(segment, False)[0][2]
    words = re.findall(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)?", subject)
    assert 2 <= len(words) <= 4, (segment, subject, words)
    assert not re.search(r"maxcolor|verum", subject, re.I)
    assert "?" not in subject and "!" not in subject


@pytest.mark.parametrize("korean", [False, True])
@pytest.mark.parametrize("segment", SEGMENTS)
def test_each_first_touch_asks_one_low_friction_question(segment, korean):
    body = seed_sequences.steps_for(segment, korean)[0][3]
    assert body.count("?") == 1, (segment, korean, body)


def test_bundled_template_refresh_preserves_custom_rows(conn):
    assert seeds.seed_templates(conn) == 22
    known = conn.execute(
        "SELECT id FROM templates WHERE name=? AND channel='email'",
        ("首次触达（英语）",),
    ).fetchone()["id"]
    conn.execute("UPDATE templates SET body='stale system copy' WHERE id=?", (known,))
    custom_id = conn.execute(
        "INSERT INTO templates(name, channel, subject, body, lang) VALUES (?,?,?,?,?)",
        ("Allen 自定义", "email", "Custom", "Keep this exact copy.", "en"),
    ).lastrowid
    same_name_custom_channel = conn.execute(
        "INSERT INTO templates(name, channel, subject, body, lang) VALUES (?,?,?,?,?)",
        ("首次触达（英语）", "facebook", None, "Keep this channel too.", "en"),
    ).lastrowid
    conn.commit()

    updated = seeds.refresh_bundled_templates(conn)

    assert updated == 22
    assert conn.execute("SELECT body FROM templates WHERE id=?", (known,)).fetchone()["body"] == seeds.EN_BODY
    assert conn.execute("SELECT body FROM templates WHERE id=?", (custom_id,)).fetchone()["body"] == "Keep this exact copy."
    assert conn.execute(
        "SELECT body FROM templates WHERE id=?", (same_name_custom_channel,)
    ).fetchone()["body"] == "Keep this channel too."


def test_system_sequence_refresh_preserves_unknown_sequences(conn):
    custom_id = conn.execute(
        "INSERT INTO sequences(name, channel) VALUES ('Allen 自定义序列', 'email')"
    ).lastrowid
    conn.execute(
        "INSERT INTO sequence_steps(sequence_id, step_order, day_offset, subject, body)"
        " VALUES (?,0,0,'Custom','Keep this sequence.')",
        (custom_id,),
    )
    conn.commit()

    seed_sequences.seed_all(conn)
    seed_sequences.seed_all(conn)

    row = conn.execute(
        "SELECT subject, body FROM sequence_steps WHERE sequence_id=?", (custom_id,)
    ).fetchone()
    assert tuple(row) == ("Custom", "Keep this sequence.")
