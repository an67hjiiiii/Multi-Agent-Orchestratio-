import asyncio
import json

import pytest

from app.core.types import ProviderResult, RunMetrics, Usage
from app.research.decomposer import _extract_json, decompose


def test_planner_parser_accepts_json_and_fenced_json_object():
    expected = {"tasks": [{"id": "T1", "goal": "Review authentication"}]}

    assert _extract_json(json.dumps(expected)) == expected
    assert _extract_json(f"```json\n{json.dumps(expected)}\n```") == expected


def test_planner_parser_rejects_text_without_json_object():
    with pytest.raises(ValueError, match="Planner did not return JSON"):
        _extract_json("The plan is to review authentication.")


def test_decompose_maps_task_ids_and_dependencies_without_rewriting_them():
    class StructuredProvider:
        async def generate(self, *, system: str, user: str) -> ProviderResult:
            assert "Return JSON only" in system
            assert "USER REQUEST:" in user
            return ProviderResult(
                text=json.dumps(
                    {
                        "tasks": [
                            {"id": "T1", "goal": "Identify the user", "domain": "security"},
                            {
                                "id": "T2",
                                "goal": "Check permissions",
                                "domain": "security",
                                "depends_on": ["T1"],
                                "evidence_needs": ["authorization"],
                            },
                        ]
                    }
                ),
                usage=Usage(input_tokens=12, output_tokens=9),
            )

    tasks = asyncio.run(
        decompose(StructuredProvider(), "Review user security", "", RunMetrics())
    )

    assert [task.task_id for task in tasks] == ["T1", "T2"]
    assert tasks[1].depends_on == ["T1"]
    assert tasks[1].evidence_needs == ["authorization"]
