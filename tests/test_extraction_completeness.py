import asyncio
import json

import pytest

from app.core.types import ProviderResult
from app.research.decomposer import build_task_plan_prompt
from app.research.obligation_concern_extraction import (
    build_extraction_prompt,
    extract_obligations_and_concerns,
)


class CapturingProvider:
    def __init__(self, payload):
        self.payload = payload
        self.prompt = ""

    async def generate_structured(self, *, system, user, response_schema):
        self.prompt = user
        assert "NEGATIVE / PRESERVATION CONSTRAINTS" in user
        assert "required=true" in user
        assert "Do not add a coverage obligation when it is absent" in user
        schema = response_schema["properties"]["obligations"]["items"]
        assert set(schema["properties"]) == {"obligation_id", "description", "required"}
        return ProviderResult(text=json.dumps(self.payload))


@pytest.mark.parametrize(
    "constraint",
    [
        "Do not omit any required item.",
        "Ensure every identified requirement is represented.",
        "Preserve all required constraints.",
        "Produce output satisfying all required items.",
        "Summarize without omitting required constraints.",
        "The output must not lose any stated requirement.",
    ],
)
def test_explicit_coverage_obligation_is_preserved_without_domain_or_id_rewrite(constraint):
    payload = {
        "obligations": [
            {"obligation_id": "REQ-A", "description": "Analyze architecture design", "required": True},
            {"obligation_id": "REQ-B", "description": "Analyze database design", "required": True},
            {"obligation_id": "REQ-OUTPUT", "description": "Produce a validated plan", "required": True},
            {"obligation_id": "REQ-COVERAGE", "description": constraint, "required": True},
        ],
        "concerns": [
            {"concern_id": "C-API", "description": "Architecture design", "domain": "api_architecture"},
            {"concern_id": "C-DB", "description": "Database design", "domain": "database"},
            {"concern_id": "C-SEC", "description": "Security ownership risk", "domain": "security"},
        ],
    }
    user_request = f"Analyze architecture, database and security ownership. Produce a validated plan. {constraint}"
    provider = CapturingProvider(payload)
    result = asyncio.run(extract_obligations_and_concerns(provider, user_request))
    assert result.to_dict() == payload
    coverage = result.to_dict()["obligations"][-1]
    assert coverage == {"obligation_id": "REQ-COVERAGE", "description": constraint, "required": True}
    assert all("domain" not in item for item in result.to_dict()["obligations"])
    ids = [item.obligation_id for item in result.obligations]
    assert ids == [item["obligation_id"] for item in payload["obligations"]]
    assert len(ids) == len(set(ids))
    handoff = build_task_plan_prompt(user_request, extraction=result)
    assert f"REQ-COVERAGE: {constraint} (required=True)" in handoff
    assert provider.prompt.endswith(user_request)


def test_simple_request_has_no_automatically_appended_coverage_requirement():
    payload = {
        "obligations": [{"obligation_id": "O1", "description": "Review authentication", "required": True}],
        "concerns": [{"concern_id": "C1", "description": "Authentication", "domain": "security"}],
    }
    result = asyncio.run(extract_obligations_and_concerns(CapturingProvider(payload), "Review authentication."))
    assert result.to_dict() == payload


def test_prompt_explicitly_retains_negative_constraints_by_meaning_not_prefix():
    prompt = build_extraction_prompt("Assess database constraints; keep the report complete.")
    assert "NEGATIVE / PRESERVATION CONSTRAINTS" in prompt
    assert "by their meaning, not by a negative prefix alone" in prompt
    assert "conversational filler" in prompt
    assert "every explicit correctness constraint" in prompt
