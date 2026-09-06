import asyncio
import json

from app.core.types import ProviderResult, RunMetrics, Usage
from app.research.decomposer import (
    PLANNER_TEMPERATURE,
    TASK_PLAN_JSON_SCHEMA,
    DecompositionResult,
    TaskItem,
    decompose,
)


class _Provider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def generate(self, *, system, user):
        self.calls.append({"system": system, "user": user})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return ProviderResult(response, Usage(input_tokens=10, output_tokens=5))


class _ThinkAwareProvider(_Provider):
    async def generate(self, *, system, user, think):
        self.calls.append({"system": system, "user": user, "think": think})
        response = self.responses.pop(0)
        return ProviderResult(response, Usage(input_tokens=3, output_tokens=2))


class _StructuredProvider(_Provider):
    async def generate(self, *, system, user, format, temperature):
        self.calls.append(
            {"system": system, "user": user, "format": format, "temperature": temperature}
        )
        response = self.responses.pop(0)
        return ProviderResult(response, Usage(input_tokens=3, output_tokens=2))


def _valid_response():
    return json.dumps(
        {
            "tasks": [
                {
                    "task_id": "T1",
                    "title": "Review authentication",
                    "objective": "Check the stated authentication requirements.",
                    "expected_output": "Authentication findings with references.",
                    "domain": "security",
                    "role_profile": "Security Analyst",
                    "depends_on": [],
                },
                {
                    "task_id": "T2",
                    "title": "Review API boundary",
                    "objective": "Check the API boundary after authentication.",
                    "expected_output": "API boundary findings with references.",
                    "domain": "api_architecture",
                    "role_profile": "API/Architecture Analyst",
                    "depends_on": ["T1"],
                },
            ]
        }
    )


def test_decompose_returns_locked_contract_and_uses_bounded_context():
    provider = _ThinkAwareProvider([_valid_response()])
    metrics = RunMetrics()

    result = asyncio.run(
        decompose(
            provider,
            "Review authentication and the API boundary.",
            "[plan_security] Keep authentication atomic.\n[plan_api] Preserve API dependencies.",
            metrics,
        )
    )

    assert isinstance(result, DecompositionResult)
    assert result.status == "COMPLETE"
    assert result.request == "Review authentication and the API boundary."
    assert result.planning_evidence_ids == ["plan_security", "plan_api"]
    assert [task.task_id for task in result.tasks] == ["T1", "T2"]
    assert isinstance(result.tasks[0], TaskItem)
    assert result.tasks[1].depends_on == ["T1"]
    assert provider.calls[0]["think"] is False
    assert "TASK_DECOMPOSER" in provider.calls[0]["system"]
    assert "Keep authentication atomic." in provider.calls[0]["user"]
    assert metrics.llm_calls == 1


def test_decompose_prompt_preserves_distinct_dependent_obligations():
    provider = _ThinkAwareProvider([_valid_response()])

    result = asyncio.run(
        decompose(
            provider,
            "Review the data model first, then check the query access path.",
            "[plan_database] Keep model and query responsibilities separate.",
            RunMetrics(),
        )
    )

    assert result.status == "COMPLETE"
    prompt = provider.calls[0]["user"]
    assert "PROMPT VERSION: p-lite-decomposer-v2" in prompt
    assert prompt.index("OUTPUT PROTOCOL") < prompt.index("CURRENT REQUEST")
    assert prompt.index("PLANNER RULES") < prompt.index("PLANNING EVIDENCE")
    assert "separate tasks" in prompt
    assert "depends_on" in prompt
    assert "Every task must include every schema field" in prompt


def test_decompose_uses_exact_task_plan_schema_and_zero_temperature_when_supported():
    provider = _StructuredProvider([_valid_response()])

    result = asyncio.run(decompose(provider, "Review auth.", "", RunMetrics()))

    assert result.status == "COMPLETE"
    assert provider.calls[0]["format"] == TASK_PLAN_JSON_SCHEMA
    assert provider.calls[0]["temperature"] == PLANNER_TEMPERATURE == 0.0


def test_decompose_retries_a_collapsed_explicitly_ordered_plan():
    collapsed = json.dumps(
        {
            "tasks": [
                {
                    "task_id": "T1",
                    "title": "Review the model and query",
                    "objective": "Check both obligations together.",
                    "expected_output": "One combined review.",
                    "domain": "database",
                    "role_profile": "reviewer",
                    "depends_on": [],
                }
            ]
        }
    )
    provider = _Provider([collapsed, _valid_response()])

    result = asyncio.run(
        decompose(
            provider,
            "Review the data model first, then check the query access path.",
            "[plan_database] Keep responsibilities separate.",
            RunMetrics(),
        )
    )

    assert result.status == "COMPLETE"
    assert [task.task_id for task in result.tasks] == ["T1", "T2"]
    assert result.tasks[1].depends_on == ["T1"]
    assert len(provider.calls) == 2
    assert "explicitly ordered obligations" in provider.calls[1]["user"]
    assert "preserving every distinct obligation" in provider.calls[1]["user"]


def test_decompose_allows_one_structured_retry_and_counts_usage():
    provider = _Provider(["not json", _valid_response()])
    metrics = RunMetrics()

    result = asyncio.run(decompose(provider, "Review auth.", "", metrics))

    assert result.status == "COMPLETE"
    assert len(result.tasks) == 2
    assert len(provider.calls) == 2
    assert metrics.llm_calls == 2
    assert "corrected JSON object only" in provider.calls[1]["user"]


def test_decompose_rejects_invalid_dependency_after_single_retry():
    invalid = json.dumps(
        {
            "tasks": [
                {
                    "task_id": "T1",
                    "title": "Review",
                    "objective": "Review the request.",
                    "expected_output": "Findings.",
                    "domain": "security",
                    "role_profile": "Security Analyst",
                    "depends_on": ["missing"],
                }
            ]
        }
    )
    provider = _Provider([invalid, invalid])

    result = asyncio.run(decompose(provider, "Review auth.", "[plan_security] guidance", RunMetrics()))

    assert result.status == "FAILED"
    assert result.tasks == []
    assert len(provider.calls) == 2
    assert any("unknown task" in warning for warning in result.warnings)


def test_decompose_rejects_dependency_cycles():
    cyclic = json.dumps(
        {
            "tasks": [
                {
                    "task_id": "T1",
                    "title": "First",
                    "objective": "Review the first obligation.",
                    "expected_output": "First findings.",
                    "domain": "security",
                    "role_profile": "Security Analyst",
                    "depends_on": ["T2"],
                },
                {
                    "task_id": "T2",
                    "title": "Second",
                    "objective": "Review the second obligation.",
                    "expected_output": "Second findings.",
                    "domain": "database",
                    "role_profile": "Database Analyst",
                    "depends_on": ["T1"],
                },
            ]
        }
    )
    provider = _Provider([cyclic, cyclic])

    result = asyncio.run(decompose(provider, "Review both.", "", RunMetrics()))

    assert result.status == "FAILED"
    assert len(provider.calls) == 2
    assert any("cycle" in warning for warning in result.warnings)


def test_decompose_provider_failure_is_safe_and_does_not_retry():
    provider = _Provider([RuntimeError("provider body contains secret-token")])

    result = asyncio.run(decompose(provider, "Review auth.", "", RunMetrics()))

    assert result.status == "FAILED"
    assert len(provider.calls) == 1
    assert "secret-token" not in result.warnings[0]
