import asyncio
import json

import pytest

from app.core.types import ProviderResult, RunMetrics, Usage
from app.research.obligation_concern_extraction import (
    extract_obligations_and_concerns,
    parse_obligation_concern_output,
)


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
