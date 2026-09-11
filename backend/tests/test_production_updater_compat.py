from pathlib import Path


def test_windows_updater_is_ascii_and_has_no_inline_python_command():
    repo = Path(__file__).resolve().parents[2]
    script = (repo / "scripts" / "update_production.ps1").read_text(encoding="utf-8")
    assert script.isascii()
    # ASCII alone is not enough. On 2026-09-11 an edit wrote the frontend path with a
    # real form feed in it instead of the two characters that spell it: ASCII, invisible
    # on screen, and enough to make npm print its own help instead of installing.
    stray = {c for c in script if ord(c) < 32 and ord(c) not in (9, 10, 13)}
    assert not stray, f'script carries control characters: {[hex(ord(c)) for c in stray]}'
    assert "python -c" not in script
    assert "production_acceptance.py" in script


def test_the_updater_proves_the_code_before_it_touches_production():
    """2026-09-11: a commit whose tests were red reached production because this script
    installs, builds and restarts without ever running them. One of those failures was
    Korean customers vanishing from the DM queue - silently, in the market this product
    is mostly aimed at. Building is not proving.
    """
    repo = Path(__file__).resolve().parents[2]
    script = (repo / "scripts" / "update_production.ps1").read_text(encoding="utf-8")
    assert "pytest" in script, "deploy does not run the backend tests"
    assert "run typecheck" in script, "vite build does not typecheck; nothing else would"
    assert script.index("pytest") < script.index("Restart local service"),         "tests must run before the service is touched, not after"


def test_the_frontend_has_a_typecheck_script():
    repo = Path(__file__).resolve().parents[2]
    package = (repo / "frontend" / "package.json").read_text(encoding="utf-8")
    assert '"typecheck"' in package


def test_production_acceptance_module_imports():
    import production_acceptance

    assert callable(production_acceptance.run_checks)
    assert callable(production_acceptance.main)
