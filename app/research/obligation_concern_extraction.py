from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from app.research.registry import REGISTRY, validate_domain
from app.research.decomposer import detect_domains
from app.core.structured_output import decode_structured_json

from app.core.types import (
    Concern,
    Obligation,
    ObligationConcernExtraction,
    RunMetrics,
)


EXTRACTION_PROMPT_VERSION = "extract-v4-explicit-preservation-constraints"
EXTRACTION_SYSTEM_PROMPT = (
    "OBLIGATION_CONCERN_EXTRACTOR. Return exactly one JSON object containing "
    f"obligations and concerns. Contract={EXTRACTION_PROMPT_VERSION}. "
    "Extract independently checkable requirements, not a summary of the request. "
    "Separate technical subjects from process and output instructions; "
    "do not invent requirements, return tasks, or add unsupported fields."
)
EXTRACTION_SCHEMA = (
    '{"obligations":[{"obligation_id":"O1","description":"...",'
    '"required":true}],'
    '"concerns":[{"concern_id":"C1","description":"...",'
    f'"domain":"{"|".join(REGISTRY)}"}}]}}'
)
EXTRACTION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "obligations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "obligation_id": {"type": "string", "minLength": 1},
                    "description": {"type": "string", "minLength": 1},
                    "required": {"type": "boolean"},
                },
                "required": ["obligation_id", "description", "required"],
                "additionalProperties": False,
            },
        },
        "concerns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "concern_id": {"type": "string", "minLength": 1},
                    "description": {"type": "string", "minLength": 1},
                    "domain": {"type": "string", "enum": list(REGISTRY)},
                },
                "required": ["concern_id", "description", "domain"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["obligations", "concerns"],
    "additionalProperties": False,
}
_ROOT_FIELDS = frozenset({"obligations", "concerns"})
_OBLIGATION_FIELDS = frozenset({"obligation_id", "description", "required"})
_CONCERN_FIELDS = frozenset({"concern_id", "description", "domain"})


def build_extraction_prompt(request: str) -> str:
    """Build the bounded request-understanding prompt for this extraction step."""

    if not isinstance(request, str) or not request.strip():
        raise ValueError("request must be a non-empty string")
    request_domains = detect_domains(request)
    domain_guidance = "\n".join(
        f"- {domain}: {REGISTRY[domain]['scope']}; "
        f"subjects: {', '.join(REGISTRY[domain]['capabilities'])}"
        for domain in request_domains
    ) or "none"
    return (
        "OUTPUT PROTOCOL:\n"
        f"Schema: {EXTRACTION_SCHEMA}\n\n"
        "Rules:\n"
        "- Derive both arrays only from the current request.\n"
        "- Preserve each independently checkable requested action or output as a "
        "distinct obligation with its full technical subject. A coordinated list "
        "of independent review subjects is not one summary obligation.\n"
        "- Technical concerns describe the actual subjects/risks to examine, "
        "with canonical domains where applicable. Domain hints identify scope, "
        "not additional requirements. Do not invent subjects, ownership rules, "
        "risks or technical details merely because a domain is mentioned.\n"
        "- An instruction to identify obligations and concerns is not a technical "
        "concern. Do not emit meta-concerns about identifying concerns.\n"
        "- Keep explicitly requested dependency reasoning, supporting evidence, "
        "validation and completeness as separate domainless obligations when "
        "they are independently checkable process/output requirements. Do not "
        "assign them a made-up technical concern domain or omit them.\n"
        "NEGATIVE / PRESERVATION CONSTRAINTS:\n"
        "- Explicit prohibitions and preservation/completeness invariants are "
        "requirements too, not merely commentary about the process. Preserve "
        "them by their meaning, not by a negative prefix alone.\n"
        "- When an explicit constraint governs correctness or coverage of the "
        "output, retain it as a distinct domainless obligation with required=true. "
        "Keep its quantifier, subject and prohibitive/preservation meaning; do "
        "not replace it with a weaker positive action or technical Concern.\n"
        "- For example, requesting a comparison plus 'retain every stated "
        "limitation' requires both the comparison and retention obligation. "
        "A request to validate output does not subsume a separate no-omission "
        "constraint. Preserve both when both are explicitly requested.\n"
        "- Distinguish meaningful constraints from conversational filler, "
        "irrelevant negatives and examples not asserted as requirements. "
        "Do not add a coverage obligation when it is absent from the request.\n"
        "- For example, reviewing endpoint errors and transaction consistency "
        "preserves two independent subjects; requesting a cited report adds an "
        "output obligation, not a concern about writing reports.\n"
        "- Keep a simple single-subject request simple. There is no fixed item "
        "count and these arrays are not a task plan.\n"
        "- Preserve any supplied IDs, required values, and non-empty domains.\n"
        "- A canonical enum value alone is not sufficient: a concern's domain "
        "must match its technical subject using the subject-domain guidance. "
        "Do not assign an unrelated domain merely because it appears elsewhere "
        "in the request. Cross-domain concerns must retain their full subject; "
        "do not invent a domain relationship to resolve ambiguity.\n"
        "- Otherwise assign unique O1, O2, ... and C1, C2, ... in request order; "
        "never merge independent subjects or remove an item to fit a summary.\n"
        "- Use empty arrays when the request contains no item of that kind.\n"
        "- Use only the two root arrays and their schema fields; return no task, "
        "dependency, verification, repair, or answer fields.\n"
        "Before returning, compare all request clauses against both arrays: "
        "every explicit correctness constraint must be represented with its "
        "required value and polarity preserved, including trailing constraints. "
        "Do not emit the comparison or add fields; return JSON only.\n\n"
        "REQUEST DOMAINS (scope hints only):\n"
        f"{', '.join(request_domains) or 'none'}\n\n"
        "SUBJECT-DOMAIN GUIDANCE (existing registry, not new requirements):\n"
        f"{domain_guidance}\n\n"
        "CURRENT REQUEST:\n"
        f"{request}"
    )


def _decode_payload(payload: Mapping[str, Any] | str) -> Mapping[str, Any]:
    if isinstance(payload, Mapping):
        return payload
    if not isinstance(payload, str) or not payload.strip():
        raise ValueError("extractor output must be a JSON object")

    text = payload.strip()
    try:
        decoded = decode_structured_json(text)
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
    structured = getattr(provider, "generate_structured", None)
    result = (
        await structured(
            system=EXTRACTION_SYSTEM_PROMPT, user=prompt,
            response_schema=EXTRACTION_RESPONSE_SCHEMA,
        )
        if callable(structured)
        else await provider.generate(system=EXTRACTION_SYSTEM_PROMPT, user=prompt)
    )
    if metrics is not None:
        metrics.add_usage(result.usage)
    extraction = parse_obligation_concern_output(result.text)
    request_domains = set(detect_domains(request))
    for concern in extraction.concerns:
        validate_domain(concern.domain)
        subject_domains = detect_domains(concern.description)
        # Enforce only a request-supported, unambiguous existing detector result.
        # Ambiguous subjects are not relabeled to the first matching domain.
        if len(subject_domains) == 1 and subject_domains[0] in request_domains:
            expected = subject_domains[0]
            if concern.domain != expected:
                raise ValueError(
                    f"concern {concern.concern_id} subject-domain mismatch: "
                    f"expected {expected}, received {concern.domain}"
                )
    return extraction


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
