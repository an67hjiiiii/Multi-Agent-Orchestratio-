from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.storage.postgres.base import Base
from app.storage.postgres.runtime import PostgresAuthStore, PostgresSourceStore
import app.storage.postgres.runtime as runtime_module


def _factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(
        engine,
        "connect",
        lambda connection, _record: connection.create_function(
            "btrim", 1, lambda value: value.strip()
        ),
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_source_import_persists_ready_status_and_failed_reimport(monkeypatch):
    factory = _factory()
    owner = PostgresAuthStore(factory).register(
        email="lifecycle@example.test", password="long-enough-password"
    )
    store = PostgresSourceStore(factory, owner["user_id"])

    imported = store.import_text("notes.md", "Stable source text")
    source_id = imported["source_id"]
    assert store.source_status(source_id)["status"] == "READY"

    def fail_chunks(*_args, **_kwargs):
        raise RuntimeError("chunking failed")

    monkeypatch.setattr(runtime_module, "make_chunks", fail_chunks)
    with pytest.raises(RuntimeError, match="chunking failed"):
        store.import_text("notes.md", "Stable source text")

    failed = store.source_status(source_id)
    assert failed["status"] == "FAILED"
    assert failed["metadata"]["error_type"] == "RuntimeError"
    assert store.chunks() == []
