import asyncio
import os
from pathlib import Path
from app.research.pipeline import ResearchPipeline
from app.storage.source_store import SourceStore
from app.storage.run_store import RunStore


def test_a_b_c_fake_dev_profile(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "dev")
    sources=SourceStore(str(tmp_path/'data'))
    sources.import_text('security.md','Authentication uses bearer JWT. Authorization checks permissions server-side.')
    sources.import_text('db.md','Database queries should use indexes for frequent identifiers.')
    runs=RunStore(str(tmp_path/'runs'))
    pipe=ResearchPipeline(sources,runs)
    for condition in ['A','B','C','C-P','C-N','C-O']:
        run=asyncio.run(pipe.run('Review JWT security, database query and API architecture',condition,'fake'))
        assert run['condition']==condition
        assert run['answer']
        assert run['status'] != 'FAILED'
        assert run['metrics']['llm_calls']>=1
        assert runs.get(run['run_id']) is not None


def test_m0_rejects_non_a(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    sources=SourceStore(str(tmp_path/'data'))
    runs=RunStore(str(tmp_path/'runs'))
    pipe=ResearchPipeline(sources,runs)
    try:
        asyncio.run(pipe.run('anything','B','fake'))
        assert False, 'B must be rejected in M0 profile'
    except ValueError as exc:
        assert 'not available in profile m0' in str(exc)


def test_m0_a_has_valid_citation_and_no_evidence_state(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    sources=SourceStore(str(tmp_path/'data'))
    sources.import_text('api.md','The API contract defines request validation and error responses.')
    runs=RunStore(str(tmp_path/'runs'))
    pipe=ResearchPipeline(sources,runs)
    good=asyncio.run(pipe.run('What does the API contract define?','A','fake'))
    assert good['status']=='COMPLETE'
    assert good['task_results'][0]['citations']
    assert good['metrics']['citation_locator_validity']==1.0
    missing=asyncio.run(pipe.run('What is the production deployment region?','A','fake'))
    assert missing['status']=='NO_EVIDENCE'
    assert not missing['task_results'][0]['citations']


def test_provider_timeout_persists_terminal_failed_run(tmp_path: Path, monkeypatch):
    from app.research import pipeline as pipeline_module

    class TimeoutProvider:
        name = "timeout-test"
        model = "timeout-test"

        async def generate(self, *, system: str, user: str):
            raise TimeoutError("simulated provider timeout")

    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "m0")
    sources = SourceStore(str(tmp_path / "data"))
    sources.import_text("api.md", "The API validates requests.")
    runs = RunStore(str(tmp_path / "runs"))
    monkeypatch.setattr(pipeline_module, "get_provider", lambda *_args: TimeoutProvider())

    result = asyncio.run(
        ResearchPipeline(sources, runs).run("Summarize the API", "A", "timeout-test")
    )

    assert result["status"] == "FAILED"
    assert result["events"][-1]["stage"] == "run_failed"
    assert result["events"][-1]["error_type"] == "TimeoutError"
    assert runs.get(result["run_id"]) == result
