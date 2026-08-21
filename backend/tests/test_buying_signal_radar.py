from app import discovery, enrich, recheck, sales_intelligence, signal_detector


def _signal(signal_type="tender", headline="Public RFQ for AV system"):
    return {
        "signal_type": signal_type,
        "headline": headline,
        "evidence": "Request for quotation for a new AV and LED display system.",
        "source_url": "https://alpha.com/news/rfq-led",
        "occurred_at": None,
        "confidence": 85,
        "use_case": "Fixed Installation",
        "product_fit": "LED display / video wall / digital signage",
        "suggested_angle": "Confirm whether the RFQ includes an LED display requirement.",
    }


def test_detector_recognizes_high_intent_public_evidence():
    text = """
    Procurement notice. Request for proposals (RFP) for renovation of our conference
    center audiovisual system. Qualified vendors may submit proposals this month.
    """
    rows = signal_detector.detect_page("https://acme.com/procurement/rfp", text)
    assert any(row["signal_type"] == "tender" and row["confidence"] >= 80 for row in rows)
    assert all(row["source_url"] == "https://acme.com/procurement/rfp" for row in rows)


def test_detector_rejects_generic_project_and_hiring_noise():
    generic = "We deliver projects for events worldwide and are hiring an accountant."
    rows = signal_detector.detect_page("https://acme.com/about", generic)
    assert not any(row["signal_type"] in ("project", "hiring") for row in rows)


def test_project_signal_requires_change_plus_facility_context():
    text = "We are opening a new broadcast studio and production facility this fall."
    rows = signal_detector.detect_page("https://acme.com/news/new-studio", text)
    project = next(row for row in rows if row["signal_type"] == "project")
    assert project["use_case"] == "Broadcast"
    assert "studio" in project["evidence"].lower()


def test_hiring_signal_requires_relevant_av_role():
    text = "We're hiring. Join our team as an AV technician and video engineer."
    rows = signal_detector.detect_page("https://acme.com/careers", text)
    assert any(row["signal_type"] == "hiring" for row in rows)


def test_exhibition_and_distributor_signals_require_strong_language():
    text = "Meet us at InfoComm at booth C123. We are also looking for new distributors in the US."
    rows = signal_detector.detect_page("https://acme.com/news", text)
    kinds = {row["signal_type"] for row in rows}
    assert "exhibition" in kinds and "distributor" in kinds


def test_multilingual_detector_handles_korean_procurement_and_chinese_channel_signal():
    text = "신규 스튜디오 AV 시스템 입찰공고입니다. 同时我们正在招募经销商，欢迎渠道伙伴联系。"
    rows = signal_detector.detect_page("https://acme.com/notice", text)
    kinds = {row["signal_type"] for row in rows}
    assert "tender" in kinds and "distributor" in kinds


def test_enrichment_returns_source_backed_signal_candidates():
    pages = {
        "https://acme.com/contact": "Contact sales@acme.com",
        "https://acme.com/contact-us": "",
        "https://acme.com": "We are opening a new showroom and retail store this year.",
    }
    out = enrich.enrich_domain("acme.com", fetch=lambda url: pages.get(url, ""))
    assert out["buying_signals"]
    signal = next(row for row in out["buying_signals"] if row["signal_type"] == "project")
    assert signal["source_url"] == "https://acme.com"
    assert signal["use_case"] == "Retail"


def test_discovery_import_persists_signal_only_after_lead_creation(conn):
    before = conn.execute("SELECT COUNT(*) FROM buying_signals").fetchone()[0] if \
        conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='buying_signals'").fetchone() else 0
    result = discovery.import_candidates(conn, [{
        "company_en": "Signal Prospect",
        "website": "signalprospect.com",
        "email": "sales@signalprospect.com",
        "country": "USA",
        "icp_type": "av_integrator",
        "fit_score": 90,
        "brief": "AV integration company",
        "hook": "Saw your AV integration work.",
        "buying_signals": [_signal()],
    }], "USA")
    assert result["imported"] == 1
    lead_no = result["imported_lead_nos"][0]
    rows = sales_intelligence.list_signals(conn, lead_no=lead_no)
    assert len(rows) == 1 and rows[0]["signal_type"] == "tender"
    assert result["signals_imported"] == 1
    assert len(rows) == before + 1 if before else len(rows) == 1


def test_recheck_wakes_account_on_new_signal_even_without_contact_change(conn):
    info = {"pages": 1, "buying_signals": [_signal()]}
    first = recheck.run(conn, 1, enrich_fn=lambda _: info)
    assert first["ok"] is True and first["changed"] is True
    assert first["signals"] and first["signals"][0]["confidence"] == 85
    signal_rows = sales_intelligence.list_signals(conn, lead_no=1)
    assert len(signal_rows) == 1 and signal_rows[0]["headline"] == "Public RFQ for AV system"
    task = conn.execute(
        "SELECT title, priority FROM activities WHERE lead_no=1 AND source='recheck'"
        " ORDER BY id DESC LIMIT 1").fetchone()
    assert "采购信号" in task["title"] and task["priority"] == "high"

    second = recheck.run(conn, 1, enrich_fn=lambda _: info)
    assert second["changed"] is False
    assert len(sales_intelligence.list_signals(conn, lead_no=1)) == 1


def test_first_read_backfill_does_not_promote_old_signal_as_fresh(conn):
    result = recheck.run(conn, 1, enrich_fn=lambda _: {
        "pages": 1,
        "buying_signals": [_signal()],
    }, first_read=True)
    assert result["changed"] is False
    assert sales_intelligence.list_signals(conn, lead_no=1) == []
