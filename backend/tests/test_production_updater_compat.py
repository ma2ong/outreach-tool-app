from pathlib import Path


def test_windows_updater_is_ascii_and_has_no_inline_python_command():
    repo = Path(__file__).resolve().parents[2]
    script = (repo / "scripts" / "update_production.ps1").read_text(encoding="utf-8")
    assert script.isascii()
    assert "python -c" not in script
    assert "production_acceptance.py" in script


def test_production_acceptance_module_imports():
    import production_acceptance

    assert callable(production_acceptance.run_checks)
    assert callable(production_acceptance.main)
