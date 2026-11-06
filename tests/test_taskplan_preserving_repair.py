"""Deterministic reproduction of lost process coverage / destructive repair."""
import asyncio
from copy import deepcopy
import json

import pytest

from app.core.types import Concern, Obligation, ObligationConcernExtraction, ProviderResult
from app.research import pipeline as pipeline_module
from app.research.decomposer import build_task_plan_prompt, parse_task_plan_output, task_plan_response_schema
from app.research.normalizer import normalize_tasks
from app.research.pipeline import ResearchPipeline
from app.research.plan_verification import validate_repaired_plan, verify_task_plan
from app.storage.run_store import RunStore
from app.storage.source_store import SourceStore


REQUEST = "Review database consistency and security permissions. Explain dependencies, retrieve supporting evidence and preserve every constraint."


def requirements():
    return ObligationConcernExtraction(
        obligations=[
            Obligation("storage", "Review database consistency"),
            Obligation("access", "Review security permissions"),
            Obligation("ordering", "Explain dependency direction"),
            Obligation("grounding", "Retrieve supporting evidence"),
            Obligation("completeness", "Do not omit any identified constraint"),
        ],
        concerns=[Concern("consistency", "Database consistency", "database"),
                  Concern("permissions", "Security permissions", "security")],
    )


def initial_payload():
    return {"tasks": [
        {"task_id": "storage-review", "goal": "Review database consistency", "domain": "database",
         "depends_on": [], "evidence_needs": [], "covers_obligations": ["storage"], "covers_concerns": ["consistency"]},
        {"task_id": "access-review", "goal": "Review security permissions", "domain": "security",
         "depends_on": ["storage-review"], "evidence_needs": [], "covers_obligations": ["access"], "covers_concerns": ["permissions"]},
    ]}


def repaired_payload():
    payload = initial_payload()
    task = payload["tasks"][0]
    task["goal"] += ". Explain dependency direction. Retrieve supporting evidence. Do not omit any identified constraint."
    task["covers_obligations"] += ["ordering", "grounding", "completeness"]
    task["evidence_needs"] = ["database consistency constraints"]
    payload["tasks"][1]["evidence_needs"] = ["security permission boundaries"]
    return payload


class Provider:
    name = "deterministic-plan"
    model = "fixture"

    def __init__(self, repair):
        self.outputs = [initial_payload(), repair]
        self.calls = []

    async def generate_structured(self, *, system, user, response_schema):
        if "OBLIGATION_CONCERN_EXTRACTOR" in system:
            return ProviderResult(json.dumps(requirements().to_dict()))
        self.calls.append((user, response_schema))
        return ProviderResult(json.dumps(self.outputs.pop(0)))

    async def generate(self, *, system, user):
        if "OBLIGATION_CONCERN_EXTRACTOR" in system:
            return ProviderResult(json.dumps(requirements().to_dict()))
        if "SYNTHESIZER" in system:
            return ProviderResult("No corpus evidence in this isolated test.")
        raise AssertionError("No live provider or worker generation permitted")


def test_required_ids_schema_and_no_text_fallback():
    extracted = requirements()
    prompt = build_task_plan_prompt(REQUEST, extraction=extracted)
    data = json.loads(prompt.split("REQUIREMENTS JSON:\n")[1].split("\n\nPLANNING EVIDENCE")[0])
    assert data["required_obligation_ids"] == [item.obligation_id for item in extracted.obligations]
    assert data["required_concern_ids"] == [item.concern_id for item in extracted.concerns]
    fields = task_plan_response_schema(extracted)["properties"]["tasks"]["items"]["properties"]
    assert fields["covers_obligations"]["items"]["enum"] == data["required_obligation_ids"]
    assert fields["covers_concerns"]["items"]["enum"] == data["required_concern_ids"]
    assert "general" not in fields["domain"]["enum"]
    payload = repaired_payload()
    for task in payload["tasks"]:
        del task["covers_obligations"]
        del task["covers_concerns"]
    report = verify_task_plan(parse_task_plan_output(payload, REQUEST, extracted))
    assert not report.valid
    assert set(report.missing_required_obligations) == set(data["required_obligation_ids"])
    assert set(report.missing_concerns) == set(data["required_concern_ids"])


@pytest.mark.parametrize("drop_valid_coverage", [False, True])
def test_repair_preserves_good_coverage_or_no_handoff(tmp_path, monkeypatch, drop_valid_coverage):
    monkeypatch.setenv("IMPLEMENTATION_PROFILE", "dev")
    repair = repaired_payload()
    if drop_valid_coverage:
        # Final union still covers everything, but moving a valid task's claims
        # elsewhere must not disguise destructive repair.
        extra = deepcopy(repair["tasks"][1])
        extra["task_id"] = "replacement"
        repair["tasks"].append(extra)
        repair["tasks"][1]["covers_obligations"] = []
        repair["tasks"][1]["covers_concerns"] = []
        candidate = parse_task_plan_output(repair, REQUEST, requirements())
        assert verify_task_plan(candidate).valid
        assert not validate_repaired_plan(parse_task_plan_output(initial_payload(), REQUEST, requirements()), candidate).valid
    provider = Provider(repair)
    monkeypatch.setattr(pipeline_module, "get_provider", lambda *_: provider)
    result = asyncio.run(ResearchPipeline(SourceStore(str(tmp_path / "sources")), RunStore(str(tmp_path / "runs"))).run(REQUEST, "C", "fixture"))
    assert len(provider.calls) == 2
    assert provider.calls[0][1] == provider.calls[1][1] == task_plan_response_schema(requirements())
    prompt = provider.calls[1][0]
    assert "PRESERVATION JSON:" in prompt
    assert "missing required obligation coverage: ordering, grounding, completeness" in prompt
    assert "task storage-review requires subject-specific evidence_needs" in prompt
    assert "task access-review requires subject-specific evidence_needs" in prompt
    handoffs = [event for event in result["events"] if event["stage"] == "validated_plan_handoff"]
    if drop_valid_coverage:
        assert not handoffs
        assert result["status"] == "FAILED"
    else:
        assert len(handoffs) == 1
        handoff = handoffs[0]
        assert handoff["verification_valid"]
        assert {item for task in handoff["tasks"] for item in task["covers_obligations"]} == {item.obligation_id for item in requirements().obligations}
        assert {item for task in handoff["tasks"] for item in task["covers_concerns"]} == {item.concern_id for item in requirements().concerns}
        assert handoff["tasks"] == repair["tasks"]
        assert all(task["evidence_needs"] for task in handoff["tasks"])


@pytest.mark.parametrize("field", ["covers_obligations", "covers_concerns"])
@pytest.mark.parametrize("values", [["unknown"], ["storage", "storage"]])
def test_invalid_coverage_ids_rejected(field, values):
    payload = repaired_payload()
    payload["tasks"][0][field] = values
    with pytest.raises(ValueError):
        parse_task_plan_output(payload, REQUEST, requirements())


def test_normalization_retains_explicit_task_identity_and_distinct_claims():
    tasks = parse_task_plan_output(repaired_payload(), REQUEST, requirements()).tasks
    duplicate_goal = deepcopy(tasks[0])
    duplicate_goal.task_id = "different-obligation"
    duplicate_goal.covers_obligations = ["ordering"]
    normalized, removed = normalize_tasks([*tasks, duplicate_goal])
    assert removed == 0
    assert [task.task_id for task in normalized] == [task.task_id for task in [*tasks, duplicate_goal]]
    assert normalized[0].covers_obligations == tasks[0].covers_obligations


def test_repair_cannot_flip_polarity_of_verified_goal_with_same_words():
    original = parse_task_plan_output(repaired_payload(), REQUEST, requirements())
    payload = repaired_payload()
    payload["tasks"][0]["goal"] = payload["tasks"][0]["goal"].replace(
        "Do not omit any identified constraint.", "Omit any identified constraint. Do not review."
    )
    candidate = parse_task_plan_output(payload, REQUEST, requirements())
    # Token coverage alone is insufficient to protect an existing good goal.
    assert verify_task_plan(candidate).valid
    result = validate_repaired_plan(original, candidate)
    assert not result.valid
    assert any("lost valid goal content" in error for error in result.errors)


@pytest.mark.parametrize("field,value", [("evidence_needs", ["database transaction boundaries"]), ("depends_on", ["access-review"])])
def test_normalization_keeps_same_coverage_with_distinct_valid_fields(field, value):
    tasks = parse_task_plan_output(repaired_payload(), REQUEST, requirements()).tasks
    other = deepcopy(tasks[0])
    other.task_id = "second-storage-review"
    setattr(other, field, value)
    normalized, removed = normalize_tasks([*tasks, other])
    assert removed == 0
    assert normalized[-1].task_id == other.task_id
    assert getattr(normalized[-1], field) == value
