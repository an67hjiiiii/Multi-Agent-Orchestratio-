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
    assert "PROMPT VERSION: p-lite-decomposer-v5" in prompt
    assert prompt.index("OUTPUT PROTOCOL") < prompt.index("CURRENT REQUEST")
    assert prompt.index("PLANNER RULES") < prompt.index("PLANNING EVIDENCE")
    assert "separate tasks" in prompt
    assert "depends_on" in prompt
    assert "Every task must include every schema field" in prompt
    assert "sole source of obligations" in prompt
    assert "canonical domain IDs" in prompt
    assert "shared-evidence wording does not create a dependency" in prompt
    assert "request naming multiple domains" in prompt
    assert "planning categories as extra tasks" in prompt


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


def test_decompose_retries_noncanonical_domain_to_canonical_contract():
    invalid = json.loads(_valid_response())
    invalid["tasks"][0]["domain"] = "Security"
    provider = _Provider([json.dumps(invalid), _valid_response()])

    result = asyncio.run(
        decompose(
            provider,
            "Review authentication and the API boundary.",
            "",
            RunMetrics(),
        )
    )

    assert result.status == "COMPLETE"
    assert result.tasks[0].domain == "security"
    assert len(provider.calls) == 2
    assert "canonical task domains" in provider.calls[1]["user"]


def test_decompose_rejects_dependency_for_repeated_obligation_without_order():
    repeated = json.loads(_valid_response())
    repeated["tasks"][0].update(
        title="Review authentication evidence",
        objective="Review the authentication evidence.",
        expected_output="Authentication evidence findings.",
        domain="security",
        role_profile="Security Analyst",
        depends_on=[],
    )
    repeated["tasks"][1].update(
        title="Repeat the authorization evidence check",
        objective="Repeat the authorization evidence check.",
        expected_output="Authorization evidence findings.",
        domain="security",
        role_profile="Security Analyst",
        depends_on=["T1"],
    )
    provider = _Provider([json.dumps(repeated), json.dumps(repeated)])

    result = asyncio.run(
        decompose(
            provider,
            "Review authentication evidence and repeat the authorization evidence check.",
            "[plan_security] Keep distinct security obligations atomic.",
            RunMetrics(),
        )
    )

    assert result.status == "FAILED"
    assert len(provider.calls) == 2
    assert any("repeated or shared-evidence" in warning for warning in result.warnings)


def test_decompose_repairs_category_expansion_and_preserves_named_domains():
    overexpanded = json.dumps(
        {
            "tasks": [
                {
                    "task_id": "T1",
                    "title": "Review schema",
                    "objective": "Identify schema and data model requirements for the database.",
                    "expected_output": "Schema findings.",
                    "domain": "database",
                    "role_profile": "Database Analyst",
                    "depends_on": [],
                },
                {
                    "task_id": "T2",
                    "title": "Review query access",
                    "objective": "Identify query and access requirements for the database.",
                    "expected_output": "Query findings.",
                    "domain": "database",
                    "role_profile": "Database Analyst",
                    "depends_on": [],
                },
                {
                    "task_id": "T3",
                    "title": "Review transactions",
                    "objective": "Identify transaction and consistency requirements for the database.",
                    "expected_output": "Transaction findings.",
                    "domain": "database",
                    "role_profile": "Database Analyst",
                    "depends_on": [],
                },
                {
                    "task_id": "T4",
                    "title": "Review performance",
                    "objective": "Identify performance requirements for the database.",
                    "expected_output": "Performance findings.",
                    "domain": "database",
                    "role_profile": "Database Analyst",
                    "depends_on": [],
                },
            ]
        }
    )
    repaired = json.dumps(
        {
            "tasks": [
                {
                    "task_id": "T1",
                    "title": "Review authentication",
                    "objective": "Review the requested authentication requirements.",
                    "expected_output": "Authentication findings.",
                    "domain": "security",
                    "role_profile": "Security Analyst",
                    "depends_on": [],
                },
                {
                    "task_id": "T2",
                    "title": "Review database indexes",
                    "objective": "Review the requested database index requirements.",
                    "expected_output": "Database index findings.",
                    "domain": "database",
                    "role_profile": "Database Analyst",
                    "depends_on": [],
                },
            ]
        }
    )
    provider = _Provider([overexpanded, repaired])

    result = asyncio.run(
        decompose(
            provider,
            "Assess login authentication and database index concerns.",
            "[plan_database] Keep database guidance bounded to the request.",
            RunMetrics(),
        )
    )

    assert result.status == "COMPLETE"
    assert len(provider.calls) == 2
    assert [task.domain for task in result.tasks] == ["security", "database"]
    assert "authentication" in result.tasks[0].objective
    assert "index" in result.tasks[1].objective
    assert "request obligation" in provider.calls[1]["user"]


def test_decompose_accepts_single_canonical_domain_with_paraphrased_anchor():
    response = json.dumps(
        {
            "tasks": [
                {
                    "task_id": "T1",
                    "title": "Review access controls",
                    "objective": "Review access controls for the service.",
                    "expected_output": "Access-control findings.",
                    "domain": "security",
                    "role_profile": "Security Analyst",
                    "depends_on": [],
                },
                {
                    "task_id": "T2",
                    "title": "Review database queries",
                    "objective": "Review database query concerns.",
                    "expected_output": "Database-query findings.",
                    "domain": "database",
                    "role_profile": "Database Analyst",
                    "depends_on": [],
                },
            ]
        }
    )
    provider = _Provider([response])

    result = asyncio.run(
        decompose(
            provider,
            "Review JWT security and database query concerns.",
            "",
            RunMetrics(),
        )
    )

    assert result.status == "COMPLETE"
    assert len(provider.calls) == 1
    assert [task.domain for task in result.tasks] == ["security", "database"]


def test_decompose_provider_failure_is_safe_and_does_not_retry():
    provider = _Provider([RuntimeError("provider body contains secret-token")])

    result = asyncio.run(decompose(provider, "Review auth.", "", RunMetrics()))

    assert result.status == "FAILED"
    assert len(provider.calls) == 1
    assert "secret-token" not in result.warnings[0]
