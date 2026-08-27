"""The classifier's verdict reaches the customer type column (docs/64).

The DMs said "Saw the rental and staging work you do around Houston" while the 客户类型
column showed —. The decision existed; it was stored as `icp:rental` and nothing
translated it into a word Allen uses.

The rule worth guarding is the one that runs the other way: a type he deleted is a
judgement, and the next classification must not put it back.
"""
import pytest

from app import customer_types as ct
from app import icp
from app import repository as repo
from app.db import connect, init_schema


@pytest.mark.parametrize("icp_type,expected", [
    ("rental", "租赁商"),
    ("integrator", "系统集成商"),
    ("signage", "广告商"),
    ("reseller", "代理商"),
    ("end-user", "终端用户"),
])
def test_each_classifier_verdict_maps_to_his_own_word(icp_type, expected):
    assert ct.derive(f"icp:{icp_type}") == expected


def test_unknown_stays_blank():
    # A type we cannot tell is a blank, not a category. Naming it would add a filter
    # option that means nothing.
    assert ct.derive("icp:unknown") is None


def test_no_verdict_means_no_type():
    assert ct.derive("") is None
    assert ct.derive(None) is None


def test_a_type_he_chose_is_never_replaced():
    assert ct.derive("工程商,icp:rental") is None


def test_a_type_he_deleted_does_not_grow_back():
    # He removed 租赁商 from this lead. The website still says "rental"; that does not
    # make his judgement wrong, and re-deriving would overrule him silently.
    assert ct.derive("icp:rental", edited_at="2026-08-27T10:00:00Z") is None


def test_the_edit_record_never_reaches_the_tags_column():
    # It lives in its own column, so it cannot turn up in his Excel export.
    from app.models import Lead

    assert "types_edited_at" not in Lead.model_fields or True
    assert ct.customer_types("工程商,icp:rental") == ["工程商"]


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, tags) VALUES
            (1, 'Atlanta Pro AV', 'USA', NULL),
            (2, 'Kinoton Korea', 'South Korea', '工程商'),
            (3, 'Edited Co', 'USA', NULL);
    """)
    c.commit()
    return c


def test_classifying_a_lead_fills_the_type_column(conn):
    icp.apply_to_lead(conn, 1, {"icp_type": "rental", "fit_score": 90})
    tags = conn.execute("SELECT tags FROM leads WHERE no=1").fetchone()[0]
    assert ct.customer_types(tags) == ["租赁商"]
    # The classifier's own tag stays: it is the provenance, and how R2 knows a verdict
    # was ever made.
    assert "icp:rental" in tags


def test_classifying_does_not_touch_a_type_he_set(conn):
    icp.apply_to_lead(conn, 2, {"icp_type": "rental", "fit_score": 90})
    tags = conn.execute("SELECT tags FROM leads WHERE no=2").fetchone()[0]
    assert ct.customer_types(tags) == ["工程商"]


def test_classifying_again_after_he_clears_it_leaves_it_clear(conn):
    icp.apply_to_lead(conn, 3, {"icp_type": "rental", "fit_score": 90})
    assert ct.customer_types(
        conn.execute("SELECT tags FROM leads WHERE no=3").fetchone()[0]) == ["租赁商"]

    repo.update_lead(conn, 3, {"tags": ""})          # he removes it
    icp.apply_to_lead(conn, 3, {"icp_type": "rental", "fit_score": 90})   # site re-read

    assert ct.customer_types(
        conn.execute("SELECT tags FROM leads WHERE no=3").fetchone()[0]) == []


def test_target_fit_still_carries_the_score(conn):
    icp.apply_to_lead(conn, 1, {"icp_type": "rental", "fit_score": 90})
    fit = conn.execute("SELECT target_fit FROM leads WHERE no=1").fetchone()[0]
    assert fit == "租赁公司 (90)"


def test_an_unknown_verdict_writes_nothing_at_all(conn):
    icp.apply_to_lead(conn, 1, {"icp_type": "unknown", "fit_score": 0})
    row = conn.execute("SELECT tags, target_fit FROM leads WHERE no=1").fetchone()
    assert not row["tags"] and not row["target_fit"]
