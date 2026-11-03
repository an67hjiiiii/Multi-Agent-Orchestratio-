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
                    "anchors": ["API contract"],
                }
            ],
            "concerns": [
                {
                    "concern_id": "CONCERN-1",
                    "description": "Check malformed responses.",
                    "domain": "api_architecture",
                    "source_anchor": "malformed responses",
                }
            ],
        }
    )

    assert [item.obligation_id for item in result.obligations] == ["REQ-1"]
    assert result.obligations[0].required is False
    assert result.obligations[0].anchors == ["API contract"]
    assert [item.concern_id for item in result.concerns] == ["CONCERN-1"]
    assert result.concerns[0].domain == "api_architecture"
    assert result.concerns[0].source_anchor == "malformed responses"
    assert result.to_dict()["obligations"][0]["anchors"] == ["API contract"]
    assert "tasks" not in result.to_dict()


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
    assert result.obligations[0].anchors == []
    assert result.concerns == []


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"obligations": [{"description": "Missing ID"}]}, "obligation.obligation_id"),
        ({"concerns": [{"concern_id": "C1"}]}, "concern.description"),
        (
            {"obligations": [{"obligation_id": "O1", "description": "x", "required": "yes"}]},
            "obligation.required",
        ),
        (
            {"concerns": [{"concern_id": "C1", "description": "x", "domain": 1}]},
            "concern.domain",
        ),
    ],
)
def test_parser_rejects_ambiguous_structured_items(payload, message):
    with pytest.raises(ValueError, match=message):
        parse_obligation_concern_output(payload)


def test_provider_extraction_returns_only_obligations_and_concerns_and_tracks_usage():
    class StructuredProvider:
        async def generate(self, *, system: str, user: str) -> ProviderResult:
            assert "OBLIGATION_CONCERN_EXTRACTOR" in system
            assert '"obligations"' in user
            assert '"concerns"' in user
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
