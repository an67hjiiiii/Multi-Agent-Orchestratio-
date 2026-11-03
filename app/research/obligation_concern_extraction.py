from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from app.research.registry import validate_domain

from app.core.types import (
    Concern,
    Obligation,
    ObligationConcernExtraction,
    RunMetrics,
)


EXTRACTION_SYSTEM_PROMPT = (
    "OBLIGATION_CONCERN_EXTRACTOR. Return exactly one JSON object containing "
    "obligations and concerns. Preserve the request's explicit distinctions; "
    "do not invent requirements, return tasks, or add unsupported fields."
)
EXTRACTION_SCHEMA = (
    '{"obligations":[{"obligation_id":"O1","description":"...",'
    '"required":true}],'
    '"concerns":[{"concern_id":"C1","description":"...",'
    '"domain":"general"}]}'
)
_ROOT_FIELDS = frozenset({"obligations", "concerns"})
_OBLIGATION_FIELDS = frozenset({"obligation_id", "description", "required"})
_CONCERN_FIELDS = frozenset({"concern_id", "description", "domain"})


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
        "- Preserve any supplied IDs, required values, and non-empty domains.\n"
        "- Use empty arrays when the request contains no item of that kind.\n"
        "- Use only the two root arrays and their schema fields; return no task, "
        "dependency, verification, repair, or answer fields.\n"
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
        raise ValueError("extractor output must be exactly one JSON object") from None

    if not isinstance(decoded, Mapping):
        raise ValueError("extractor output must be a JSON object")
    return decoded


def _validate_envelope(payload: Mapping[str, Any]) -> None:
    unsupported = [str(key) for key in payload if key not in _ROOT_FIELDS]
    if unsupported:
        raise ValueError(
            "extractor output contains unsupported root fields: "
            + ", ".join(sorted(unsupported))
        )
    missing = [key for key in _ROOT_FIELDS if key not in payload]
    if missing:
        raise ValueError(
            "extractor output must contain root arrays: " + ", ".join(sorted(missing))
        )


def _as_text(value: Any, field_name: str, item_kind: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{item_kind}.{field_name} must be a non-empty string")
    return value


def _validate_record_fields(
    record: Mapping[str, Any], allowed: frozenset[str], item_kind: str
) -> None:
    unsupported = [str(key) for key in record if key not in allowed]
    if unsupported:
        raise ValueError(
            f"{item_kind} contains unsupported fields: "
            + ", ".join(sorted(unsupported))
        )


def _records(payload: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    if key not in payload:
        raise ValueError(f"{key} must be present as a list")
    raw = payload[key]
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

    The parser is deliberately strict about the envelope and item fields.
    Optional fields keep the existing Sprint 1 defaults (`required=True` and
    `domain="general"`).
    """

    obj = _decode_payload(payload)
    _validate_envelope(obj)
    obligations: list[Obligation] = []
    obligation_ids: set[str] = set()
    for record in _records(obj, "obligations"):
        _validate_record_fields(record, _OBLIGATION_FIELDS, "obligation")
        identifier = _as_text(record.get("obligation_id"), "obligation_id", "obligation")
        if identifier in obligation_ids:
            raise ValueError(f"duplicate obligation_id: {identifier}")
        obligation_ids.add(identifier)
        description = _as_text(record.get("description"), "description", "obligation")
        required = record.get("required", True)
        if not isinstance(required, bool):
            raise ValueError("obligation.required must be a boolean")
        item = Obligation(identifier, description, required)
        obligations.append(item)

    concerns: list[Concern] = []
    concern_ids: set[str] = set()
    for record in _records(obj, "concerns"):
        _validate_record_fields(record, _CONCERN_FIELDS, "concern")
        identifier = _as_text(record.get("concern_id"), "concern_id", "concern")
        if identifier in concern_ids:
            raise ValueError(f"duplicate concern_id: {identifier}")
        concern_ids.add(identifier)
        description = _as_text(record.get("description"), "description", "concern")
        domain = record.get("domain", "general")
        if not isinstance(domain, str) or not domain.strip():
            raise ValueError("concern.domain must be a non-empty string")
        if domain != "general":
            try:
                validate_domain(domain)
            except ValueError as exc:
                raise ValueError(f"concern.domain: {exc}") from exc
        item = Concern(identifier, description, domain)
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
