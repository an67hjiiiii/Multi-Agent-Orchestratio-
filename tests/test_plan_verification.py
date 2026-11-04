import pytest

from app.core.types import Concern, Obligation, Task, TaskPlan
from app.research.plan_verification import (
    TaskPlanValidationError,
    decide_repair,
    validate_repaired_plan,
    validate_task_plan,
    verify_task_plan,
)


def make_plan(*, task_domain="security", concern_domain="general", goal="Review identity"):
    return TaskPlan(
        request="Review identity and authorization.",
        obligations=[Obligation("O1", "Review identity.")],
        concerns=[Concern("C1", "Check authorization.", concern_domain)],
        tasks=[Task("T1", goal, task_domain)],
    )


def test_valid_plan_covers_obligation_and_general_concern():
    plan = make_plan(goal="Review identity and authorization")

    result = verify_task_plan(plan)

    assert result.valid is True
    assert result.covered_obligations == ("O1",)
    assert result.covered_concerns == ("C1",)
    assert decide_repair(result).action == "ACCEPT"


def test_generic_extractor_prefix_does_not_hide_covered_api_concern():
    plan = TaskPlan(
        request="Review API request validation and error responses.",
        obligations=[
            Obligation("O1", "Review API request validation and error responses")
        ],
        concerns=[
            Concern(
                "C1",
                "General concern about API request validation and error responses",
                "general",
            )
        ],
        tasks=[
            Task(
                "T1",
                "Review API request validation and error responses",
                "api_architecture",
            )
        ],
    )

    result = verify_task_plan(plan)

    assert result.valid is True
    assert result.covered_obligations == ("O1",)
    assert result.covered_concerns == ("C1",)
    assert result.missing_concerns == ()


def test_one_shared_term_does_not_cover_multi_term_obligation_or_concern():
    plan = TaskPlan(
        request="Review identity and authorization.",
        obligations=[Obligation("O1", "Review identity and authorization.")],
        concerns=[Concern("C1", "Check authorization and sessions.", "security")],
        tasks=[Task("T1", "Review identity and authorization sessions", "security")],
    )

    result = verify_task_plan(plan)
    assert result.valid is True

    partial = TaskPlan(
        request=plan.request,
        obligations=plan.obligations,
        concerns=plan.concerns,
        tasks=[Task("T1", "Review authorization", "security")],
    )
    result = verify_task_plan(partial)
    assert result.valid is False
    assert result.missing_required_obligations == ("O1",)
    assert result.missing_concerns == ("C1",)


def test_partial_term_overlap_does_not_cover_longer_obligation():
    plan = TaskPlan(
        request="Review identity, authorization, and transaction boundaries.",
        obligations=[
            Obligation(
                "O1",
                "Review identity, authorization, transaction, and boundary requirements.",
            )
        ],
        tasks=[Task("T1", "Review identity and authorization", "security")],
    )

    result = verify_task_plan(plan)

    assert result.valid is False
    assert result.missing_required_obligations == ("O1",)


def test_missing_required_coverage_requests_one_repair_then_rejects():
    plan = make_plan(goal="Review unrelated deployment")

    result = verify_task_plan(plan)

    assert result.valid is False
    assert result.missing_required_obligations == ("O1",)
    assert result.missing_concerns == ("C1",)
    assert decide_repair(result).action == "REPAIR"
    assert decide_repair(result, repair_attempted=True).action == "REJECT"


def test_empty_task_plan_is_invalid():
    plan = TaskPlan(request="Review identity.", obligations=[], concerns=[], tasks=[])

    result = verify_task_plan(plan)

    assert result.valid is False
    assert any("at least one task" in error for error in result.errors)


def test_specific_concern_requires_a_matching_task_domain():
    plan = make_plan(concern_domain="security", goal="Review authorization")
    plan.tasks[0].domain = "database"

    result = verify_task_plan(plan)

    assert result.valid is False
    assert result.misrouted_concerns == ("C1",)


def test_explicit_coverage_mapping_is_checked_against_task_and_obligation_ids():
    plan = make_plan(goal="Review identity and authorization")

    result = verify_task_plan(plan, coverage={"T1": ["O1"]})

    assert result.valid is True
    assert result.covered_obligations == ("O1",)

    unknown = verify_task_plan(plan, coverage={"T9": ["O1"]})
    assert unknown.valid is False
    assert any("unknown task T9" in error for error in unknown.errors)


@pytest.mark.parametrize(
    "plan, message",
    [
        (make_plan(task_domain="billing", goal="Review identity and authorization"), "Unknown task domain"),
        (
            TaskPlan(
                request="Review identity.",
                obligations=[Obligation("O1", "Review identity.")],
                tasks=[Task("T1", "Review identity", "security", ["missing"])],
            ),
            "Unknown dependency",
        ),
        (
            TaskPlan(
                request="Review identity.",
                obligations=[Obligation("O1", "Review identity.")],
                tasks=[
                    Task("T1", "Review identity", "security", ["T2"]),
                    Task("T2", "Review identity", "security", ["T1"]),
                ],
            ),
            "cycle",
        ),
    ],
)
def test_task_plan_reuses_existing_domain_and_dependency_validation(plan, message):
    with pytest.raises(TaskPlanValidationError, match=message):
        validate_task_plan(plan)


def test_repair_must_preserve_request_obligations_and_concerns_and_revalidate():
    original = make_plan(goal="Review unrelated deployment")
    repaired = make_plan(goal="Review identity and authorization")

    result = validate_repaired_plan(original, repaired)

    assert result.valid is True

    dropped_requirement = TaskPlan(
        request=original.request,
        obligations=[],
        concerns=original.concerns,
        tasks=repaired.tasks,
    )
    result = validate_repaired_plan(original, dropped_requirement)
    assert result.valid is False
    assert "repair changed the obligations" in result.errors

    changed_concern = TaskPlan(
        request=original.request,
        obligations=original.obligations,
        concerns=[Concern("C1", "Check a different concern.", "general")],
        tasks=repaired.tasks,
    )
    result = validate_repaired_plan(original, changed_concern)
    assert result.valid is False
    assert "repair changed the concerns" in result.errors

    changed_request = TaskPlan(
        request="A different request.",
        obligations=original.obligations,
        concerns=original.concerns,
        tasks=repaired.tasks,
    )
    result = validate_repaired_plan(original, changed_request)
    assert result.valid is False
    assert "repair changed the request" in result.errors


def test_post_repair_validation_does_not_trust_invalid_repaired_plan():
    original = make_plan(goal="Review unrelated deployment")
    repaired = make_plan(goal="Review identity and authorization", task_domain="billing")

    result = validate_repaired_plan(original, repaired)

    assert result.valid is False
    assert any("Unknown task domain" in error for error in result.errors)
