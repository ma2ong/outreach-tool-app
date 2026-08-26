"""The agent noticing things on its own (docs/58).

Two defects that only make sense together. The recurring website re-read passed
`first_read=True` — a flag documented for a one-time historical backfill — so buying
signal detection was switched off on the one path that reads hundreds of sites a week.
And the five signals that did get through are markdown fragments, not sentences:

    公开采购 / RFQ：n+Products) * [+ View All Categories](https:/

Fixing only the flag would flood the book with hundreds more of those, which is exactly
the "genuine buying windows get buried" outcome the flag's comment was guarding against.
So these tests hold both ends: detection runs on re-reads, and an unreadable candidate
never gets stored.
"""
import pytest

from app import recheck, signal_detector
from app.agent import autonomous_work
from app.db import connect, init_schema

# A real page: navigation soup around one genuine sentence.
NAV_SOUP = (
    "* [Home](https://x.com/) * [+ View All Categories](https://x.com/cats) "
    "n+Products) * [Contact](https://x.com/c) request for proposal "
    "* [Careers](https://x.com/j) * [Blog](https://x.com/b)"
)
REAL_SENTENCE = (
    "Our facilities team has issued a request for proposal for the arena "
    "video wall replacement, with bids due in March."
)


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, website, target_fit, recheck_count) VALUES
            (1, 'Verum AV', 'verumav.com', 'high', 3),
            (2, 'Newly Found', 'newfound.com', 'high', 0);
    """)
    c.commit()
    return c


# --- R2: an excerpt that does not read as prose is not evidence -------------------

def test_a_markdown_link_fragment_never_becomes_a_headline():
    got = signal_detector.detect_page("https://x.com/", NAV_SOUP + " " + REAL_SENTENCE)
    for item in got:
        assert "](http" not in item["headline"]
        assert "* [" not in item["headline"]


def test_a_real_sentence_still_produces_a_readable_headline():
    got = signal_detector.detect_page("https://x.com/rfp", REAL_SENTENCE)
    assert got, "a genuine RFP sentence must still be detected"
    assert "video wall replacement" in got[0]["headline"] or "request for proposal" in got[0]["headline"]


def test_a_candidate_with_nothing_readable_is_dropped():
    # Every fragment here is navigation; there is no sentence to quote.
    only_soup = NAV_SOUP.replace("request for proposal", "request for proposal")
    got = signal_detector.detect_page("https://x.com/", only_soup)
    assert got == []


@pytest.mark.parametrize("fragment", [
    "n+Products) * [+ View All Categories](https:/",
    "## Let's discuss your project Connect with o",
    "* [Home](https://x.com) * [About](https://x.com/a)",
    "https://example.com/very/long/path?utm=1",
])
def test_known_junk_fragments_are_rejected(fragment):
    assert not signal_detector.reads_as_prose(fragment)


@pytest.mark.parametrize("sentence", [
    "Our facilities team has issued a request for proposal for the video wall.",
    "We are exhibiting at InfoComm 2026 in booth C120.",
    "부스에서 만나요 우리는 이번 전시회에 참가합니다",
])
def test_real_sentences_pass(sentence):
    assert signal_detector.reads_as_prose(sentence)


# --- R1: the recurring re-read is not a first read -------------------------------

def test_a_lead_read_before_gets_signal_detection(conn, monkeypatch):
    seen = {}
    def record(c, no, cands):
        seen["called"] = True
        return []
    monkeypatch.setattr(recheck, "_store_new_signals", record)
    info = {"pages": 2, "buying_signals": [], "icp_type": "integrator", "fit_score": 70}
    autonomous_work._refresh_common(conn, {"no": 1}, info)
    assert seen.get("called") is True


def test_a_lead_never_read_keeps_the_backfill_exemption(conn, monkeypatch):
    seen = {}
    def record(c, no, cands):
        seen["called"] = True
        return []
    monkeypatch.setattr(recheck, "_store_new_signals", record)
    info = {"pages": 2, "buying_signals": [], "icp_type": "integrator", "fit_score": 70}
    autonomous_work._refresh_common(conn, {"no": 2}, info)
    assert "called" not in seen


# --- R3: boilerplate repeated across sites is not a fact about a company ---------

def test_the_same_excerpt_on_a_second_domain_is_boilerplate(conn):
    candidate = {
        "signal_type": "distributor", "headline": "渠道 / 经销商拓展：partner with us today",
        "evidence": "We are always looking for new partners — partner with us today.",
        "source_url": "https://a.com/partners", "confidence": 70,
        "occurred_at": None, "use_case": None,
        "product_fit": "LED", "suggested_angle": "确认渠道拓展计划",
    }
    first = recheck._store_new_signals(conn, 1, [candidate])
    assert len(first) == 1
    # Same words, different company: template text, not something this company did.
    again = recheck._store_new_signals(
        conn, 2, [{**candidate, "source_url": "https://b.com/partners"}])
    assert again == []
