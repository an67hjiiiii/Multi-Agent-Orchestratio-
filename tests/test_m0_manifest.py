import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core import telemetry
from app.storage.source_store import SourceStore
from scripts import create_m0_manifest


def _set_m0_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    monkeypatch.setenv("PROVIDER", "fake")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "qwen3:4b")


def test_build_manifest_binds_m0_config_and_tracked_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _set_m0_environment(monkeypatch)

    manifest = create_m0_manifest.build_manifest(
        data_dir=tmp_path / "source-store",
        created_at=datetime(2026, 9, 6, tzinfo=timezone.utc),
    )

    assert manifest["manifest_schema"] == "m0-release-v1"
    assert manifest["milestone"] == "M0"
    assert manifest["claim_status"] == "CANDIDATE_ONLY_UNTIL_LOCAL_GATE_PASSES"
    assert manifest["allowed_conditions"] == ["A"]
    assert manifest["runtime_config"]["implementation_profile"] == "m0"
    assert manifest["runtime_config"]["provider"] == "fake"
    assert manifest["model"]["research_frozen"] is False
    assert manifest["created_at"] == "2026-09-06T00:00:00+00:00"
    assert manifest["corpus"]["store_file_present"] is False
    assert manifest["corpus"]["chunk_count"] == 0
    assert manifest["missing_files"] == []
    assert manifest["files"]["app/core/telemetry.py"] == create_m0_manifest.sha256(
        create_m0_manifest.ROOT / "app/core/telemetry.py"
    )
    assert manifest["trace_metrics_contract"]["document"] == "docs/M0_TRACE_METRICS.md"


def test_build_manifest_records_source_store_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _set_m0_environment(monkeypatch)
    data_dir = tmp_path / "source-store"
    store = SourceStore(str(data_dir))
    store.import_text("fixture.md", "A deterministic M0 source fixture.")

    manifest = create_m0_manifest.build_manifest(data_dir=data_dir)

    assert manifest["corpus"]["store_file_present"] is True
    assert manifest["corpus"]["chunk_count"] == len(store.chunks())
    assert manifest["corpus_snapshot_id"] == store.snapshot_id()


def test_manifest_builder_rejects_non_m0_profile(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "dev")

    with pytest.raises(ValueError, match="requires IMPLEMENTATION_PROFILE=m0"):
        create_m0_manifest.build_manifest()


def test_manifest_import_is_side_effect_free():
    output_path = create_m0_manifest.ROOT / "config/releases/m0_candidate_manifest.json"
    original = output_path.read_bytes()

    importlib.reload(create_m0_manifest)

    assert output_path.read_bytes() == original


def test_write_manifest_round_trips_json(tmp_path: Path):
    output_path = tmp_path / "release" / "manifest.json"
    payload = {"manifest_schema": "m0-release-v1", "claim_status": "CANDIDATE"}

    result = create_m0_manifest.write_manifest(payload, output_path)

    assert result == output_path
    assert json.loads(output_path.read_text(encoding="utf-8")) == payload
    assert output_path.read_text(encoding="utf-8").endswith("\n")


def test_process_rss_converts_bytes_to_finite_mib(monkeypatch: pytest.MonkeyPatch):
    fake_psutil = SimpleNamespace(
        Process=lambda _pid: SimpleNamespace(
            memory_info=lambda: SimpleNamespace(rss=3 * 1024 * 1024 + 512 * 1024)
        )
    )
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    assert telemetry.process_rss_mb() == 3.5


def test_gpu_memory_uses_largest_valid_device_value(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        telemetry.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout="128\nnot-a-number\n256.4\n-1\nnan\n",
        ),
    )

    assert telemetry.gpu_memory_mb() == 256.4


def test_gpu_memory_is_na_when_command_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        telemetry.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout="512\n"),
    )

    assert telemetry.gpu_memory_mb() is None
