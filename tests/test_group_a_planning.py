import asyncio
import json

import pytest

from app.core.types import (
    Concern,
    Obligation,
    ObligationConcernExtraction,
    ProviderResult,
    RunMetrics,
    Usage,
)
from app.research.decomposer import (
    DecompositionResult,
    PlanningResult,
    build_task_plan_prompt,
    decompose_plan,
    detect_domains,
    parse_task_plan_output,
    understand_request,
)


def _valid_plan() -> str:
    return json.dumps(
        {
            "tasks": [
                {
                    "task_id": "T1",
                    "goal": "Review authentication.",
                    "domain": "security",
                    "depends_on": [],
                    "evidence_needs": ["authentication"],
                },
                {
                    "task_id": "T2",
                    "goal": "Review the API boundary.",
                    "domain": "api_architecture",
                    "depends_on": ["T1"],
                    "evidence_needs": ["endpoint"],
                },
            ]
        }
    )


def test_request_understanding_normalizes_text_and_detects_only_named_domains():
    understanding = understand_request("  Review auth, the schema, and an API endpoint. ")

    assert understanding.normalized_request == "Review auth, the schema, and an API endpoint."
    assert list(understanding.domains) == [
        "security",
        "database",
        "api_architecture",
    ]
    assert detect_domains("Explain the request") == []


def test_task_plan_parser_preserves_obligations_concerns_and_dependencies():
    extraction = ObligationConcernExtraction(
        obligations=[Obligation("O1", "Keep authentication separate.")],
        concerns=[Concern("C1", "Check the API boundary.", "api_architecture")],
    )

    plan = parse_task_plan_output(
        _valid_plan(),
        request="Review auth then the API boundary.",
        extraction=extraction,
    )

    assert plan.request == "Review auth then the API boundary."
    assert plan.obligations == extraction.obligations
    assert plan.concerns == extraction.concerns
    assert [task.task_id for task in plan.tasks] == ["T1", "T2"]
    assert plan.tasks[1].depends_on == ["T1"]


@pytest.mark.parametrize(
    "payload, message",
    [
        ({}, "tasks list"),
        ({"tasks": None}, "tasks must be a list"),
        ({"tasks": []}, "at least one task"),
        ({"tasks": [], "verification": []}, "unsupported root fields"),
        (
            {
                "tasks": [
                    {
                        "task_id": "T1",
                        "goal": "Review auth.",
                        "domain": "security",
                        "unexpected": True,
                    }
                ]
            },
            "unsupported fields",
        ),
        (
            {
                "tasks": [
                    {
                        "task_id": "T1",
                        "goal": "Review auth.",
                        "domain": "security",
                        "evidence_needs": [],
                    }
                ]
            },
            "must include depends_on",
        ),
        (
            {
                "tasks": [
                    {
                        "task_id": "T1",
                        "goal": "Review auth.",
                        "domain": "security",
                        "depends_on": [],
                    }
                ]
            },
            "must include evidence_needs",
        ),
    ],
)
def test_task_plan_parser_rejects_invalid_structured_output(payload, message):
    with pytest.raises(ValueError, match=message):
        parse_task_plan_output(payload)


def test_task_plan_parser_rejects_unknown_dependencies_and_cycles():
    unknown = json.loads(_valid_plan())
    unknown["tasks"][1]["depends_on"] = ["missing"]
    with pytest.raises(ValueError, match="(?i)unknown dependency"):
        parse_task_plan_output(unknown)

    cyclic = json.loads(_valid_plan())
    cyclic["tasks"][0]["depends_on"] = ["T2"]
    with pytest.raises(ValueError, match="cycle"):
        parse_task_plan_output(cyclic)


def test_task_plan_prompt_keeps_group_a_inputs_and_excludes_later_stages():
    extraction = ObligationConcernExtraction(
        obligations=[Obligation("O1", "Review authentication.")],
        concerns=[Concern("C1", "Check the API response.", "api_architecture")],
    )

    prompt = build_task_plan_prompt(
        "Review authentication and the API response.",
        "[planning-api] Keep the API contract explicit.",
        extraction,
    )

    assert "O1: Review authentication." in prompt
    assert "C1: Check the API response." in prompt
    assert "depends_on" in prompt
    assert "Plan Verification" not in prompt
    assert "worker" in prompt
    assert "dispatch" in prompt


def test_decompose_plan_performs_at_most_one_bounded_repair_and_tracks_usage():
    class RepairingProvider:
        def __init__(self):
            self.calls = []

        async def generate(self, *, system: str, user: str) -> ProviderResult:
            self.calls.append((system, user))
            if len(self.calls) == 1:
                return ProviderResult("not json", Usage(input_tokens=3, output_tokens=2))
            return ProviderResult(_valid_plan(), Usage(input_tokens=5, output_tokens=4))

    provider = RepairingProvider()
    metrics = RunMetrics()
    result = asyncio.run(
        decompose_plan(provider, "Review auth then the API boundary.", metrics=metrics)
    )

    assert isinstance(result, PlanningResult)
    assert isinstance(result, DecompositionResult)
    assert result.status == "COMPLETE"
    assert result.repair_attempted is True
    assert result.tasks[1].depends_on == ["T1"]
    assert len(provider.calls) == 2
    assert "PREVIOUS INVALID TASK PLAN" in provider.calls[1][1]
    assert metrics.llm_calls == 2
    assert metrics.input_tokens == 8
    assert metrics.output_tokens == 6


def test_decompose_plan_handles_provider_failure_without_retry_or_raw_secret():
    class FailingProvider:
        def __init__(self):
            self.calls = 0

        async def generate(self, *, system: str, user: str) -> ProviderResult:
            self.calls += 1
            raise RuntimeError("provider secret-token=do-not-leak")

    provider = FailingProvider()
    result = asyncio.run(decompose_plan(provider, "Review auth."))

    assert result.status == "FAILED"
    assert result.plan is None
    assert result.repair_attempted is False
    assert provider.calls == 1
    assert "do-not-leak" not in result.warnings[0]
