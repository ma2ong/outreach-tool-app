"""A name you can say out loud, even when you cannot write to it (docs/98).

`decision_maker_radar` has run 545 scans and produced 270 candidates. 24 became
contacts; **246 have sat at `new` and were never used once**, held by one line in
`promote_candidate`:

    if not (candidate.get("email") or candidate.get("linkedin")):
        raise DecisionMakerValidation("自动晋级需要公开公司邮箱或个人 LinkedIn")

That rule is right about what it guards — promotion means this person might receive a
letter, and without a channel there is nothing to send to. But saying someone's name
needs no channel at all, and those 88 companies are being mailed anyway, at `info@`,
opening with "Hi,". A gate built for "can we write to him" was closing over "can we
call him by name", which is a different question.

Nothing here invents a name, guesses an address, or overwrites one of Allen's own.
"""
from __future__ import annotations

import datetime as dt
import re

from app import personalize

# Korea is handled elsewhere (Allen, 09-04). Not read, not written — the greeting
# column has another piece of work writing to it and two writers on one column is how
# corrections get lost. Same list as docs/63.
KOREA = {"south korea", "korea", "kr", "republic of korea"}
# Three of the companies this would have named carry no country at all and are plainly
# Korean — 이승근 / 대표. Allen's rule is about Korean companies, not about a column
# being filled in, so the script decides when the column cannot (docs/98 R1).
_HANGUL = re.compile(r"[가-힯]")

# Web furniture that reads as a two-word capitalised name and sails straight through
# `personalize.looks_like_a_person` — that gate blocks job titles, not buttons. A list
# rather than a pattern: an inferred rule eventually meets someone actually surnamed
# More, and a list never does.
FURNITURE = {
    "read more", "learn more", "see more", "show more", "read bio", "view profile",
    "our team", "meet the team", "contact us", "about us", "get in touch",
    "markdown content", "skip to content", "main menu", "privacy policy",
}

# Words that are a job, not a person. `looks_like_a_person` blocks "Outside Sales" and
# "Contact" through its own list but passes "Operations Manager" and "Executive
# Producer" — measured, not assumed. A name made entirely of these is a title the
# scraper picked up instead of a name. One title word is fine: somebody is surnamed
# Marshall, and "Tom Sales" is likelier a person than a department.
TITLE_WORDS = {
    "ceo", "cto", "coo", "cfo", "cmo", "vp", "svp", "evp", "president", "vice",
    "director", "manager", "managing", "executive", "chief", "officer", "head",
    "lead", "leader", "founder", "co-founder", "owner", "partner", "principal",
    "producer", "engineer", "engineering", "technical", "technician", "operations",
    "production", "project", "account", "sales", "marketing", "business",
    "development", "general", "senior", "junior", "assistant", "associate",
    "coordinator", "specialist", "consultant", "supervisor", "administrator",
    "support", "service", "services", "solutions", "media", "digital", "creative",
}

_SUFFIX = re.compile(
    r"[\s,]*\b(inc|inc\.|llc|l\.l\.c\.|ltd|ltd\.|limited|corp|corp\.|co|co\.|"
    r"gmbh|bv|b\.v\.|srl|s\.r\.l\.|sa|s\.a\.|pty|plc|ag|kg|oy|ab|as|nv)\b\.?\s*$", re.I)
_TIDY = re.compile(r"[^a-z0-9]+")


def _normalise(value: str) -> str:
    return _TIDY.sub("", str(value or "").lower())


def _company_forms(company: str) -> set[str]:
    """The company's name, with and without its legal suffix."""
    raw = str(company or "").strip()
    forms = {raw}
    trimmed = _SUFFIX.sub("", raw).strip()
    if trimmed:
        forms.add(trimmed)
    return {_normalise(f) for f in forms if f}


def is_sayable(name: str, company: str) -> bool:
    """Can this string be said to a customer as their own name?

    Three filters, all deterministic, applied before anything is counted (docs/98 R3).
    The first is docs/95 R3's gate, reused as-is: `personalize.py` is not touched here.
    """
    text = str(name or "").strip()
    if not text or not personalize.looks_like_a_person(text):
        return False
    if text.lower() in FURNITURE:
        return False
    tokens = [t.strip(".,").lower() for t in text.split() if t.strip(".,")]
    if tokens and all(t in TITLE_WORDS for t in tokens):
        return False
    return _normalise(text) not in _company_forms(company)


_JUDGE_SYSTEM = (
    "You decide whether a string scraped from a company website is a real person's "
    "name, or something else: a page heading, a section title, a navigation label, a "
    "company or venue name, a department, or a job title. Answer only about what the "
    "string is. Never rewrite, translate, trim or complete a name. "
    'Reply with JSON: {"people": ["<the exact strings that are personal names>"]}. '
    "Include a string only if you are confident it names an individual person."
)


def _judged_people(conn, items: list[dict]) -> set[str]:
    """Which of these strings a classifier is willing to call a person's name.

    The deterministic filters cap out well short of usable. Measured on the real book:
    29 companies would have been named, and the letters would have opened "Hi Our
    Story," / "Hi Recent Comments," / "Hi Warranty Overview," — roughly three in five
    wrong. docs/95 records that tightening the regex was tried twice and missed in both
    directions, so this asks a model instead, on the `classify` task that already exists
    for exactly this kind of judgement.

    Two rules keep it honest, both from docs/93: the model only judges, it never writes
    — a returned string that is not one we sent is discarded, and the name that reaches
    the letter is always the original — and an unavailable model means no names, not
    guessed ones (docs/98 R7).
    """
    from app.agent import llm

    if not items:
        return set()
    sent = {i["name"] for i in items}
    lines = "\n".join(
        f'- "{i["name"]}" (listed as {i["title"] or "no title"} at {i["company"]})'
        for i in items)
    try:
        data = llm.complete_json(conn, "classify", _JUDGE_SYSTEM,
                                 "Strings scraped from company sites:\n" + lines)
    except Exception:  # noqa: BLE001 — 不确定就 Hi,（Allen 09-04）
        return set()
    people = data.get("people")
    if not isinstance(people, list):
        return set()
    # Only strings we actually sent. A name the model produced is a name nobody read
    # off the customer's page.
    return {p for p in people if isinstance(p, str) and p in sent}


_K_LAST_DAY = "contact_names_last_day"


def run_if_due(conn, now: dt.datetime | None = None) -> dict | None:
    """Once a sales day, not once a cycle.

    The candidates a model turns down stay `new` on purpose — the radar keeps improving
    and tomorrow's crawl may read the same page better — so without a day gate the same
    thirty-odd names would be re-judged in all eighty-five cycles. One call a day is the
    whole cost of this feature.
    """
    from app import local_time, settings

    day = local_time.sales_day(now).isoformat()
    if settings.get(conn, _K_LAST_DAY) == day:
        return None
    settings.set_value(conn, _K_LAST_DAY, day)
    return fill(conn, now)


def fill(conn, now: dt.datetime | None = None, judge=None) -> dict:
    """Give a greeting to every company that has exactly one credible name.

    Exactly one, not the highest-scoring one (docs/98 R2). Data Projections has six real
    names and all nine of its candidates score 81 — sorting by confidence there would
    only be a coin toss written as an algorithm. Not knowing which person to name is
    precisely the "不确定" that Allen said should stay "Hi,".
    """
    from app import contacts, decision_maker_radar

    decision_maker_radar.ensure_schema(conn)
    stamp = (now or dt.datetime.now()).isoformat(timespec="seconds")
    rows = conn.execute(
        """SELECT cc.id, cc.lead_no, cc.name, cc.title, cc.source_url,
                  l.company_en, l.country, l.website
           FROM contact_candidates cc JOIN leads l ON l.no = cc.lead_no
           WHERE cc.status = 'new'
             AND COALESCE(l.contact_name, '') = ''
           ORDER BY cc.lead_no, cc.id"""
    ).fetchall()

    by_lead: dict[int, list] = {}
    korea = set()
    for row in rows:
        if (str(row["country"] or "").strip().lower() in KOREA
                or _HANGUL.search(f'{row["name"] or ""}{row["title"] or ""}')):
            korea.add(row["lead_no"])
            continue
        by_lead.setdefault(row["lead_no"], []).append(row)

    survivors: dict[int, list] = {}
    for lead_no, candidates in by_lead.items():
        kept = [c for c in candidates
                if is_sayable(c["name"], c["company_en"])
                and decision_maker_radar._company_owned(c["source_url"], c["website"])]
        if kept:
            survivors[lead_no] = kept

    # One call for the whole day's batch, not one per name.
    judge = judge or _judged_people
    people = judge(conn, [{"name": c["name"], "title": c["title"],
                           "company": c["company_en"]}
                          for kept in survivors.values() for c in kept])

    named = ambiguous = rejected = 0
    for lead_no, kept in survivors.items():
        usable = [c for c in kept if c["name"] in people]
        if not usable:
            rejected += 1
            continue
        if len(usable) > 1:
            ambiguous += 1
            continue
        pick = usable[0]
        contact = contacts.create(
            conn, lead_no,
            {"name": pick["name"], "title": pick["title"], "role": "other",
             "note": (f"docs/98：官网公开姓名，用作称呼；来源 {pick['source_url']}；"
                      "没有邮箱，不是收件人也不会被抄送。")[:1000]},
            is_primary=False, source="agent.public-site")
        conn.execute("UPDATE leads SET contact_name=? WHERE no=?", (pick["name"], lead_no))
        # Marking it promoted is what makes Allen's later edit final: a cleared name is
        # never refilled, because this candidate is no longer looked at (docs/98 R5).
        conn.execute(
            "UPDATE contact_candidates SET status='promoted', promoted_contact_id=?,"
            " updated_at=? WHERE id=?", (contact["id"], stamp, pick["id"]))
        named += 1
    conn.commit()
    return {"named": named, "ambiguous": ambiguous, "rejected": rejected,
            "korea_skipped": len(korea)}
