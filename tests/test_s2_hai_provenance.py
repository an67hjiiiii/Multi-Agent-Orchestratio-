from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.storage.postgres.base import Base
from app.storage.postgres.runtime import PostgresAuthStore, PostgresSourceStore
from app.storage.source_store import SourceStore


def test_file_source_and_chunk_keep_stable_provenance():
    with TemporaryDirectory(dir=Path.cwd()) as root:
        store = SourceStore(str(Path(root) / "data"))
        imported = store.import_text(
            "guide.md",
            "Source provenance is preserved.",
            provenance={"source_format": "md", "ingestion_version": "s2-test"},
        )

        source = store.source(imported["source_id"])
        assert source["provenance"]["source_hash"] == imported["source_hash"]
        assert source["provenance"]["source_format"] == "md"
        assert source["chunks"][0]["provenance"]["chunk_id"] == source["chunks"][0]["chunk_id"]
        assert source["chunks"][0]["provenance"]["chunk_index"] == 0


def test_postgres_source_and_chunk_keep_provenance():
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
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = PostgresAuthStore(factory).register(
        email="provenance@example.test", password="long-enough-password"
    )
    store = PostgresSourceStore(factory, owner["user_id"])
    imported = store.import_text(
        "guide.md",
        "PostgreSQL provenance is authoritative.",
        provenance={"source_format": "md", "ingestion_version": "s2-test"},
    )

    source = store.source(imported["source_id"])
    chunk = source["chunks"][0]
    assert source["provenance"]["source_hash"] == imported["source_hash"]
    assert chunk["provenance"]["source_id"] == imported["source_id"]
    assert chunk["provenance"]["chunk_index"] == 0
