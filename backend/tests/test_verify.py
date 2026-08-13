import pytest

from app import verify, outreach
from app.db import connect, init_schema


def _resolver(known_good):
    # returns True for known-good domains, False otherwise; None never here
    return lambda d: d in known_good


def test_classify_syntax_invalid():
    assert verify.classify_email("not-an-email", lambda d: True)[0] == "invalid"
    assert verify.classify_email("a@b", lambda d: True)[0] == "invalid"


def test_classify_no_mx_invalid():
    assert verify.classify_email("bob@dead.com", lambda d: False) == ("invalid", "no-mx")


def test_classify_role_vs_personal():
    r = _resolver({"acme.com"})
    assert verify.classify_email("info@acme.com", r)[0] == "role"
    assert verify.classify_email("sales@acme.com", r)[0] == "role"
    assert verify.classify_email("john.doe@acme.com", r)[0] == "valid"


def test_classify_dns_hiccup_is_unknown_not_invalid():
    assert verify.classify_email("john@acme.com", lambda d: None) == ("unknown", "dns-error")


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, email) VALUES
            (1, 'Good', 'john@good.com'),
            (2, 'Role', 'info@good.com'),
            (3, 'Dead', 'x@dead.com'),
            (4, 'Bad', 'nope'),
            (5, 'NoEmail', NULL);
    """)
    c.commit()
    return c


def test_verify_leads_updates_status_and_counts(conn):
    res = verify.verify_leads(conn, resolve_domain=_resolver({"good.com"}))
    assert res == {"checked": 4, "valid": 1, "role": 1, "invalid": 2, "unknown": 0}
    rows = {r["no"]: r["email_status"] for r in conn.execute("SELECT no, email_status FROM leads")}
    assert rows[1] == "valid" and rows[2] == "role" and rows[3] == "invalid" and rows[4] == "invalid"
    assert rows[5] is None  # no email, untouched


def test_invalid_email_excluded_from_send(conn):
    verify.verify_leads(conn, resolve_domain=_resolver({"good.com"}))
    elig = [l["no"] for l in outreach.eligible_leads(conn, [1, 2, 3, 4], "email")]
    assert elig == [1, 2]  # dead + bad-syntax dropped, role kept


def test_verify_scoped_to_lead_nos(conn):
    res = verify.verify_leads(conn, lead_nos=[1], resolve_domain=_resolver({"good.com"}))
    assert res["checked"] == 1
    assert conn.execute("SELECT email_status FROM leads WHERE no=3").fetchone()["email_status"] is None


def test_reverify_never_revives_a_bounced_address(tmp_path):
    """A bounced address keeps resolving — DNS alone would hand it straight back."""
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.execute("INSERT INTO leads(no, company_en, email, email_status, bounced_at)"
              " VALUES (1, 'A', 'john@acme.com', 'invalid', '2026-08-01T00:00:00+00:00')")
    c.execute("INSERT INTO leads(no, company_en, email) VALUES (2, 'B', 'jane@acme.com')")
    c.commit()
    result = verify.verify_leads(c, resolve_domain=_resolver({"acme.com"}))
    rows = {r["no"]: r["email_status"] for r in c.execute("SELECT no, email_status FROM leads")}
    assert rows[1] == "invalid"      # untouched despite a healthy domain
    assert rows[2] == "valid"        # the un-bounced address is classified normally
    assert result["invalid"] == 1 and result["valid"] == 1
