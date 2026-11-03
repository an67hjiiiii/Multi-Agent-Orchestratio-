from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.core.types import (
    Concern,
    Obligation,
    ObligationConcernExtraction,
    RunMetrics,
)


EXTRACTION_SYSTEM_PROMPT = (
    "OBLIGATION_CONCERN_EXTRACTOR. Return exactly one JSON object containing "
    "obligations and concerns. Preserve the request's explicit distinctions; "
    "do not invent requirements or return tasks."
)
EXTRACTION_SCHEMA = (
    '{"obligations":[{"obligation_id":"O1","description":"...",'
    '"required":true,"anchors":["..."]}],'
    '"concerns":[{"concern_id":"C1","description":"...",'
    '"domain":"security|database|api_architecture|general",'
    '"anchors":["..."]}]}'
)
_JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def build_extraction_prompt(request: str) -> str:
    """Build the bounded request-understanding prompt for this extraction step."""

    if not isinstance(request, str) or not request.strip():
        raise ValueError("request must be a non-empty string")
    return (
        "CURRENT REQUEST:\n"
        f"{request}\n\n"
        f"Schema: {EXTRACTION_SCHEMA}\n\n"
        "Rules:\n"
        "- Derive both arrays only from the current request.\n"
        "- Keep a required obligation separate from an explicit review concern.\n"
        "- Preserve any supplied IDs, required values, domains, and anchors.\n"
        "- Use empty arrays when the request contains no item of that kind.\n"
        "- Return no task, dependency, verification, repair, or answer fields.\n"
        "Return JSON only."
    )


def _decode_payload(payload: Mapping[str, Any] | str) -> Mapping[str, Any]:
    if isinstance(payload, Mapping):
        return payload
    if not isinstance(payload, str) or not payload.strip():
        raise ValueError("extractor output must be a JSON object")

    text = payload.strip()
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_OBJECT_PATTERN.search(text)
        if not match:
            raise ValueError("extractor output must be a JSON object") from None
        try:
            decoded = json.loads(match.group(0))
        except json.JSONDecodeError:
            raise ValueError("extractor output must be a JSON object") from None

    if not isinstance(decoded, Mapping):
        raise ValueError("extractor output must be a JSON object")
    return decoded


def _as_text(value: Any, field_name: str, item_kind: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{item_kind}.{field_name} must be a non-empty string")
    return value


def _as_anchors(record: Mapping[str, Any], item_kind: str) -> list[str]:
    """Normalize already-present plural or scalar anchor forms without inventing one."""

    raw: Any = None
    for key in ("anchors", "source_anchors", "source_anchor", "anchor"):
        if key in record:
            raw = record[key]
            break
    if raw is None:
        return []
    if isinstance(raw, str):
        return [_as_text(raw, "anchors", item_kind)]
    if not isinstance(raw, Sequence) or isinstance(raw, (bytes, bytearray)):
        raise ValueError(f"{item_kind}.anchors must be a string or list of strings")

    anchors: list[str] = []
    for index, value in enumerate(raw):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"{item_kind}.anchors[{index}] must be a non-empty string"
            )
        anchors.append(value)
    return anchors


def _records(payload: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    raw = payload.get(key, [])
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"{key} must be a list")
    records: list[Mapping[str, Any]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ValueError(f"{key}[{index}] must be an object")
        records.append(item)
    return records


def parse_obligation_concern_output(
    payload: Mapping[str, Any] | str,
) -> ObligationConcernExtraction:
    """Parse structured obligations and concerns without creating task plans.

    The parser is deliberately strict about identity and text fields. Optional
    fields keep the existing Sprint 1 defaults (`required=True` and
    `domain="general"`), while anchors are retained only when present in the
    structured output.
    """

    obj = _decode_payload(payload)
    obligations: list[Obligation] = []
    obligation_ids: set[str] = set()
    for record in _records(obj, "obligations"):
        identifier = _as_text(record.get("obligation_id"), "obligation_id", "obligation")
        if identifier in obligation_ids:
            raise ValueError(f"duplicate obligation_id: {identifier}")
        obligation_ids.add(identifier)
        description = _as_text(record.get("description"), "description", "obligation")
        required = record.get("required", True)
        if not isinstance(required, bool):
            raise ValueError("obligation.required must be a boolean")
        item = Obligation(identifier, description, required)
        item.anchors = _as_anchors(record, "obligation")
        obligations.append(item)

    concerns: list[Concern] = []
    concern_ids: set[str] = set()
    for record in _records(obj, "concerns"):
        identifier = _as_text(record.get("concern_id"), "concern_id", "concern")
        if identifier in concern_ids:
            raise ValueError(f"duplicate concern_id: {identifier}")
        concern_ids.add(identifier)
        description = _as_text(record.get("description"), "description", "concern")
        domain = record.get("domain", "general")
        if not isinstance(domain, str) or not domain.strip():
            raise ValueError("concern.domain must be a non-empty string")
        item = Concern(identifier, description, domain)
        item.anchors = _as_anchors(record, "concern")
        concerns.append(item)

    return ObligationConcernExtraction(obligations=obligations, concerns=concerns)


async def extract_obligations_and_concerns(
    provider: Any,
    request: str,
    metrics: RunMetrics | None = None,
) -> ObligationConcernExtraction:
    """Ask the configured provider for obligations/concerns only."""

    prompt = build_extraction_prompt(request)
    result = await provider.generate(system=EXTRACTION_SYSTEM_PROMPT, user=prompt)
    if metrics is not None:
        metrics.add_usage(result.usage)
    return parse_obligation_concern_output(result.text)


# Singular/plural aliases make the narrow extraction seam discoverable without
# coupling it to the later TaskPlan decomposition API.
parse_obligation_concerns = parse_obligation_concern_output
extract_obligation_concerns = extract_obligations_and_concerns


__all__ = [
    "EXTRACTION_SCHEMA",
    "EXTRACTION_SYSTEM_PROMPT",
    "build_extraction_prompt",
    "extract_obligation_concerns",
    "extract_obligations_and_concerns",
    "parse_obligation_concern_output",
    "parse_obligation_concerns",
]
