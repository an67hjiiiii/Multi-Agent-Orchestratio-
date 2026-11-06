import asyncio
import json

import pytest

from app.core.types import ProviderResult, RunMetrics, Usage
from app.research.obligation_concern_extraction import (
    build_extraction_prompt,
    EXTRACTION_PROMPT_VERSION,
    extract_obligations_and_concerns,
    parse_obligation_concern_output,
)


def test_extraction_prompt_separates_atomic_subjects_from_process_instructions():
    request = (
        "Review the uploaded architecture, database and security design. "
        "Identify the important technical obligations and explicit concerns, "
        "determine their domains and dependencies, retrieve supporting planning "
        "evidence, and produce a validated implementation plan. "
        "Do not silently omit any identified requirement."
    )
    prompt = build_extraction_prompt(request)
    assert "independently checkable" in prompt
    assert "not a technical concern" in prompt
    assert "domainless obligations" in prompt
    assert "security, database, api_architecture" in prompt
    assert prompt.endswith(request)
    assert '"domain":"general"' not in prompt


def test_structured_extraction_preserves_distinct_requirements_and_planner_handoff():
    from app.research.decomposer import build_task_plan_prompt
    from app.research.registry import REGISTRY

    payload = {
        "obligations": [
            {"obligation_id": "O1", "description": "Review architecture design", "required": True},
            {"obligation_id": "O2", "description": "Review database design", "required": True},
            {"obligation_id": "O3", "description": "Review security design", "required": True},
            {"obligation_id": "O4", "description": "Determine dependencies", "required": True},
            {"obligation_id": "O5", "description": "Use supporting planning evidence", "required": True},
            {"obligation_id": "O6", "description": "Produce a complete validated implementation plan", "required": True},
        ],
        "concerns": [
            {"concern_id": "C1", "description": "Architecture design", "domain": "api_architecture"},
            {"concern_id": "C2", "description": "Database design", "domain": "database"},
            {"concern_id": "C3", "description": "Security design", "domain": "security"},
        ],
    }

    class CaptureProvider:
        async def generate_structured(self, *, system, user, response_schema):
            assert EXTRACTION_PROMPT_VERSION in system
            concern_schema = response_schema["properties"]["concerns"]["items"]
            assert concern_schema["properties"]["domain"]["enum"] == list(REGISTRY)
            assert "general" not in concern_schema["properties"]["domain"]["enum"]
            assert "REQUEST DOMAINS" in user
            return ProviderResult(text=json.dumps(payload))

        async def generate(self, **kwargs):
            raise AssertionError("Structured provider must not use generic JSON")

    request = "Review architecture, database and security design, dependencies, planning evidence and a validated complete plan."
    extraction = asyncio.run(extract_obligations_and_concerns(CaptureProvider(), request))
    assert extraction.to_dict() == payload
    assert len({item.obligation_id for item in extraction.obligations}) == len(payload["obligations"])
    handoff = build_task_plan_prompt(request, extraction=extraction)
    for item in extraction.obligations:
        assert f"{item.obligation_id}: {item.description}" in handoff
    for item in extraction.concerns:
        assert f"{item.concern_id}: {item.description} (domain={item.domain})" in handoff


@pytest.mark.parametrize(
    "user_request,payload",
    [
        ("Identify obligations and concerns.", {"obligations": [], "concerns": []}),
        ("Review authentication.", {
            "obligations": [{"obligation_id": "O1", "description": "Review authentication", "required": True}],
            "concerns": [{"concern_id": "C1", "description": "Authentication", "domain": "security"}],
        }),
    ],
)
def test_extraction_boundary_does_not_invent_items_or_expand_simple_output(user_request, payload):
    class Provider:
        async def generate_structured(self, **kwargs):
            assert "Do not invent subjects" in kwargs["user"]
            return ProviderResult(text=json.dumps(payload))

    result = asyncio.run(extract_obligations_and_concerns(Provider(), user_request))
    assert result.to_dict() == payload


def test_actual_ollama_extraction_transport_sends_canonical_schema(monkeypatch):
    from app.providers.ollama import OllamaProvider
    from app.research.obligation_concern_extraction import EXTRACTION_RESPONSE_SCHEMA

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

            class Response:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {"message": {"content": '{"obligations":[],"concerns":[]}'}}

            return Response()

    monkeypatch.setattr("app.providers.ollama.httpx.AsyncClient", Client)
    result = asyncio.run(extract_obligations_and_concerns(
        OllamaProvider(model="qwen3:4b"), "Identify obligations and concerns."
    ))
    assert result.concerns == []
    assert len(captured) == 1
    assert captured[0]["format"] == EXTRACTION_RESPONSE_SCHEMA
    assert captured[0]["model"] == "qwen3:4b"
    assert captured[0]["think"] is False


def test_alternative_independent_subjects_are_not_merged_by_extraction_boundary():
    payload = {
        "obligations": [
            {"obligation_id": "TLS-1", "description": "Review certificate expiry", "required": True},
            {"obligation_id": "ERR-1", "description": "Review endpoint error messages", "required": False},
        ],
        "concerns": [
            {"concern_id": "TLS-RISK", "description": "Expired certificates", "domain": "security"},
            {"concern_id": "ERR-RISK", "description": "Endpoint error messages", "domain": "api_architecture"},
        ],
    }

    class Provider:
        async def generate_structured(self, **kwargs):
            return ProviderResult(text=json.dumps(payload))

    result = asyncio.run(extract_obligations_and_concerns(
        Provider(), "Review certificate expiry and, optionally, endpoint error messages."
    ))
    assert result.to_dict() == payload


def test_parser_keeps_obligations_and_concerns_distinct_and_preserves_fields():
    result = parse_obligation_concern_output(
        {
            "obligations": [
                {
                    "obligation_id": "REQ-1",
                    "description": "Preserve the API contract.",
                    "required": False,
                }
            ],
            "concerns": [
                {
                    "concern_id": "CONCERN-1",
                    "description": "Check malformed responses.",
                    "domain": "security",
                }
            ],
        }
    )

    assert [item.obligation_id for item in result.obligations] == ["REQ-1"]
    assert result.obligations[0].required is False
    assert [item.concern_id for item in result.concerns] == ["CONCERN-1"]
    assert result.concerns[0].domain == "security"
    assert result.to_dict() == {
        "obligations": [
            {
                "obligation_id": "REQ-1",
                "description": "Preserve the API contract.",
                "required": False,
            }
        ],
        "concerns": [
            {
                "concern_id": "CONCERN-1",
                "description": "Check malformed responses.",
                "domain": "security",
            }
        ],
    }


def test_parser_applies_existing_contract_defaults_without_inventing_items():
    result = parse_obligation_concern_output(
        json.dumps(
            {
                "obligations": [
                    {"obligation_id": "O1", "description": "Check identity."}
                ],
                "concerns": [],
            }
        )
    )

    assert len(result.obligations) == 1
    assert result.obligations[0].required is True
    assert result.concerns == []


def test_parser_accepts_explicit_empty_arrays():
    result = parse_obligation_concern_output(
        {"obligations": [], "concerns": []}
    )

    assert result.to_dict() == {"obligations": [], "concerns": []}


@pytest.mark.parametrize(
    "payload, message",
    [
        (
            {
                "obligations": [{"description": "Missing ID"}],
                "concerns": [],
            },
            "obligation.obligation_id",
        ),
        (
            {"obligations": [], "concerns": [{"concern_id": "C1"}]},
            "concern.description",
        ),
        (
            {
                "obligations": [
                    {
                        "obligation_id": "O1",
                        "description": "x",
                        "required": "yes",
                    }
                ],
                "concerns": [],
            },
            "obligation.required",
        ),
        (
            {
                "obligations": [],
                "concerns": [
                    {"concern_id": "C1", "description": "x", "domain": 1}
                ],
            },
            "concern.domain",
        ),
    ],
)
def test_parser_rejects_ambiguous_structured_items(payload, message):
    with pytest.raises(ValueError, match=message):
        parse_obligation_concern_output(payload)


@pytest.mark.parametrize(
    "payload, message",
    [
        ({}, "root arrays"),
        ({"obligations": []}, "concerns"),
        ({"concerns": []}, "obligations"),
        ({"obligations": None, "concerns": []}, "obligations must be a list"),
        ({"obligations": [], "concerns": None}, "concerns must be a list"),
        ({"tasks": []}, "unsupported root fields.*tasks"),
        (
            {"obligations": [], "concerns": [], "tasks": []},
            "unsupported root fields.*tasks",
        ),
        (
            {
                "obligations": [
                    {
                        "obligation_id": "O1",
                        "description": "Check identity.",
                        "anchors": ["identity"],
                    }
                ],
                "concerns": [],
            },
            "obligation contains unsupported fields.*anchors",
        ),
    ],
)
def test_parser_fails_closed_for_missing_null_or_unsupported_fields(payload, message):
    with pytest.raises(ValueError, match=message):
        parse_obligation_concern_output(payload)


def test_parser_rejects_prose_around_json_object():
    with pytest.raises(ValueError, match="exactly one JSON object"):
        parse_obligation_concern_output(
            'Explanation: {"obligations": [], "concerns": []} done.'
        )


def test_parser_rejects_unknown_concern_domain_but_preserves_general():
    with pytest.raises(ValueError, match="Unknown task domain: custom-review"):
        parse_obligation_concern_output(
            {
                "obligations": [],
                "concerns": [
                    {"concern_id": "C1", "description": "Review", "domain": "custom-review"}
                ],
            }
        )

    result = parse_obligation_concern_output(
        {
            "obligations": [],
            "concerns": [{"concern_id": "C1", "description": "Review"}],
        }
    )
    assert result.concerns[0].domain == "general"


def test_provider_extraction_returns_only_obligations_and_concerns_and_tracks_usage():
    class StructuredProvider:
        async def generate(self, *, system: str, user: str) -> ProviderResult:
            assert "OBLIGATION_CONCERN_EXTRACTOR" in system
            assert '"obligations"' in user
            assert '"concerns"' in user
            assert '"anchors"' not in user
            return ProviderResult(
                text=json.dumps(
                    {
                        "obligations": [
                            {"obligation_id": "O1", "description": "Review identity."}
                        ],
                        "concerns": [
                            {
                                "concern_id": "C1",
                                "description": "Check access control.",
                                "domain": "security",
                            }
                        ],
                    }
                ),
                usage=Usage(input_tokens=7, output_tokens=5),
            )

    metrics = RunMetrics()
    result = asyncio.run(
        extract_obligations_and_concerns(
            StructuredProvider(), "Review identity and access control.", metrics
        )
    )

    assert [item.obligation_id for item in result.obligations] == ["O1"]
    assert [item.concern_id for item in result.concerns] == ["C1"]
    assert metrics.llm_calls == 1
    assert metrics.input_tokens == 7
    assert metrics.output_tokens == 5
