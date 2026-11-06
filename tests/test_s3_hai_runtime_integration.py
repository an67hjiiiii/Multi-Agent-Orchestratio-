from __future__ import annotations

import asyncio
import json

from app.core.types import ProviderResult, SourceChunk, Usage
from app.providers.fake import FakeProvider
from app.research import pipeline as pipeline_module
from app.research.pipeline import ResearchPipeline
from app.storage.run_store import RunStore
from app.storage.source_store import SourceStore


class RecordingRunStore(RunStore):
    def __init__(self, root: str):
        super().__init__(root)
        self.saved_lifecycle_statuses: list[str | None] = []

    def save(self, run: dict) -> None:
        self.saved_lifecycle_statuses.append(run.get("lifecycle_status"))
        super().save(run)


class ScriptedPlanningProvider:
    name = "scripted-planning"
    model = "scripted-planning-test"

    def __init__(
        self,
        plan_outputs: list[str],
        obligations: list[dict],
        concerns: list[dict] | None = None,
    ):
        self.plan_outputs = list(plan_outputs)
        self.obligations = obligations
        self.concerns = concerns or []
        self.plan_prompts: list[str] = []
        self.worker_calls = 0

    async def generate(self, *, system: str, user: str) -> ProviderResult:
        marker = system.upper()
        if "OBLIGATION_CONCERN_EXTRACTOR" in marker:
            text = json.dumps(
                {"obligations": self.obligations, "concerns": self.concerns},
                ensure_ascii=False,
            )
        elif "TASK_PLAN_BUILDER" in marker:
            self.plan_prompts.append(user)
            text = self.plan_outputs.pop(0)
        elif "WORKER" in marker:
            self.worker_calls += 1
            text = json.dumps(
                {
                    "status": "NO_EVIDENCE",
                    "answer": "No evidence available.",
                    "citations": [],
                    "missing_information": ["relevant evidence"],
                }
            )
        elif "SYNTHESIZER" in marker:
            text = "Synthesis completed."
        else:
            raise AssertionError(f"Unexpected provider system prompt: {system}")
        return ProviderResult(text=text, usage=Usage(1, 1), model=self.model)


def _task_plan(goal: str, domain: str, *, concerns: bool = False) -> str:
    return json.dumps(
        {
            "tasks": [
                {
                    "task_id": "T1",
                    "goal": goal,
                    "domain": domain,
                    "depends_on": [],
                    "evidence_needs": [],
                    "covers_obligations": ["O1"],
                    "covers_concerns": ["C1"] if concerns else [],
                }
            ]
        },
        ensure_ascii=False,
    )


def _api_request_concern() -> dict[str, str]:
    return {
        "concern_id": "C1",
        "description": "General concern about API request validation and error responses",
        "domain": "api_architecture",
    }


def test_pipeline_runs_verified_plan_and_traces_scored_planning_evidence(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "dev")
    provider = FakeProvider()
    monkeypatch.setattr(pipeline_module, "get_provider", lambda *_args: provider)
    sources = SourceStore(str(tmp_path / "sources"))
    sources.import_text("api.md", "The API endpoint validates requests and error responses.")
    runs = RecordingRunStore(str(tmp_path / "runs"))
    pipeline = ResearchPipeline(sources, runs)
    planning_chunk = SourceChunk(
        chunk_id="planning-api-1",
        source_id="planning-api",
        source_name="planning_api.md",
        text="Preserve API error and dependency requirements.",
        index=0,
        score=0.87,
    )
    pipeline.planning.search = lambda _query, **_kwargs: [planning_chunk]

    result = asyncio.run(
        pipeline.run("Review API endpoint error handling", "C", "fake")
    )

    stages = [event["stage"] for event in result["events"]]
    assert stages.index("obligation_concern_extraction") < stages.index(
        "planning_retrieval"
    ) < stages.index("planning_generation") < stages.index(
        "plan_verification"
    ) < stages.index("validated_plan_handoff") < stages.index("task_retrieval")
    retrieval = next(
        event for event in result["events"] if event["stage"] == "planning_retrieval"
    )
    assert retrieval["enabled"] is True
    assert retrieval["selected"] == ["planning-api-1"]
    assert retrieval["selected_evidence"] == [
        {"evidence_id": "planning-api-1", "score": 0.87}
    ]
    assert retrieval["fallback_reason"] is None
    post_normalization = next(
        event
        for event in result["events"]
        if event["stage"] == "plan_verification"
        and event.get("phase") == "post_normalization"
    )
    assert post_normalization["valid"] is True
    normalization_index = stages.index("normalization")
    post_normalization_index = result["events"].index(post_normalization)
    handoff_index = stages.index("validated_plan_handoff")
    assert normalization_index < post_normalization_index < handoff_index
    assert result["events"][handoff_index]["execution_order"] == [
        task["task_id"] for task in result["events"][handoff_index]["tasks"]
    ]
    assert result["lifecycle_status"] == "COMPLETED"
    assert result["status"] == "COMPLETE"
    assert runs.saved_lifecycle_statuses == ["PENDING", "RUNNING", "COMPLETED"]
    assert runs.list()[0]["lifecycle_status"] == "COMPLETED"


def test_reproduced_api_plan_reaches_handoff_without_unneeded_repair(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "dev")
    request = "Review API request validation and error responses."
    provider = ScriptedPlanningProvider(
        plan_outputs=[_task_plan(request.rstrip("."), "api_architecture", concerns=True)],
        obligations=[
            {
                "obligation_id": "O1",
                "description": "Review API request validation and error responses",
                "required": True,
            }
        ],
        concerns=[_api_request_concern()],
    )
    monkeypatch.setattr(pipeline_module, "get_provider", lambda *_args: provider)
    sources = SourceStore(str(tmp_path / "sources"))
    runs = RunStore(str(tmp_path / "runs"))

    result = asyncio.run(ResearchPipeline(sources, runs).run(request, "C", "fake"))

    initial_verification = next(
        event
        for event in result["events"]
        if event["stage"] == "plan_verification" and event.get("phase") == "initial"
    )
    assert initial_verification["valid"] is True
    assert initial_verification["covered_concerns"] == ["C1"]
    assert not any(event["stage"] == "planning_repair" for event in result["events"])
    assert any(event["stage"] == "validated_plan_handoff" for event in result["events"])
    assert result["lifecycle_status"] == "COMPLETED"
    assert len(provider.plan_prompts) == 1


def test_missing_concern_repair_gets_canonical_domains_and_can_handoff(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "dev")
    provider = ScriptedPlanningProvider(
        plan_outputs=[
            _task_plan("Review unrelated database indexing", "database", concerns=True),
            _task_plan("Review API request validation and error responses", "api_architecture", concerns=True),
        ],
        obligations=[
            {
                "obligation_id": "O1",
                "description": "Review API request validation and error responses",
                "required": True,
            }
        ],
        concerns=[_api_request_concern()],
    )
    monkeypatch.setattr(pipeline_module, "get_provider", lambda *_args: provider)
    sources = SourceStore(str(tmp_path / "sources"))
    runs = RunStore(str(tmp_path / "runs"))

    result = asyncio.run(
        ResearchPipeline(sources, runs).run(
            "Review API request validation and error responses.", "C", "scripted-planning"
        )
    )

    initial_verification = next(
        event
        for event in result["events"]
        if event["stage"] == "plan_verification" and event.get("phase") == "initial"
    )
    assert initial_verification["missing_concerns"] == ["C1"]
    repair_prompt = provider.plan_prompts[1]
    assert "missing concern coverage: C1" in repair_prompt
    assert "C1: General concern about API request validation and error responses" in repair_prompt
    assert "REQUIRED CONCERN COVERAGE:" in repair_prompt
    assert "task.goal" in repair_prompt
    assert "Do not substitute concern IDs or evidence_needs for goal coverage" in repair_prompt
    assert '"domain":"security|database|api_architecture"' in repair_prompt
    repair = next(
        event for event in result["events"] if event["stage"] == "planning_repair"
    )
    assert repair["accepted"] is True
    assert any(event["stage"] == "validated_plan_handoff" for event in result["events"])
    assert result["lifecycle_status"] == "COMPLETED"
    assert provider.worker_calls == 1


def test_enabled_planning_records_explicit_empty_evidence_fallback(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "dev")
    monkeypatch.setattr(pipeline_module, "get_provider", lambda *_args: FakeProvider())
    sources = SourceStore(str(tmp_path / "sources"))
    runs = RunStore(str(tmp_path / "runs"))
    result = asyncio.run(
        ResearchPipeline(sources, runs).run(
            "Review an unspecified catalog entry", "C", "fake"
        )
    )

    retrieval = next(
        event for event in result["events"] if event["stage"] == "planning_retrieval"
    )
    assert retrieval["enabled"] is True
    assert retrieval["selected_evidence"] == []
    assert retrieval["fallback_reason"] == (
        "no_planning_evidence_selected; continuing without retrieved planning context"
    )
    assert result["lifecycle_status"] == "COMPLETED"
    assert result["status"] == "NO_EVIDENCE"


def test_parse_repair_uses_the_single_total_repair_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "dev")
    provider = ScriptedPlanningProvider(
        plan_outputs=[
            '{"tasks": []}',
            _task_plan("Review database query performance", "database"),
        ],
        obligations=[
            {
                "obligation_id": "O1",
                "description": "Review authentication controls",
                "required": True,
            }
        ],
    )
    monkeypatch.setattr(pipeline_module, "get_provider", lambda *_args: provider)
    sources = SourceStore(str(tmp_path / "sources"))
    runs = RecordingRunStore(str(tmp_path / "runs"))

    result = asyncio.run(
        ResearchPipeline(sources, runs).run(
            "Review authentication controls", "B", "scripted-planning"
        )
    )

    assert result["status"] == "FAILED"
    assert result["lifecycle_status"] == "FAILED"
    assert runs.saved_lifecycle_statuses == ["PENDING", "RUNNING", "FAILED"]
    assert provider.worker_calls == 0
    assert len(provider.plan_prompts) == 2
    repairs = [
        event
        for event in result["events"]
        if event["stage"] == "planning_repair"
    ]
    assert [(event["phase"], event["attempt"]) for event in repairs] == [
        ("parse", 1)
    ]
    assert not any(event["stage"] == "validated_plan_handoff" for event in result["events"])
    assert not any(event["stage"] == "task_retrieval" for event in result["events"])


def test_semantic_repair_receives_only_parser_supported_task_payload(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "dev")
    provider = ScriptedPlanningProvider(
        plan_outputs=[
            _task_plan("Review database query performance", "database"),
            _task_plan("Review authentication controls", "security"),
        ],
        obligations=[
            {
                "obligation_id": "O1",
                "description": "Review authentication controls",
                "required": True,
            }
        ],
    )
    monkeypatch.setattr(pipeline_module, "get_provider", lambda *_args: provider)
    sources = SourceStore(str(tmp_path / "sources"))
    runs = RunStore(str(tmp_path / "runs"))

    result = asyncio.run(
        ResearchPipeline(sources, runs).run(
            "Review authentication controls", "B", "scripted-planning"
        )
    )

    repair_prompt = provider.plan_prompts[1]
    previous_output = repair_prompt.split("PREVIOUS INVALID TASK PLAN:\n", 1)[1].split(
        "\n\nVALIDATION ERROR:", 1
    )[0]
    assert set(json.loads(previous_output)) == {"tasks"}
    assert result["status"] == "NO_EVIDENCE"
    assert result["lifecycle_status"] == "COMPLETED"
    repair = next(
        event
        for event in result["events"]
        if event["stage"] == "planning_repair"
    )
    assert repair["phase"] == "semantic_verification"
    assert repair["attempt"] == 1
    assert repair["accepted"] is True
    assert any(event["stage"] == "validated_plan_handoff" for event in result["events"])
    assert any(event["stage"] == "task_retrieval" for event in result["events"])
    assert provider.worker_calls == 1
