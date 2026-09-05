from pathlib import Path

import pytest

from app.storage.source_store import SourceStore


def test_source_and_chunk_locator(tmp_path: Path):
    store = SourceStore(str(tmp_path / "data"))
    imported = store.import_text("x.md", "Alpha beta gamma.\n\nDelta epsilon.")
    assert imported["source_id"]
    rows = store.list_sources()
    assert rows[0]["source_name"] == "x.md"
    source = store.source(imported["source_id"])
    assert source and source["chunks"]
    chunk_id = source["chunks"][0]["chunk_id"]
    chunk = store.chunk(chunk_id)
    assert chunk and chunk["source_id"] == imported["source_id"]
    assert store.snapshot_id().startswith("corpus_")


def test_utf8_identity_is_stable_across_normalization_and_restart(tmp_path: Path):
    data_dir = tmp_path / "data"
    first = SourceStore(data_dir)
    initial = first.import_text(
        "cafe\u0301.md",
        "\ufeffTiếng Việt\r\n\r\nMục tiêu.\x00",
    )

    second = SourceStore(data_dir)
    repeat = second.import_text("café.md", "Tiếng Việt\n\nMục tiêu.")

    assert repeat["source_id"] == initial["source_id"]
    assert repeat["chunks_added"] == 0
    assert repeat["snapshot_id"] == initial["snapshot_id"]
    assert second.source(initial["source_id"])["chunks"][0]["text"] == (
        "Tiếng Việt\n\nMục tiêu."
    )
    assert "Tiếng Việt" in (data_dir / "sources.json").read_text(encoding="utf-8")


def test_source_store_rejects_empty_normalized_input(tmp_path: Path):
    store = SourceStore(tmp_path / "data")

    with pytest.raises(ValueError, match="source_name must not be empty"):
        store.import_text("  ", "content")
    with pytest.raises(ValueError, match="text must not be empty"):
        store.import_text("notes.md", "\ufeff\x00\r\n")
