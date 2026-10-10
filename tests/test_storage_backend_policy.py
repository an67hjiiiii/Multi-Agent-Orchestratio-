from __future__ import annotations

import pytest

from app import main
from app.storage.postgres.config import PostgresConfigurationError
from app.storage.source_store import SourceStore
from app.storage.run_store import RunStore


def test_product_storage_defaults_to_postgres_and_fails_closed_without_url(monkeypatch):
    monkeypatch.delenv("APP_STORAGE_BACKEND", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(PostgresConfigurationError, match="DATABASE_URL must be set"):
        main._configured_stores()


def test_product_storage_selects_postgres_when_explicitly_configured(monkeypatch):
    from app.storage.postgres.runtime import PostgresAuthStore

    monkeypatch.setenv("APP_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://cap1:temporary@127.0.0.1:5432/cap1"
    )
    monkeypatch.delenv("LOCAL_AUTH_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("LOCAL_AUTH_ADMIN_PASSWORD", raising=False)

    auth, sources, runs, runtime = main._configured_stores()

    assert isinstance(auth, PostgresAuthStore)
    assert sources is None
    assert runs is None
    assert runtime is not None
    runtime[0].dispose()


def test_file_stores_require_explicit_backend_selection(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(main, "RUNS_DIR", str(tmp_path / "runs"))
    auth, sources, runs, postgres_runtime = main._configured_stores("file")

    assert auth.__class__.__name__ == "AuthStore"
    assert isinstance(sources, SourceStore)
    assert isinstance(runs, RunStore)
    assert postgres_runtime is None
