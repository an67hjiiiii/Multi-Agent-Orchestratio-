# Foundation quality gates

This repository keeps its first quality gate small and local. The gate checks
repository policy, runs the backend pytest suite, and runs the frontend Vitest
contract when a `frontend/` package is present.

## Commands

From PowerShell on Windows:

```powershell
.\scripts\check_repo.ps1
```

The Python entry point is useful in CI or other shells:

```powershell
python scripts/check_foundation.py
python scripts/check_foundation.py --policy-only
```

The configured `.venv\Scripts\python.exe` is preferred by the PowerShell
wrapper. When that environment does not exist, the wrapper uses an available
`python` command or the Windows `py -3` launcher; it does not create or install
an environment.

## Gates

- **Backend:** `pyproject.toml` scopes pytest to `tests/`, with the repository
  root on `pythonpath`.
- **Frontend:** `tests/foundation/frontend_contract.test.mjs` is a Vitest
  contract for the local `/api` boundary. It checks that frontend source uses
  documented routes and does not contain direct provider, credential, or
  absolute-host calls. It is skipped while `frontend/` is absent; once the
  frontend package exists, the validator requires Vitest and installed
  frontend dependencies, then runs this file without implicitly downloading
  packages.
- **Line endings:** text defaults to LF. PowerShell, batch, and command files
  intentionally use CRLF. `.editorconfig` guides editors and `.gitattributes`
  makes Git checkout behavior explicit.

These checks establish wiring and repository hygiene. They do not prove local
LLM quality, milestone completion, semantic answer correctness, or a research
evaluation result.
