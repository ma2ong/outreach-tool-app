"""The richer ICP classifier collapses into the three outbound customer types."""
import pytest

from app import customer_types as ct
from app import icp
from app import repository as repo
from app.db import connect, init_schema


@pytest.mark.parametrize("icp_type,expected", [
    ("rental", "Rental"),
    ("integrator", "Install"),
    ("signage", "General"),
    ("reseller", "General"),
    ("end-user", "General"),
    ("unknown", "General"),
])
def test_classifier_verdict_maps_to_three_customer_types(icp_type, expected):
    assert ct.from_icp(icp_type) == expected
    assert ct.derive(f"icp:{icp_type}") == expected


def test_no_classifier_verdict_means_no_automatic_type():
    assert ct.derive("") is None
    assert ct.derive(None) is None


def test_human_type_is_never_replaced():
    assert ct.derive("Install,icp:rental") is None


def test_manual_edit_prevents_rederivation():
    assert ct.derive("icp:rental", edited_at="2026-08-27T10:00:00Z") is None


@pytest.fixture
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    init_schema(c)
    c.executescript("""
        INSERT INTO leads(no, company_en, country, tags) VALUES
            (1, 'Atlanta Pro AV', 'USA', NULL),
            (2, 'Kinoton Korea', 'South Korea', 'Install'),
            (3, 'Edited Co', 'USA', NULL),
            (4, 'Signage Co', 'USA', NULL),
            (5, 'Unknown Co', 'USA', NULL);
    """)
    c.commit()
    return c


def test_classifying_rental_fills_rental_type(conn):
    icp.apply_to_lead(conn, 1, {"icp_type": "rental", "fit_score": 90})
    tags = conn.execute("SELECT tags FROM leads WHERE no=1").fetchone()[0]
    assert ct.customer_types(tags) == ["Rental"]
    assert "icp:rental" in tags


def test_classifying_signage_fills_general_not_outdoor_or_install(conn):
    icp.apply_to_lead(conn, 4, {"icp_type": "signage", "fit_score": 75})
    tags = conn.execute("SELECT tags FROM leads WHERE no=4").fetchone()[0]
    assert ct.customer_types(tags) == ["General"]
    assert "icp:signage" in tags


def test_unknown_classifier_result_fills_general(conn):
    icp.apply_to_lead(conn, 5, {"icp_type": "unknown", "fit_score": 0})
    row = conn.execute("SELECT tags, target_fit FROM leads WHERE no=5").fetchone()
    assert row["target_fit"] == "未知 (0)"
    assert ct.customer_types(row["tags"]) == ["General"]
    assert "icp:unknown" in row["tags"]


def test_classifying_does_not_touch_human_type(conn):
    icp.apply_to_lead(conn, 2, {"icp_type": "rental", "fit_score": 90})
    tags = conn.execute("SELECT tags FROM leads WHERE no=2").fetchone()[0]
    assert ct.customer_types(tags) == ["Install"]


def test_classifying_again_after_human_clears_type_leaves_it_clear(conn):
    icp.apply_to_lead(conn, 3, {"icp_type": "rental", "fit_score": 90})
    assert ct.customer_types(
        conn.execute("SELECT tags FROM leads WHERE no=3").fetchone()[0]) == ["Rental"]

    repo.update_lead(conn, 3, {"tags": ""})
    icp.apply_to_lead(conn, 3, {"icp_type": "rental", "fit_score": 90})

    assert ct.customer_types(
        conn.execute("SELECT tags FROM leads WHERE no=3").fetchone()[0]) == []


def test_target_fit_keeps_richer_icp_label_and_score(conn):
    icp.apply_to_lead(conn, 1, {"icp_type": "rental", "fit_score": 90})
    fit = conn.execute("SELECT target_fit FROM leads WHERE no=1").fetchone()[0]
    assert fit == "租赁公司 (90)"
