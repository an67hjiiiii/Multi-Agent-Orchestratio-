from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_pytest_gate_is_configured_for_repo_tests() -> None:
    config = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.pytest.ini_options]" in config
    assert 'testpaths = ["tests"]' in config
    assert 'pythonpath = ["."]' in config


def test_windows_line_ending_policy_is_explicit() -> None:
    editorconfig = (ROOT / ".editorconfig").read_text(encoding="utf-8")
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "end_of_line = lf" in editorconfig
    assert "[*.ps1]" in editorconfig
    assert "end_of_line = crlf" in editorconfig
    assert "* text=auto eol=lf" in attributes
    assert "*.ps1 text eol=crlf" in attributes


def test_vitest_contract_is_kept_outside_production_code() -> None:
    contract = ROOT / "tests" / "foundation" / "frontend_contract.test.mjs"
    assert contract.is_file()
    assert "documentedRoutes" in contract.read_text(encoding="utf-8")
