import pytest

from app import opportunities
from app.agent import solution_engineer


def _product(conn, *, approved=1, pitch="P2.5", indoor_outdoor="Indoor", exact=True):
    fields = {
        "model": "P2.5 500 cabinet",
        "pixel_pitch": pitch,
        "brightness": "800-1000 nits",
        "use_case": "Fixed Installation",
        "indoor_outdoor": indoor_outdoor,
        "refresh_rate_hz": 3840,
        "maintenance_access": "front",
        "cabinet_size": "500x500mm",
        "agent_approved": approved,
    }
    if exact:
        fields.update({
            "cabinet_width_mm": 500,
            "cabinet_height_mm": 500,
            "cabinet_resolution_w": 200,
            "cabinet_resolution_h": 200,
            "module_width_mm": 250,
            "module_height_mm": 250,
            "max_power_w_cabinet": 200,
            "avg_power_w_cabinet": 80,
        })
    cols = list(fields)
    cur = conn.execute(
        f"INSERT INTO products({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
        [fields[c] for c in cols],
    )
    conn.commit()
    return cur.lastrowid


def _opportunity(conn, **overrides):
    data = {
        "title": "Lobby wall",
        "stage": "requirements",
        "use_case": "Fixed Installation",
        "indoor_outdoor": "indoor",
        "width_m": 3.1,
        "height_m": 2.1,
        "quantity": 2,
        "pixel_pitch": "P2.5",
        "brightness_nits": 800,
        "refresh_rate_hz": 3840,
        "maintenance_access": "front",
        "input_voltage_v": 220,
        "controller_capacity_px": 2_300_000,
        "controller_output_ports": 10,
        "max_pixels_per_port": 650_000,
        "spare_pct": 3,
    }
    data.update(overrides)
    return opportunities.create(conn, 1, data)


def test_unapproved_product_cannot_be_engineered(conn):
    pid = _product(conn, approved=0)
    opp = _opportunity(conn)
    result = solution_engineer.advise(conn, opp, product_id=pid)
    assert result["ready"] is False
    assert result["status"] == "product_not_approved"
    assert result["product"] is None


def test_manual_product_conflict_is_blocked(conn):
    pid = _product(conn, approved=1, pitch="P3.91")
    opp = _opportunity(conn, pixel_pitch="P2.5")
    result = solution_engineer.advise(conn, opp, product_id=pid)
    assert result["ready"] is False
    assert result["status"] == "product_conflict"
    assert any("点间距冲突" in text for text in result["selection"]["conflicts"])


def test_exact_engineering_calculates_layout_resolution_power_control_and_spares(conn):
    pid = _product(conn)
    opp = _opportunity(conn)
    result = solution_engineer.advise(conn, opp, product_id=pid)

    assert result["ready"] is True
    layout = result["selected_layout"]
    assert (layout["cabinet_columns"], layout["cabinet_rows"]) == (6, 4)
    assert layout["actual_width_m"] == 3.0
    assert layout["actual_height_m"] == 2.0
    assert layout["cabinets_per_screen"] == 24
    assert layout["total_cabinets"] == 48

    resolution = result["resolution"]
    assert resolution["screen_width_px"] == 1200
    assert resolution["screen_height_px"] == 800
    assert resolution["pixels_per_screen"] == 960_000
    assert resolution["pixels_project"] == 1_920_000

    power = result["power"]
    assert power["max_power_w_per_screen"] == 4800
    assert power["max_power_w_project"] == 9600
    assert power["avg_power_w_per_screen"] == 1920
    assert power["theoretical_max_current_a_per_screen"] == pytest.approx(21.82)

    control = result["control"]
    assert control["minimum_controller_units_by_pixel_capacity_per_screen"] == 1
    assert control["required_output_ports_per_screen"] == 2
    assert control["minimum_controller_units_per_screen"] == 1

    spares = result["spares"]
    assert spares["spare_cabinets"] == 2
    assert spares["modules_per_cabinet"] == 4
    assert spares["total_modules"] == 192
    assert spares["spare_modules"] == 6


def test_nominal_pitch_never_becomes_exact_resolution(conn):
    pid = _product(conn, exact=False)
    # Exact cabinet dimensions are enough for physical layout, but exact pixel
    # resolution is deliberately absent.
    conn.execute(
        "UPDATE products SET cabinet_width_mm=500, cabinet_height_mm=500 WHERE id=?", (pid,)
    )
    conn.commit()
    opp = _opportunity(conn)
    result = solution_engineer.advise(conn, opp, product_id=pid)
    assert result["selected_layout"]["cabinets_per_screen"] == 24
    assert result["resolution"] is None
    assert result["ready"] is False
    assert any("不能用标称点间距反推" in gap for gap in result["gaps"])


def test_current_and_spares_require_explicit_project_inputs(conn):
    pid = _product(conn)
    opp = _opportunity(conn, input_voltage_v=None, spare_pct=None)
    result = solution_engineer.advise(conn, opp, product_id=pid)
    assert "theoretical_max_current_a_per_screen" not in result["power"]
    assert result["spares"] is None
    assert any("输入电压" in gap for gap in result["gaps"])
    assert any("备品比例" in gap for gap in result["gaps"])


def test_solution_endpoint_and_additive_fields(client, conn):
    pid = _product(conn)
    opp = _opportunity(conn)
    r = client.get(f"/api/opportunities/{opp['id']}/solution?product_id={pid}")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True
    assert body["selected_layout"]["actual_width_m"] == 3.0

    r = client.patch(f"/api/opportunities/{opp['id']}", json={
        "input_voltage_v": 110,
        "controller_capacity_px": 1_000_000,
        "controller_output_ports": 4,
        "max_pixels_per_port": 300_000,
        "spare_pct": 5,
    })
    assert r.status_code == 200
    assert r.json()["input_voltage_v"] == 110
    assert r.json()["spare_pct"] == 5
