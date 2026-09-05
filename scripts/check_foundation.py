"""Run the repository's small, deterministic foundation quality gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _has_text(path: Path, text: str) -> bool:
    return path.is_file() and text in path.read_text(encoding="utf-8")


def check_policy() -> list[str]:
    required = {
        "pyproject.toml": '[tool.pytest.ini_options]',
        ".editorconfig": "end_of_line = lf",
        ".gitattributes": "* text=auto eol=lf",
        "docs/QUALITY_GATES.md": "Vitest",
        "tests/foundation/frontend_contract.test.mjs": "documentedRoutes",
    }
    errors = [
        f"missing or incomplete {relative}"
        for relative, marker in required.items()
        if not _has_text(ROOT / relative, marker)
    ]
    if not _has_text(ROOT / ".editorconfig", "[*.ps1]"):
        errors.append(".editorconfig does not declare the PowerShell section")
    if not _has_text(ROOT / ".gitattributes", "*.ps1 text eol=crlf"):
        errors.append(".gitattributes does not declare CRLF for PowerShell")
    return errors


def run_backend() -> int:
    print("[RUN] backend pytest")
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT,
        check=False,
    )
    return completed.returncode


def run_frontend() -> int:
    package_path = ROOT / "frontend" / "package.json"
    if not package_path.is_file():
        print("[SKIP] frontend Vitest contract (frontend is not present in this checkout)")
        return 0

    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[FAIL] frontend/package.json: {exc}")
        return 1

    dependencies = {
        **package.get("dependencies", {}),
        **package.get("devDependencies", {}),
    }
    if "vitest" not in dependencies:
        print("[FAIL] frontend/package.json does not declare Vitest")
        return 1

    frontend_dir = package_path.parent
    vitest_name = "vitest.cmd" if sys.platform == "win32" else "vitest"
    vitest = frontend_dir / "node_modules" / ".bin" / vitest_name
    if not vitest.is_file():
        print("[FAIL] frontend dependencies are not installed; run npm install first")
        return 1

    print("[RUN] frontend Vitest contract")
    completed = subprocess.run(
        [str(vitest), "run", "../tests/foundation/frontend_contract.test.mjs"],
        cwd=frontend_dir,
        check=False,
    )
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-backend", action="store_true")
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--policy-only", action="store_true")
    args = parser.parse_args()

    errors = check_policy()
    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1
    print("[PASS] repository quality-tooling policy")

    if args.policy_only:
        return 0

    if not args.skip_backend and run_backend() != 0:
        return 1
    if not args.skip_frontend and run_frontend() != 0:
        return 1
    print("[PASS] foundation quality gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
