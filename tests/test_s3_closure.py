import asyncio
from dataclasses import asdict
import json

import pytest

from app.core.types import Concern, Obligation, ObligationConcernExtraction, ProviderResult, Task, TaskPlan
from app.research.decomposer import (
    TASK_PLAN_RESPONSE_SCHEMA, build_task_plan_repair_prompt,
    decompose_plan, generate_task_plan, parse_task_plan_output,
)
from app.research.obligation_concern_extraction import parse_obligation_concern_output
from app.research.plan_verification import verify_task_plan
from app.research.pipeline import ResearchPipeline
from app.research import pipeline as pipeline_module
from app.storage.run_store import RunStore
from app.storage.source_store import SourceStore


def extraction():
    return ObligationConcernExtraction(
        obligations=[
            Obligation("O-API", "Review architecture design"),
            Obligation("O-DB", "Review database design"),
            Obligation("O-SEC", "Review security design"),
            Obligation("O-EVID", "Retrieve supporting planning evidence"),
            Obligation("O-PLAN", "Produce a validated implementation plan"),
            Obligation("O-KEEP", "Do not omit any identified requirement"),
            Obligation("O-OPT", "Review optional deployment constraints", False),
        ],
        concerns=[Concern("C-API", "Architecture design", "api_architecture"),
                  Concern("C-DB", "Database design", "database"),
                  Concern("C-SEC", "Security design", "security")],
    )


def task_payload():
    payload = {"tasks": [
        {"task_id": "api-review", "goal": "Review architecture design. Retrieve supporting planning evidence. Produce a validated implementation plan. Do not omit any identified requirement.", "domain": "api_architecture", "depends_on": [], "evidence_needs": ["architecture design"]},
        {"task_id": "db-review", "goal": "Review database design", "domain": "database", "depends_on": ["api-review"], "evidence_needs": ["database schema design"]},
        {"task_id": "security-review", "goal": "Review security design", "domain": "security", "depends_on": ["db-review"], "evidence_needs": ["security access controls"]},
    ]}
    for task, obligations, concerns in zip(payload["tasks"],
            [["O-API", "O-EVID", "O-PLAN", "O-KEEP"], ["O-DB"], ["O-SEC"]],
            [["C-API"], ["C-DB"], ["C-SEC"]]):
        task["covers_obligations"] = obligations
        task["covers_concerns"] = concerns
    return payload


REQUEST = "Review architecture, database and security design. Retrieve supporting planning evidence, produce a validated implementation plan. Do not omit any identified requirement."


def make_plan(payload=None):
    return parse_task_plan_output(payload or task_payload(), REQUEST, extraction())


def test_complete_plan_retains_domainless_process_coverage_and_execution_input_shape():
    plan = make_plan()
    report = verify_task_plan(plan)
    assert report.valid, report.errors
    assert report.missing_required_obligations == ()
    assert report.covered_concerns == ("C-API", "C-DB", "C-SEC")
    assert "O-KEEP" in report.task_coverage["api-review"]["obligation_ids"]
    assert report.uncovered_optional_obligations == ("O-OPT",)
    for task in plan.tasks:
        assert set(asdict(task)) == {"task_id", "goal", "domain", "depends_on", "evidence_needs", "covers_obligations", "covers_concerns"}


def test_cross_domain_megatask_cannot_cover_independent_obligations_by_word_overlap():
    plan = TaskPlan(REQUEST, extraction().obligations, [], [Task(
        "one", "Review architecture design, database design and security design. Retrieve supporting planning evidence. Produce a validated implementation plan. Do not omit any identified requirement.",
        "security", evidence_needs=["security design"],
    )])
    report = verify_task_plan(plan)
    assert not report.valid
    assert {"O-API", "O-DB"} <= set(report.missing_required_obligations)


def test_similar_prefix_is_not_semantic_authentication_coverage():
    plan = TaskPlan("Review authentication", [Obligation("O1", "Review authentication")], [], [Task("T1", "Review authorization", "security")])
    assert not verify_task_plan(plan).valid


@pytest.mark.parametrize("coverage", [{}, {"api-review": []}, {"api-review": ["UNKNOWN"]}, {"api-review": ["O-API", "O-API"]}])
def test_explicit_missing_or_unknown_coverage_cannot_fall_back_to_text(coverage):
    report = verify_task_plan(make_plan(), coverage=coverage)
    assert not report.valid
    assert report.missing_required_obligations


@pytest.mark.parametrize("needs", [[], ["relevant evidence"], ["src_1234567890abcdef_c0000"], ["O999"]])
def test_positive_evidence_request_rejects_empty_or_placeholder_needs(needs):
    payload = task_payload()
    payload["tasks"][1]["evidence_needs"] = needs
    report = verify_task_plan(make_plan(payload))
    assert not report.valid
    assert any("db-review" in error and "evidence_needs" in error for error in report.errors)


def test_simple_request_without_evidence_instruction_does_not_require_needs():
    report = verify_task_plan(TaskPlan("Review authentication", [Obligation("O1", "Review authentication")], [], [Task("T1", "Review authentication", "security")]))
    assert report.valid


@pytest.mark.parametrize("user_request", [
    "Review security and include citations.",
    "Review security and provide sources without omitting required details.",
    "Retrieve supporting evidence for security and do not omit required details.",
])
def test_explicit_citations_and_positive_evidence_clause_still_require_search_needs(user_request):
    report = verify_task_plan(TaskPlan(user_request, [], [], [Task("T1", "Review security", "security")]))
    assert not report.valid
    assert any("evidence_needs" in error for error in report.errors)


def test_negated_evidence_request_does_not_force_retrieval():
    report = verify_task_plan(TaskPlan("Review security. Do not retrieve evidence.", [], [], [Task("T1", "Review security", "security")]))
    assert report.valid


def test_typed_technical_concern_requires_evidence_even_without_domain_keyword():
    report = verify_task_plan(TaskPlan(
        "Review certificate expiry and provide citations.", [],
        [Concern("C1", "Certificate expiry", "security")],
        [Task("T1", "Review certificate expiry", "security")],
    ))
    assert not report.valid
    assert any("evidence_needs" in error for error in report.errors)


@pytest.mark.parametrize("dependencies", [["Review architecture design"], ["missing"], ["db-review"], ["api-review", "api-review"]])
def test_dependency_name_unknown_self_and_duplicate_rejected(dependencies):
    payload = task_payload()
    payload["tasks"][1]["depends_on"] = dependencies
    with pytest.raises(ValueError):
        make_plan(payload)


def test_cyclic_dependency_rejected():
    payload = task_payload()
    payload["tasks"][0]["depends_on"] = ["security-review"]
    with pytest.raises(ValueError, match="cycle"):
        make_plan(payload)


@pytest.mark.parametrize("raw", ['{"tasks":[],"tasks":[]}', '{"tasks":[{"task_id":"A","task_id":"B"}]}', '<think>reasoning</think>{"tasks":[]}'])
def test_ambiguous_or_contaminated_plan_json_rejected(raw):
    with pytest.raises(ValueError):
        parse_task_plan_output(raw)


def test_extraction_duplicate_json_fields_rejected():
    with pytest.raises(ValueError, match="duplicate JSON field"):
        parse_obligation_concern_output('{"obligations":[],"concerns":[],"concerns":[]}')


@pytest.mark.parametrize("mutation", ["general", "missing_goal", "duplicate_id", "invalid_needs", "unknown_coverage"])
def test_invalid_domain_shape_ids_and_unsupported_coverage_rejected(mutation):
    payload = task_payload()
    if mutation == "general":
        payload["tasks"][0]["domain"] = "general"
    elif mutation == "missing_goal":
        del payload["tasks"][0]["goal"]
    elif mutation == "duplicate_id":
        payload["tasks"][1]["task_id"] = payload["tasks"][0]["task_id"]
    elif mutation == "invalid_needs":
        payload["tasks"][0]["evidence_needs"] = None
    else:
        payload["tasks"][0]["covers_obligations"] = ["UNKNOWN"]
    with pytest.raises(ValueError):
        make_plan(payload)


def test_real_adapter_schema_is_shared_by_initial_parse_and_semantic_repair(monkeypatch):
    from app.providers.ollama import OllamaProvider
    from app.research.registry import REGISTRY

    captured = []

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json):
            captured.append(json)
            output = task_payload()
            if len(captured) == 1:
                output["tasks"][0]["domain"] = "general"

            class Response:
                def raise_for_status(self):
                    pass

                def json(self):
                    import json as codec
                    return {"message": {"content": codec.dumps(output)}}

            return Response()

    monkeypatch.setattr("app.providers.ollama.httpx.AsyncClient", Client)

    async def run():
        provider = OllamaProvider(model="qwen3:4b")
        result = await decompose_plan(provider, REQUEST)
        assert result.plan is not None and result.repair_attempted
        await generate_task_plan(provider, user="Correct the missing process requirement.")

    asyncio.run(run())
    assert len(captured) == 3
    for payload in captured:
        assert payload["format"] == TASK_PLAN_RESPONSE_SCHEMA
        assert payload["format"]["properties"]["tasks"]["items"]["properties"]["domain"]["enum"] == list(REGISTRY)


def test_long_repair_feedback_preserves_exact_obligation_and_dependency_diagnostics():
    diagnostics = "missing obligation " + "O-API " * 120 + "; unknown dependency db-review -> absent-task"
    prompt = build_task_plan_repair_prompt(REQUEST, json.dumps(task_payload()), diagnostics, extraction=extraction(), missing_obligation_ids=("O-KEEP",))
    assert diagnostics in prompt
    assert "O-KEEP: task.goal must retain Do not omit any identified requirement" in prompt


class PlanningFixture:
    name = "deterministic-planning"
    model = "fixture"

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.plan_calls = 0
        self.prompts = []

    async def generate(self, *, system, user):
        if "OBLIGATION_CONCERN_EXTRACTOR" in system:
            return ProviderResult(json.dumps(extraction().to_dict()))
        if "TASK_PLAN_BUILDER" in system:
            self.plan_calls += 1
            self.prompts.append(user)
            return ProviderResult(json.dumps(self.outputs.pop(0)))
        if "SYNTHESIZER" in system:
            return ProviderResult("No corpus evidence in isolated test.")
        raise AssertionError("Worker must not be invoked without evidence in planning-only fixture")


@pytest.mark.parametrize("repair_succeeds", [True, False])
def test_one_semantic_repair_revalidates_all_coverage_before_handoff(tmp_path, monkeypatch, repair_succeeds):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "dev")
    invalid = task_payload()
    invalid["tasks"][0]["goal"] = "Review architecture design"
    provider = PlanningFixture([invalid, task_payload() if repair_succeeds else invalid])
    monkeypatch.setattr(pipeline_module, "get_provider", lambda *_: provider)
    run = asyncio.run(ResearchPipeline(SourceStore(str(tmp_path / "sources")), RunStore(str(tmp_path / "runs"))).run(REQUEST, "C", "fixture"))
    assert provider.plan_calls == 2
    repairs = [event for event in run["events"] if event["stage"] == "planning_repair"]
    assert len(repairs) == 1 and repairs[0]["attempt"] == 1
    assert "O-KEEP" in provider.prompts[-1]
    handoffs = [event for event in run["events"] if event["stage"] == "validated_plan_handoff"]
    if repair_succeeds:
        assert handoffs and handoffs[0]["verification_valid"]
        api_task = next(task for task in handoffs[0]["tasks"] if task["domain"] == "api_architecture")
        assert handoffs[0]["task_coverage"][api_task["task_id"]]["obligation_ids"]
        assert run["status"] != "FAILED"
        assert all(task["evidence_needs"] for task in handoffs[0]["tasks"])
    else:
        assert not handoffs and run["status"] == "FAILED"
        assert not any(event["stage"] == "task_retrieval" for event in run["events"])
