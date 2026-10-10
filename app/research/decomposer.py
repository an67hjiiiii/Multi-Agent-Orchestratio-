from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass, field
from typing import Any

from app.core.types import RunMetrics
from app.retrieval.text import terms as lexical_terms


try:
    # The schema track is integrated separately; use its canonical types when
    # it is available while keeping this focused commit independently runnable.
    from app.research.task_schema import (
        CANONICAL_TASK_DOMAINS,
        DecompositionResult,
        RequiredObligation,
        TaskItem,
        TaskPlan,
    )
except ModuleNotFoundError as exc:
    if exc.name != "app.research.task_schema":
        raise

    CANONICAL_TASK_DOMAINS = frozenset(
        {"security", "database", "api_architecture"}
    )

    @dataclass
    class TaskItem:
        task_id: str
        title: str
        objective: str
        expected_output: str
        domain: str
        role_profile: str
        depends_on: list[str] = field(default_factory=list)
        covers_obligations: list[str] = field(default_factory=list)

    @dataclass
    class RequiredObligation:
        obligation_id: str
        canonical_kind: str | None
        source_anchor: str

    @dataclass
    class DecompositionResult:
        request: str
        tasks: list[TaskItem] = field(default_factory=list)
        planning_evidence_ids: list[str] = field(default_factory=list)
        status: str = "FAILED"
        warnings: list[str] = field(default_factory=list)
        required_obligations: list[RequiredObligation] = field(default_factory=list)
        covered_obligations: list[str] = field(default_factory=list)
        missing_obligations: list[str] = field(default_factory=list)
        repair_attempted: bool = False
        coverage_validation_reason: str | None = None

    @dataclass
    class TaskPlan:
        tasks: list[TaskItem] = field(default_factory=list)


_PLANNING_ID_PATTERN = re.compile(r"\[([A-Za-z0-9_.:/-]+)\]")
_ORDERED_OBLIGATIONS_PATTERN = re.compile(
    r"(?:\bfirst\b.+\b(?:then|next|subsequently)\b)|"
    r"(?:\b.+\bbefore\b.+)|(?:\b.+\bafter\b.+)|"
    r"(?:\b.+\b(?:is\s+(?:the\s+)?input\s+to|consumes?|receives?|requires?)\b.+)|"
    r"(?:\bdependency\s+chain\b.+\bfrom\b.+\bto\b.+)",
    re.IGNORECASE | re.DOTALL,
)
_REPEATED_OBLIGATIONS_PATTERN = re.compile(
    r"\b(?:repeat|recheck|re-examine|reexamine|again)\b|"
    r"\b(?:shared evidence|using shared evidence)\b",
    re.IGNORECASE,
)
_SEPARATE_OBLIGATIONS_PATTERN = re.compile(
    r"\b(?:each|every)\b[^.!?]*\b(?:separate|separately)\b|"
    r"\bseparate\s+(?:each|every)\b",
    re.IGNORECASE,
)
_LIST_INTRO_PATTERN = re.compile(
    r"\b(?:combine|include|cover|address|map|list|specify)\s+(?P<body>[^.!?]+)",
    re.IGNORECASE,
)
_REVIEW_FOR_PATTERN = re.compile(
    r"\b(?P<action>review|assess|analy[sz]e|audit|inspect)\b\s+"
    r"(?P<target>[^.!?]+?)\s+\bfor\s+"
    r"(?P<body>[^.!?]+)",
    re.IGNORECASE,
)
_COMMAND_BODY_PATTERN = re.compile(
    r"^(?P<action>[A-Za-z]{2,32})\s+"
    r"(?P<body>[^.!?]+)$",
    re.IGNORECASE,
)
_MODAL_BODY_PATTERN = re.compile(
    r"\b(?:must|should|required\s+to|needs?\s+to)\s+"
    r"(?:cover|include|address|identify|review|assess|check|validate|record)\s+"
    r"(?P<body>[^.!?]+)",
    re.IGNORECASE,
)
_COORDINATOR_PATTERN = re.compile(r"\s+\b(?:and|but|or)\b\s+", re.IGNORECASE)
_DEPENDENCY_FROM_TO_PATTERN = re.compile(
    r"\bfrom\s+(?P<first>.+?)\s+\bto\s+(?P<second>.+?)\s*$",
    re.IGNORECASE,
)
_DEPENDENCY_INPUT_PATTERN = re.compile(
    r"(?P<first>.+?)\s+\bis\s+(?:the\s+)?(?:input|prerequisite)\s+"
    r"(?:to|for)\s+(?P<second>.+?)\s*$",
    re.IGNORECASE,
)
_DEPENDENCY_CONSUMER_PATTERN = re.compile(
    r"(?P<second>.+?)\s+\b(?:consumes?|uses?|receives?|requires?)\s+"
    r"(?P<first>.+?)\s*$",
    re.IGNORECASE,
)
_DEPENDENCY_BEFORE_PATTERN = re.compile(
    r"(?P<first>.+?)\s+\bbefore\s+(?P<second>.+?)\s*$",
    re.IGNORECASE,
)
_DEPENDENCY_AFTER_PATTERN = re.compile(
    r"(?P<second>.+?)\s+\bafter\s+(?P<first>.+?)\s*$",
    re.IGNORECASE,
)
_TRAILING_SCOPE_LABEL = re.compile(
    r"\s+(?:obligations?|requirements?|controls?|tasks?)\s*$", re.IGNORECASE
)
_DEPENDENCY_ARGUMENT_PATTERN = re.compile(
    r"\b(?:task|output|result|finding|evidence|assessment|decision)\b",
    re.IGNORECASE,
)
_CLAUSE_ACTION_ROOTS = frozenset(
    {
        "address",
        "analy",
        "assess",
        "audit",
        "authoriz",
        "build",
        "check",
        "confirm",
        "connect",
        "create",
        "decide",
        "design",
        "determine",
        "enforce",
        "establish",
        "evaluate",
        "explain",
        "identify",
        "inspect",
        "keep",
        "map",
        "optimiz",
        "order",
        "protect",
        "perform",
        "record",
        "reject",
        "report",
        "review",
        "scope",
        "specify",
        "validat",
        "verify",
    }
)
_ALIGNMENT_LOW_SIGNAL_TERMS = frozenset(
    {
        "address",
        "analyze",
        "assess",
        "audit",
        "check",
        "complete",
        "current",
        "database",
        "db",
        "determine",
        "endpoint",
        "evaluate",
        "expected",
        "finding",
        "first",
        "obligation",
        "output",
        "api",
        "architecture",
        "report",
        "request",
        "result",
        "review",
        "second",
        "security",
        "service",
        "task",
    }
)
_ACTION_WORD_SUFFIXES = frozenset(
    {"", "s", "es", "ed", "d", "ing", "e", "ze", "zes", "zed", "zing"}
)
# These are request-level domain hints, not proof that a task covers an
# obligation. Coverage is validated separately against the source anchor.
_CANONICAL_DOMAIN_HINTS = {
    "security": frozenset(
        {
            "security",
            "auth",
            "authentication",
            "authorization",
            "jwt",
            "token",
            "permission",
            "identity",
            "login",
            "session",
        }
    ),
    "database": frozenset(
        {
            "database",
            "db",
            "schema",
            "query",
            "index",
            "transaction",
            "consistency",
            "table",
        }
    ),
    "api_architecture": frozenset(
        {
            "api",
            "endpoint",
            "rest",
            "service",
            "sla",
        }
    ),
}
_DOMAIN_LABEL_HINTS = {
    "security": frozenset({"security"}),
    "database": frozenset({"database", "db"}),
    "api_architecture": frozenset({"api", "endpoint", "rest", "service", "sla"}),
}
# A domain label in the request is not always an independent obligation.  In
# particular, "API" and "endpoint" commonly provide context for security or
# data-access work.  Require an API task only when the request also names an
# API-contract concern, while keeping security/database anchors explicit.
_DOMAIN_OBLIGATION_HINTS = {
    "security": _CANONICAL_DOMAIN_HINTS["security"] - _DOMAIN_LABEL_HINTS["security"],
    "database": _CANONICAL_DOMAIN_HINTS["database"],
    "api_architecture": frozenset(
        {
            "contract",
            "design",
            "architecture",
            "validation",
            "validate",
            "validated",
            "invalid",
            "malformed",
            "error",
            "response",
            "sla",
        }
    ),
}
# qwen3:4b has emitted these presentation labels in real Ollama traces.  They
# are deterministic aliases, not new domains; unknown labels remain rejected.
_CANONICAL_DOMAIN_ALIASES = {
    "security": "security",
    "security and identity management": "security",
    "security identity management": "security",
    "database": "database",
    "database management": "database",
    "database system": "database",
    "database systems": "database",
    "api design": "api_architecture",
    "api architecture": "api_architecture",
}
_REQUIRED_TASK_FIELDS = (
    "task_id",
    "title",
    "objective",
    "expected_output",
    "domain",
    "role_profile",
)
_TASK_SCHEMA = (
    '{"tasks":[{"task_id":"T1","title":"short task title",'
    '"objective":"specific objective",'
    '"expected_output":"expected structured output",'
    '"domain":"declared domain",'
    '"role_profile":"declared role profile",'
    '"depends_on":[],"covers_obligations":["O1"]}]}'
)
PROMPT_VERSION = "p-lite-decomposer-v8"
STRUCTURED_OUTPUT_CONFIG_VERSION = "ollama-task-plan-schema-v3"
PLANNER_TEMPERATURE = 0.0
TASK_PLAN_JSON_SCHEMA = TaskPlan.model_json_schema()
_TASK_ITEM_OUTPUT_SCHEMA = TASK_PLAN_JSON_SCHEMA.get("$defs", {}).get("TaskItem")
if isinstance(_TASK_ITEM_OUTPUT_SCHEMA, dict):
    _required_output_fields = list(_TASK_ITEM_OUTPUT_SCHEMA.get("required", []))
    if "covers_obligations" not in _required_output_fields:
        _required_output_fields.append("covers_obligations")
    _TASK_ITEM_OUTPUT_SCHEMA["required"] = _required_output_fields
_SYSTEM_PROMPT = (
    "TASK_DECOMPOSER. Follow the structured task-decomposition protocol in the "
    "user message. Do not invent requirements."
)
_STATIC_PROMPT_PREFIX = (
    f"PROMPT VERSION: {PROMPT_VERSION}\n"
    "OUTPUT PROTOCOL:\n"
    "Return exactly one JSON object and no markdown or explanation.\n"
    f"Schema: {_TASK_SCHEMA}\n\n"
    "PLANNER RULES:\n"
    "The current request is the sole source of obligations. Planning evidence is "
    "non-binding guidance only; never let it add a category, domain, implementation "
    "detail, evidence need, or task that is not stated or directly implied by the "
    "request. Identify one task per explicit independent obligation before writing "
    "tasks; do not enumerate every category listed in a planning item. Add a "
    "dependency only when the request states order, causality, or that one task "
    "consumes another task's output. Repeat, recheck, and shared-evidence wording "
    "does not create a dependency by itself. Use only canonical domain IDs: "
    "security, database, or api_architecture. Preserve high-signal request terms "
    "in each title and objective instead of adding guessed specifics. For a "
    "request naming multiple domains, emit at least one task anchored to each "
    "named domain; distinct obligations in the same domain remain separate when "
    "each has its own request anchor. Do not enumerate planning categories as "
    "extra tasks when the request does not name them. Do not add N/O, "
    "execution, retrieval, or answer evidence. For explicitly ordered or dependent "
    "obligations, emit separate tasks with separate expected outputs and put the "
    "predecessor task ID in depends_on. Every task must include every schema field; "
    "use depends_on: [] when it has no predecessor. Every task must list the request-"
    "derived obligation IDs it covers in covers_obligations. Never emit blank "
    "placeholder tasks."
)


class _DecompositionOutputError(ValueError):
    """Raised when a model response cannot satisfy the P-lite contract."""


@dataclass
class _CoverageState:
    covered_ids: list[str]
    missing_ids: list[str]
    reason: str
    missing_concern_ids: list[str] = field(default_factory=list)
    misrouted_concern_ids: list[str] = field(default_factory=list)


class _CoverageValidationError(_DecompositionOutputError):
    def __init__(self, state: _CoverageState):
        super().__init__(state.reason)
        self.state = state


def _extract_planning_evidence_ids(planning_context: str) -> list[str]:
    """Preserve only evidence identifiers present in the bounded context."""

    return list(dict.fromkeys(_PLANNING_ID_PATTERN.findall(planning_context)))


def _canonical_obligation_kind(source_anchor: str) -> str | None:
    anchor_terms = lexical_terms(source_anchor)
    matches = [
        domain
        for domain, hints in _DOMAIN_OBLIGATION_HINTS.items()
        if anchor_terms & hints
    ]
    return matches[0] if len(matches) == 1 else None


@dataclass(frozen=True)
class _ObligationStructure:
    anchors: tuple[str, ...]
    dependency_pairs: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class _ExplicitConcern:
    """A request-derived semantic concern checked independently of obligations."""

    concern_id: str
    source_anchor: str
    canonical_domain: str | None


def _clean_anchor(value: str) -> str:
    """Return a stable source excerpt without coordinator punctuation."""

    clean = re.sub(r"\s+", " ", value).strip(" \t\r\n,;:.!?-")
    clean = re.sub(
        r"^(?:and|but|or|then|next|subsequently)\s+", "", clean, flags=re.IGNORECASE
    )
    return clean


def _has_clause_action(value: str) -> bool:
    """Detect a predicate without binding extraction to research domains."""

    clean = value.strip()
    if re.match(
        r"^(?:for|before|after|when|while|if|using|within|in\s+order\s+to)\b",
        clean,
        re.IGNORECASE,
    ):
        return False
    words = re.findall(r"[A-Za-z]+", clean.casefold())
    for word in words[:2]:
        for root in _CLAUSE_ACTION_ROOTS:
            if word.startswith(root) and word[len(root) :] in _ACTION_WORD_SUFFIXES:
                return True
    modal_action = re.search(
        r"\b(?:must|should|may|can|will|needs?\s+to|required\s+to)\s+"
        r"(?:be\s+)?(?P<action>[A-Za-z]+)",
        clean,
        re.IGNORECASE,
    )
    if modal_action and any(
        modal_action.group("action").casefold().startswith(root)
        and modal_action.group("action").casefold()[len(root) :]
        in _ACTION_WORD_SUFFIXES
        for root in _CLAUSE_ACTION_ROOTS
    ):
        return True
    return bool(
        re.search(
            r"\b(?:is|are|was|were|be|been|being)\s+"
            r"(?:\w+\s+){0,2}\w+(?:ed|en)\b",
            value,
            re.IGNORECASE,
        )
    )


def _is_task_action_clause(value: str, *, allow_nominal_task_label: bool = False) -> bool:
    """Accept only clauses that express an obligation, not a time/state marker."""

    clean = _clean_anchor(value)
    if not clean or re.search(r"\b(?:what|why|how|whether)\b", clean, re.IGNORECASE):
        return False
    if _has_clause_action(clean):
        return True

    # Modal clauses state an action even when its verb is outside the small
    # imperative-root matcher above (for example, "must complete").  This
    # intentionally requires an actual modal predicate, so a bare phase or
    # gerund such as "release", "deployment", or "proceeding" is not enough.
    modal_action = re.search(
        r"\b(?:must|should|may|can|will|needs?\s+to|required\s+to)\s+"
        r"(?:be\s+)?(?P<action>[A-Za-z]+)\b",
        clean,
        re.IGNORECASE,
    )
    if modal_action and modal_action.group("action").casefold() not in {
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
    }:
        return True

    # The left side of "X before Y is executed" may be a task label rather
    # than an imperative clause.  Accept a multi-word action-nominal label
    # there only; the right side still needs an actual action predicate, which
    # keeps time/state markers from becoming phantom obligations.
    terms = lexical_terms(clean)
    return bool(
        allow_nominal_task_label
        and len(terms) >= 2
        and (
            "task" in terms
            or any(
                re.search(r"(?:tion|sion|ment|ance|ence|ing)$", term)
                for term in terms
            )
        )
    )


def _coordinated_anchor(value: str) -> str:
    """Trim shared conversational context while retaining the request wording."""

    clean = _clean_anchor(value)
    modal = re.search(
        r"\b(?:must|should|needs?\s+to|required\s+to)\s+(?P<tail>.+)$",
        clean,
        re.IGNORECASE,
    )
    if modal and _has_clause_action(modal.group("tail")):
        clean = _clean_anchor(modal.group("tail"))
    by_clause = re.search(r"\bby\s+(?P<tail>.+)$", clean, re.IGNORECASE)
    if by_clause and _has_clause_action(by_clause.group("tail")):
        clean = _clean_anchor(by_clause.group("tail"))
    return clean


def _split_list_body(body: str) -> list[str]:
    """Split an explicitly scoped list, including nominal list members."""

    clean_body = _clean_anchor(body)
    label = re.search(
        r"\b(?:obligations?|requirements?|controls?|tasks?)\b", clean_body, re.IGNORECASE
    )
    if label:
        before_label = clean_body[: label.start()].strip()
        if "," in before_label or _COORDINATOR_PATTERN.search(before_label):
            clean_body = before_label
    clean_body = re.sub(
        r"^(?:the|both|each|every|separate|distinct)\s+",
        "",
        clean_body,
        flags=re.IGNORECASE,
    )
    values = re.split(r"\s*[;,]\s*|\s+\b(?:and|or)\b\s+", clean_body, flags=re.IGNORECASE)
    return [anchor for raw in values if (anchor := _clean_anchor(raw))]


_ACTION_CLAUSE = "ACTION_CLAUSE"
_SHARED_OBJECT_OR_HEAD = "SHARED_OBJECT_OR_HEAD"
_NOUN_FRAGMENT = "NOUN_FRAGMENT"
_TEMPORAL_OR_STATE_FRAGMENT = "TEMPORAL_OR_STATE_FRAGMENT"
_AMBIGUOUS = "AMBIGUOUS"
_TEMPORAL_OR_STATE_LEAD_PATTERN = re.compile(
    r"^(?:for|before|after|when|while|if|using|within|without|with|during|"
    r"then|next|subsequently|the|a|an)\b",
    re.IGNORECASE,
)


def _has_independent_unknown_action_shape(
    value: str, *, preceding_action: str | None
) -> bool:
    """Accept a bare conjunct only when several structural signals agree.

    Unknown heads are deliberately not treated as actions from their spelling or
    word count alone.  They need an established preceding action, a distinct
    request-level obligation kind, and an obligation-shaped object phrase.
    """

    if not preceding_action or _TEMPORAL_OR_STATE_LEAD_PATTERN.match(value):
        return False
    terms = re.findall(r"[A-Za-z]+", value.casefold())
    if len(terms) < 3 or re.search(r"(?:tion|sion|ance|ence|ness|ity)$", terms[0]):
        return False
    preceding_kind = _canonical_obligation_kind(preceding_action)
    candidate_kind = _canonical_obligation_kind(value)
    if not candidate_kind or candidate_kind == preceding_kind:
        return False
    # A non-head deverbal object makes the conjunct a bounded action/object
    # phrase rather than a simple alternate noun under the shared command.
    return any(term.endswith("ing") for term in terms[1:])


def _classify_coordinated_segment(
    value: str, *, preceding_action: str | None = None
) -> str:
    """Classify a candidate before permitting it to become an obligation."""

    clean = _clean_anchor(value)
    if not clean:
        return _AMBIGUOUS
    if _TEMPORAL_OR_STATE_LEAD_PATTERN.match(clean):
        return _TEMPORAL_OR_STATE_FRAGMENT
    if _is_task_action_clause(clean):
        return _ACTION_CLAUSE
    if _has_independent_unknown_action_shape(
        clean, preceding_action=preceding_action
    ):
        return _ACTION_CLAUSE
    terms = re.findall(r"[A-Za-z]+", clean.casefold())
    if len(terms) <= 2 or re.match(r"^(?:the|a|an)\b", clean, re.IGNORECASE):
        return _SHARED_OBJECT_OR_HEAD
    return _NOUN_FRAGMENT


def _accept_action_segments(candidates: list[str]) -> list[str]:
    """Fail closed unless every candidate is an independently task-like clause."""

    clauses = [_clean_anchor(candidate) for candidate in candidates]
    clauses = [clause for clause in clauses if clause]
    if len(clauses) < 2:
        return []

    preceding_action: str | None = None
    for clause in clauses:
        classification = _classify_coordinated_segment(
            clause, preceding_action=preceding_action
        )
        if classification != _ACTION_CLAUSE:
            return []
        preceding_action = clause
    return clauses


def _split_command_body(action: str, body: str, *, comma_list: bool) -> list[str]:
    """Stage a command body and retain only independently actionable segments."""

    separator = (
        r"\s*[;,]\s*(?:and\s+|but\s+|or\s+)?|\s+\b(?:and|but|or)\b\s+"
        if comma_list
        else r"\s+\b(?:and|but|or)\b\s+"
    )
    parts = [
        anchor
        for raw in re.split(separator, _clean_anchor(body), flags=re.IGNORECASE)
        if (anchor := _clean_anchor(raw))
    ]
    if len(parts) < 2:
        return []

    # The initial imperative scopes only the first candidate.  Later candidates
    # must carry their own predicate (or satisfy the conservative bare-conjunct
    # classifier) and cannot inherit the command head.
    return _accept_action_segments([f"{action} {parts[0]}", *parts[1:]])


def _dependency_structure(request: str) -> _ObligationStructure | None:
    """Extract prerequisite-to-dependent arguments from explicit relation syntax."""

    source = re.sub(r"\s+", " ", request).strip().rstrip(".!?")
    clause_source = source.rsplit(":", maxsplit=1)[-1].strip()

    leading_first = re.match(r"^first\s+(?P<body>.+)$", clause_source, re.IGNORECASE)
    suffix_first = re.match(
        r"^(?P<first>.+?)\s+first\s*,?\s*"
        r"(?:then|next|subsequently)\s+(?P<rest>.+)$",
        clause_source,
        re.IGNORECASE,
    )
    ordered_parts: list[str] = []
    if leading_first:
        ordered_parts = re.split(
            r"\s*,?\s*(?:and\s+)?\b(?:then|next|subsequently)\b\s+",
            leading_first.group("body"),
            flags=re.IGNORECASE,
        )
    elif suffix_first:
        ordered_parts = [suffix_first.group("first")]
        ordered_parts.extend(
            re.split(
                r"\s*,?\s*(?:and\s+)?\b(?:then|next|subsequently)\b\s+",
                suffix_first.group("rest"),
                flags=re.IGNORECASE,
            )
        )
    elif re.search(r"\bthen\b", clause_source, re.IGNORECASE) and not (
        re.match(r"^if\b", clause_source, re.IGNORECASE)
        and re.search(r"\botherwise\b", clause_source, re.IGNORECASE)
    ):
        ordered_parts = re.split(
            r"\s*[;,]\s*(?:and\s+)?(?:then\s+)?|\s+\bthen\b\s+",
            clause_source,
            flags=re.IGNORECASE,
        )

    if ordered_parts:
        anchors = [_coordinated_anchor(part) for part in ordered_parts]
        anchors = [anchor for anchor in anchors if anchor]
        while len(anchors) >= 3 and not _has_clause_action(anchors[0]):
            anchors.pop(0)
        if len(anchors) >= 2:
            pairs = tuple((index, index + 1) for index in range(len(anchors) - 1))
            return _ObligationStructure(tuple(anchors), pairs)

    if re.search(r"\b(?:dependency|chain|graph|flow)\b", source, re.IGNORECASE):
        match = _DEPENDENCY_FROM_TO_PATTERN.search(clause_source)
        if match:
            first = _clean_anchor(match.group("first"))
            second = _clean_anchor(match.group("second"))
            if first and second:
                return _ObligationStructure((first, second), ((0, 1),))

    match = _DEPENDENCY_INPUT_PATTERN.search(clause_source)
    if match:
        first = re.split(r"\bwhere\b", match.group("first"), flags=re.IGNORECASE)[-1]
        first = _clean_anchor(first)
        second = _clean_anchor(match.group("second"))
        if first and second:
            return _ObligationStructure((first, second), ((0, 1),))

    # "Before accepting ..., do X" is a lead-in, not an X -> accepting
    # dependency. A relation needs task/action obligations on both sides of
    # "before"; bare lifecycle states and explanatory prose stay in one anchor.
    if not re.match(r"^\s*before\b", clause_source, re.IGNORECASE):
        match = _DEPENDENCY_BEFORE_PATTERN.search(clause_source)
        if match:
            first_raw = match.group("first")
            receive = re.search(
                r"\b(?:receive|receives|received)\s+(?P<object>.+)$",
                first_raw,
                re.IGNORECASE,
            )
            first = _clean_anchor(receive.group("object") if receive else first_raw)
            second = _clean_anchor(match.group("second").split(";", maxsplit=1)[0])
            if (
                _is_task_action_clause(first, allow_nominal_task_label=True)
                and _is_task_action_clause(second)
            ):
                return _ObligationStructure((first, second), ((0, 1),))

    match = _DEPENDENCY_AFTER_PATTERN.search(clause_source)
    if match:
        first = _clean_anchor(match.group("first"))
        second = _clean_anchor(match.group("second"))
        if first and second:
            return _ObligationStructure((first, second), ((0, 1),))

    match = _DEPENDENCY_CONSUMER_PATTERN.search(clause_source)
    if match and len(_DEPENDENCY_ARGUMENT_PATTERN.findall(clause_source)) >= 2:
        first = _clean_anchor(match.group("first"))
        second = re.split(r"\bso\b", match.group("second"), flags=re.IGNORECASE)[-1]
        second = _clean_anchor(second)
        if first and second:
            return _ObligationStructure((first, second), ((0, 1),))
    return None


def _coordinated_structure(request: str) -> _ObligationStructure | None:
    """Segment explicit lists and independent coordinated clauses."""

    normalized = re.sub(r"\s+", " ", request).strip().rstrip(".!?")
    clause_source = normalized.rsplit(":", maxsplit=1)[-1].strip()
    if re.search(
        r"[,;]\s*(?:but\s+)?(?:do\s+not|don't|without|avoid)\b",
        clause_source,
        re.IGNORECASE,
    ):
        return None

    review_for = _REVIEW_FOR_PATTERN.search(normalized)
    if review_for and not _REPEATED_OBLIGATIONS_PATTERN.search(normalized):
        action = _clean_anchor(review_for.group("action"))
        target = _clean_anchor(review_for.group("target"))
        attributes = _split_list_body(review_for.group("body"))
        # The object under review remains part of every split anchor.  Only
        # split a plain coordinated attribute list; embedded action clauses
        # fall through to the existing clause extraction without over-splitting.
        if (
            action
            and target
            and len(attributes) >= 2
            and all(not _has_clause_action(attribute) for attribute in attributes)
        ):
            anchors = _accept_action_segments(
                [f"{action} {target} for {attribute}" for attribute in attributes]
            )
            if anchors:
                return _ObligationStructure(tuple(anchors))

    # Stage 1 handles an explicit comma/semicolon action list before the
    # conjunction-only path.  The command pattern is a candidate parser only:
    # acceptance is centralized in _accept_action_segments.
    command = _COMMAND_BODY_PATTERN.search(clause_source)
    if command and not _REPEATED_OBLIGATIONS_PATTERN.search(normalized):
        body = command.group("body")
        anchors = []
        if re.search(r"[;,]", body):
            anchors = _split_command_body(command.group("action"), body, comma_list=True)
        if not anchors and _COORDINATOR_PATTERN.search(body):
            # Stage 2: conjunction-only candidates.  This follows the same
            # classifier and fail-closed rule as the comma-list stage.
            anchors = _split_command_body(
                command.group("action"), body, comma_list=False
            )
        if len(anchors) >= 2:
            return _ObligationStructure(tuple(anchors))

    bodies: list[str] = []
    if ":" in normalized:
        bodies.append(clause_source)
    for pattern in (
        _MODAL_BODY_PATTERN,
        _LIST_INTRO_PATTERN,
    ):
        match = pattern.search(normalized)
        if match and not _REPEATED_OBLIGATIONS_PATTERN.search(normalized):
            bodies.append(match.group("body"))
    for body in bodies:
        anchors = _accept_action_segments(_split_list_body(body))
        if anchors:
            return _ObligationStructure(tuple(anchors))

    # A non-imperative request (for example, a modal sentence) can still
    # present top-level action clauses.  It receives the same full-set
    # classification instead of the former partial action-count acceptance.
    if re.search(r"[;,]", clause_source):
        parts = [
            anchor
            for raw in re.split(
                r"\s*[;,]\s*(?:and\s+|but\s+|or\s+)?|"
                r"\s+\b(?:and|but|or)\b\s+",
                clause_source,
                flags=re.IGNORECASE,
            )
            if (anchor := _coordinated_anchor(raw))
        ]
        anchors = _accept_action_segments(parts)
        if anchors:
            return _ObligationStructure(tuple(anchors))

    parts = [
        anchor
        for raw in _COORDINATOR_PATTERN.split(clause_source)
        if (anchor := _coordinated_anchor(raw))
    ]
    anchors = _accept_action_segments(parts)
    if anchors:
        return _ObligationStructure(tuple(anchors))
    return None


def _derive_obligation_structure(request: str) -> _ObligationStructure:
    dependency = _dependency_structure(request)
    if dependency is not None:
        return dependency
    coordinated = _coordinated_structure(request)
    if coordinated is not None:
        return coordinated
    return _ObligationStructure((request.strip(),))


def _derive_required_obligations(request: str) -> list[RequiredObligation]:
    """Extract bounded atomic clauses while retaining request-derived anchors.

    The segmenter uses only general coordination and dependency syntax. If the
    request does not expose at least two supported clauses, the complete request
    remains one traceable obligation rather than being expanded from domain
    templates, scenario IDs, planning evidence, or evaluator gold.
    """

    structure = _derive_obligation_structure(request)

    return [
        RequiredObligation(
            obligation_id=f"O{index}",
            canonical_kind=_canonical_obligation_kind(anchor),
            source_anchor=anchor,
        )
        for index, anchor in enumerate(structure.anchors, start=1)
    ]


def _derive_explicit_concerns(request: str) -> list[_ExplicitConcern]:
    """Retain explicit list concerns without changing obligation segmentation."""

    anchors: list[str] = []
    for pattern in (_MODAL_BODY_PATTERN, _LIST_INTRO_PATTERN):
        match = pattern.search(request)
        if not match:
            continue
        anchors.extend(_split_list_body(match.group("body")))

    unique_anchors: list[str] = []
    seen_anchors: set[str] = set()
    for anchor in anchors:
        key = anchor.casefold()
        if key in seen_anchors:
            continue
        seen_anchors.add(key)
        unique_anchors.append(anchor)

    return [
        _ExplicitConcern(
            concern_id=f"C{index}",
            source_anchor=anchor,
            canonical_domain=_canonical_obligation_kind(anchor),
        )
        for index, anchor in enumerate(unique_anchors, start=1)
    ]


def _format_obligations(obligations: list[RequiredObligation]) -> str:
    return "\n".join(
        f"- {item.obligation_id} | canonical_kind={item.canonical_kind or 'unknown'} "
        f"| source_anchor={item.source_anchor}"
        for item in obligations
    )


def _format_concerns(concerns: list[_ExplicitConcern]) -> str:
    return "\n".join(
        f"- {item.concern_id} | canonical_domain={item.canonical_domain or 'unknown'} "
        f"| source_anchor={item.source_anchor}"
        for item in concerns
    )


def _extract_json(text: object) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise _DecompositionOutputError("planner response was empty")

    cleaned = text.strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise _DecompositionOutputError(
            "planner response must be exactly one JSON object"
        ) from exc

    if not isinstance(parsed, dict):
        raise _DecompositionOutputError("planner response must be a JSON object")
    return parsed


def _required_text(raw: dict[str, Any], field_name: str, task_index: int) -> str:
    value = raw.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise _DecompositionOutputError(
            f"task {task_index} field {field_name} must be a non-empty string"
        )
    return value.strip()


def _canonical_domain(value: str) -> str | None:
    """Map only observed presentation labels to the locked domain IDs."""

    normalized = re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
    return _CANONICAL_DOMAIN_ALIASES.get(normalized)


def _parse_tasks(parsed: dict[str, Any]) -> list[TaskItem]:
    raw_tasks = parsed.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise _DecompositionOutputError("planner response must contain a non-empty tasks list")

    tasks: list[TaskItem] = []
    for index, raw in enumerate(raw_tasks, start=1):
        if not isinstance(raw, dict):
            raise _DecompositionOutputError(f"task {index} must be a JSON object")

        values = {
            field_name: _required_text(raw, field_name, index)
            for field_name in _REQUIRED_TASK_FIELDS
        }
        if "depends_on" not in raw:
            raise _DecompositionOutputError(
                f"task {index} must include depends_on as a list"
            )
        raw_dependencies = raw["depends_on"]
        if not isinstance(raw_dependencies, list):
            raise _DecompositionOutputError(f"task {index} depends_on must be a list")

        dependencies: list[str] = []
        for dependency in raw_dependencies:
            if not isinstance(dependency, str) or not dependency.strip():
                raise _DecompositionOutputError(
                    f"task {index} depends_on must contain non-empty strings"
                )
            dependencies.append(dependency.strip())

        if "covers_obligations" not in raw:
            raise _DecompositionOutputError(
                f"task {index} must include covers_obligations as a list"
            )
        raw_coverage = raw["covers_obligations"]
        if not isinstance(raw_coverage, list):
            raise _DecompositionOutputError(
                f"task {index} covers_obligations must be a list"
            )
        coverage_ids: list[str] = []
        for obligation_id in raw_coverage:
            if not isinstance(obligation_id, str) or not obligation_id.strip():
                raise _DecompositionOutputError(
                    f"task {index} covers_obligations must contain non-empty strings"
                )
            normalized_id = obligation_id.strip()
            if normalized_id not in coverage_ids:
                coverage_ids.append(normalized_id)

        canonical_domain = _canonical_domain(values["domain"])
        if canonical_domain is None or canonical_domain not in CANONICAL_TASK_DOMAINS:
            raise _DecompositionOutputError(
                f"task {index} domain must be one of the canonical task domains"
            )
        values["domain"] = canonical_domain
        try:
            tasks.append(
                TaskItem(
                    **values,
                    depends_on=dependencies,
                    covers_obligations=coverage_ids,
                )
            )
        except (TypeError, ValueError) as exc:
            raise _DecompositionOutputError(
                f"task {index} did not satisfy the canonical task schema"
            ) from exc

    return tasks


def _validate_dependencies(tasks: list[TaskItem]) -> None:
    task_ids = [task.task_id for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise _DecompositionOutputError("task_id values must be unique")

    known_ids = set(task_ids)
    indegree = {task_id: 0 for task_id in task_ids}
    dependents: dict[str, list[str]] = {task_id: [] for task_id in task_ids}
    for task in tasks:
        if len(task.depends_on) != len(set(task.depends_on)):
            raise _DecompositionOutputError("task dependency list contains duplicate entries")
        for dependency in task.depends_on:
            if dependency not in known_ids:
                raise _DecompositionOutputError("task dependency references an unknown task ID")
            if dependency == task.task_id:
                raise _DecompositionOutputError("task dependency cannot reference its own task ID")
            dependents[dependency].append(task.task_id)
            indegree[task.task_id] += 1

    ready = [task_id for task_id in task_ids if indegree[task_id] == 0]
    visited = 0
    while ready:
        current = ready.pop(0)
        visited += 1
        for dependent in dependents[current]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
    if visited != len(task_ids):
        raise _DecompositionOutputError("task dependency graph contains a cycle")


def _validate_explicit_coverage(
    request: str,
    tasks: list[TaskItem],
    required_obligations: list[RequiredObligation],
) -> _CoverageState:
    required_by_id = {
        obligation.obligation_id: obligation for obligation in required_obligations
    }
    covered: set[str] = set()
    invalid_reasons: list[str] = []
    requires_separate_tasks = bool(_SEPARATE_OBLIGATIONS_PATTERN.search(request))

    for task in tasks:
        coverage_ids = list(dict.fromkeys(task.covers_obligations))
        if not coverage_ids:
            task_text = f"{task.title} {task.objective} {task.expected_output}"
            coverage_ids = [
                obligation.obligation_id
                for obligation in required_obligations
                if _retains_source_anchor(task_text, obligation.source_anchor)
            ]
            if coverage_ids:
                task.covers_obligations = coverage_ids

        if not coverage_ids:
            invalid_reasons.append(
                f"task {task.task_id} does not claim a request-derived obligation"
            )
            continue

        if requires_separate_tasks and len(coverage_ids) > 1:
            invalid_reasons.append(
                f"task {task.task_id} combines obligations that the request requires separately"
            )
            continue

        task_text = f"{task.title} {task.objective} {task.expected_output}"
        for obligation_id in coverage_ids:
            obligation = required_by_id.get(obligation_id)
            if obligation is None:
                invalid_reasons.append(
                    f"task {task.task_id} references unknown obligation {obligation_id}"
                )
                continue
            if not _retains_source_anchor(task_text, obligation.source_anchor):
                invalid_reasons.append(
                    f"task {task.task_id} does not retain source anchor for {obligation_id}"
                )
                continue
            covered.add(obligation_id)

    covered_ids = [
        obligation.obligation_id
        for obligation in required_obligations
        if obligation.obligation_id in covered
    ]
    missing_ids = [
        obligation.obligation_id
        for obligation in required_obligations
        if obligation.obligation_id not in covered
    ]
    if invalid_reasons or missing_ids:
        reason_parts = invalid_reasons
        if missing_ids:
            reason_parts.append("missing required obligations: " + ", ".join(missing_ids))
        raise _CoverageValidationError(
            _CoverageState(covered_ids, missing_ids, "; ".join(reason_parts))
        )
    return _CoverageState(covered_ids, [], "complete obligation coverage")


def _retains_source_anchor(task_text: str, source_anchor: str) -> bool:
    """Require semantic text evidence; a matching domain label is not proof."""

    raw_task_terms = lexical_terms(task_text)
    raw_anchor_terms = lexical_terms(source_anchor)
    filtered_task_terms = raw_task_terms - _ALIGNMENT_LOW_SIGNAL_TERMS
    filtered_anchor_terms = raw_anchor_terms - _ALIGNMENT_LOW_SIGNAL_TERMS
    if filtered_task_terms and filtered_anchor_terms:
        task_terms = filtered_task_terms
        anchor_terms = filtered_anchor_terms
    else:
        # Filtering must be all-or-nothing for this comparison.  Falling back
        # on only one side made a task that explicitly retained a low-signal
        # request anchor look unrelated, while domain metadata never proves it.
        task_terms = raw_task_terms
        anchor_terms = raw_anchor_terms
    if task_terms.intersection(anchor_terms):
        return True

    # Cover ordinary inflectional variants without a scenario/domain synonym
    # table: authorization/authorize, validation/validate, identity/identify.
    def comparison_forms(term: str) -> tuple[str, ...]:
        forms = [term]
        for prefix in ("un", "in", "non"):
            if term.startswith(prefix) and len(term) - len(prefix) >= 4:
                forms.append(term[len(prefix) :])
        return tuple(forms)

    for raw_task_term in task_terms:
        for raw_anchor_term in anchor_terms:
            for task_term in comparison_forms(raw_task_term):
                for anchor_term in comparison_forms(raw_anchor_term):
                    limit = min(len(task_term), len(anchor_term))
                    shared = next(
                        (
                            size
                            for size in range(limit, 3, -1)
                            if task_term[:size] == anchor_term[:size]
                        ),
                        0,
                    )
                    if shared >= 4 and shared / limit >= 0.55:
                        return True
    return False


def _validate_explicit_concerns(
    tasks: list[TaskItem],
    concerns: list[_ExplicitConcern],
) -> tuple[list[str], list[str]]:
    """Return missing and misrouted request concerns independently of O* claims.

    This deliberately checks each request-derived concern separately instead of
    accepting an existential lexical match against an umbrella obligation.
    Domain metadata is only a routing check after task text retains the concern.
    """

    missing_ids: list[str] = []
    misrouted_ids: list[str] = []
    for concern in concerns:
        retaining_tasks = [
            task
            for task in tasks
            if _retains_source_anchor(
                f"{task.title} {task.objective} {task.expected_output}",
                concern.source_anchor,
            )
        ]
        if not retaining_tasks:
            missing_ids.append(concern.concern_id)
            continue
        if concern.canonical_domain and not any(
            task.domain == concern.canonical_domain for task in retaining_tasks
        ):
            misrouted_ids.append(concern.concern_id)
    return missing_ids, misrouted_ids


def _validate_dependency_direction(
    request: str,
    tasks: list[TaskItem],
    required_obligations: list[RequiredObligation],
) -> None:
    """Validate each explicit prerequisite -> dependent obligation edge."""

    structure = _derive_obligation_structure(request)
    if not structure.dependency_pairs:
        return

    tasks_by_obligation: dict[str, list[TaskItem]] = {
        obligation.obligation_id: [] for obligation in required_obligations
    }
    for task in tasks:
        for obligation_id in task.covers_obligations:
            if obligation_id in tasks_by_obligation:
                tasks_by_obligation[obligation_id].append(task)

    for prerequisite_index, dependent_index in structure.dependency_pairs:
        prerequisite_id = required_obligations[prerequisite_index].obligation_id
        dependent_id = required_obligations[dependent_index].obligation_id
        prerequisite_tasks = tasks_by_obligation[prerequisite_id]
        dependent_tasks = tasks_by_obligation[dependent_id]
        if not prerequisite_tasks or not dependent_tasks:
            continue
        prerequisite_task_ids = {task.task_id for task in prerequisite_tasks}
        dependent_task_ids = {task.task_id for task in dependent_tasks}
        if prerequisite_task_ids.intersection(dependent_task_ids):
            raise _DecompositionOutputError(
                "explicitly ordered obligations require separate tasks"
            )
        if any(
            dependency in dependent_task_ids
            for task in prerequisite_tasks
            for dependency in task.depends_on
        ):
            raise _DecompositionOutputError(
                f"dependency direction is reversed: {dependent_id} must depend on "
                f"{prerequisite_id}"
            )
        if not any(
            dependency in prerequisite_task_ids
            for task in dependent_tasks
            for dependency in task.depends_on
        ):
            raise _DecompositionOutputError(
                f"ordered obligation {dependent_id} must depend on prerequisite "
                f"{prerequisite_id}"
            )


def _validate_obligation_coverage(
    request: str,
    tasks: list[TaskItem],
    required_obligations: list[RequiredObligation],
    explicit_concerns: list[_ExplicitConcern] | None = None,
) -> _CoverageState:
    """Validate obligations, explicit concerns, and dependency structure."""

    explicit_concerns = explicit_concerns or []
    coverage_error: _CoverageValidationError | None = None
    try:
        coverage = _validate_explicit_coverage(request, tasks, required_obligations)
    except _CoverageValidationError as exc:
        coverage = exc.state
        coverage_error = exc

    missing_concern_ids, misrouted_concern_ids = _validate_explicit_concerns(
        tasks,
        explicit_concerns,
    )
    concern_reasons: list[str] = []
    if missing_concern_ids:
        concern_reasons.append(
            "missing explicit concerns: " + ", ".join(missing_concern_ids)
        )
    if misrouted_concern_ids:
        concern_reasons.append(
            "misrouted explicit concerns: " + ", ".join(misrouted_concern_ids)
        )

    structural_reasons: list[str] = []
    try:
        _validate_dependencies(tasks)
    except _DecompositionOutputError as exc:
        structural_reasons.append(str(exc))

    if (
        coverage_error is None
        and not concern_reasons
        and not structural_reasons
    ):
        try:
            _validate_dependency_direction(request, tasks, required_obligations)
        except _DecompositionOutputError as exc:
            structural_reasons.append(str(exc))

    ordered = bool(_derive_obligation_structure(request).dependency_pairs)
    if not ordered and _REPEATED_OBLIGATIONS_PATTERN.search(request) and any(
        task.depends_on for task in tasks
    ):
        structural_reasons.append(
            "repeated or shared-evidence obligations are independent unless "
            "the request states an order or dependency"
        )

    if coverage_error is not None or concern_reasons or structural_reasons:
        # Preserve valid task-to-obligation claims so the one bounded repair
        # corrects only the structural defect instead of rebuilding the plan.
        reasons = []
        if coverage_error is not None:
            reasons.append(coverage.reason)
        reasons.extend(concern_reasons)
        reasons.extend(structural_reasons)
        raise _CoverageValidationError(
            _CoverageState(
                coverage.covered_ids,
                coverage.missing_ids,
                "; ".join(dict.fromkeys(reasons)),
                missing_concern_ids=missing_concern_ids,
                misrouted_concern_ids=misrouted_concern_ids,
            )
        )
    return coverage


def _supports_generation_keyword(provider: object, keyword: str) -> bool:
    try:
        parameters = inspect.signature(provider.generate).parameters.values()
    except (AttributeError, TypeError, ValueError):
        return False
    return any(
        parameter.name == keyword or parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters
    )


async def _generate_structured(provider: object, system: str, user: str):
    kwargs: dict[str, object] = {"system": system, "user": user}
    if _supports_generation_keyword(provider, "think"):
        kwargs["think"] = False
    if _supports_generation_keyword(provider, "format"):
        kwargs["format"] = TASK_PLAN_JSON_SCHEMA
    if _supports_generation_keyword(provider, "temperature"):
        kwargs["temperature"] = PLANNER_TEMPERATURE
    return await provider.generate(**kwargs)


def _prompt(
    query: str,
    planning_context: str,
    required_obligations: list[RequiredObligation],
    conversation_context: str = "",
    explicit_concerns: list[_ExplicitConcern] | None = None,
    retry_reason: str | None = None,
    previous_plan: str = "",
    coverage: _CoverageState | None = None,
) -> str:
    explicit_concerns = explicit_concerns or []
    retry_note = ""
    if retry_reason:
        covered_ids = coverage.covered_ids if coverage else []
        missing_ids = coverage.missing_ids if coverage else [
            item.obligation_id for item in required_obligations
        ]
        missing_set = set(missing_ids)
        missing_obligations = [
            item for item in required_obligations if item.obligation_id in missing_set
        ]
        missing_concern_ids = coverage.missing_concern_ids if coverage else [
            item.concern_id for item in explicit_concerns
        ]
        misrouted_concern_ids = coverage.misrouted_concern_ids if coverage else []
        missing_concern_set = set(missing_concern_ids)
        misrouted_concern_set = set(misrouted_concern_ids)
        missing_concerns = [
            item for item in explicit_concerns if item.concern_id in missing_concern_set
        ]
        misrouted_concerns = [
            item
            for item in explicit_concerns
            if item.concern_id in misrouted_concern_set
        ]
        retry_note = (
            "\n\nPREVIOUS INVALID TASK PLAN:\n"
            f"{previous_plan}\n\n"
            "COVERAGE REPAIR:\n"
            f"Previous validation failure: {retry_reason}\n"
            f"Already covered obligation IDs: {', '.join(covered_ids) or 'none'}\n"
            "Missing obligations:\n"
            f"{_format_obligations(missing_obligations)}\n"
            "Missing explicit concerns:\n"
            f"{_format_concerns(missing_concerns) or 'none'}\n"
            "Misrouted explicit concerns:\n"
            f"{_format_concerns(misrouted_concerns) or 'none'}\n"
            "Return one corrected complete plan. Preserve every already-covered "
            "obligation and correctly routed concern, then add every missing obligation "
            "and concern. Do not replace one covered set with another. Return a corrected "
            "JSON object only."
        )
    concern_section = ""
    if explicit_concerns:
        concern_section = (
            "EXPLICIT CONCERNS TO PRESERVE "
            "(derived only from the current request):\n"
            f"{_format_concerns(explicit_concerns)}"
        )
    concern_suffix = f"{concern_section}\n\n" if concern_section else ""
    return (
        f"{_STATIC_PROMPT_PREFIX}\n\n"
        "CURRENT REQUEST:\n"
        f"{query}\n\n"
        f"{concern_suffix}"
        "PLANNING EVIDENCE (guidance only; not answer evidence):\n"
        f"{planning_context}\n\n"
        "CONVERSATION CONTEXT (reference only; not obligations or answer evidence):\n"
        f"{conversation_context or '(none)'}\n\n"
        "REQUIRED OBLIGATIONS (derived only from the current request):\n"
        f"{_format_obligations(required_obligations)}"
        f"{retry_note}"
    )


def _safe_warning(exc: BaseException) -> str:
    if isinstance(exc, _DecompositionOutputError):
        return str(exc)
    return f"planner generation failed with {type(exc).__name__}"


def _failed_result(
    query: str,
    planning_evidence_ids: list[str],
    warning: str,
    *,
    required_obligations: list[RequiredObligation] | None = None,
    coverage: _CoverageState | None = None,
    repair_attempted: bool = False,
) -> DecompositionResult:
    required = required_obligations or []
    return DecompositionResult(
        request=query,
        tasks=[],
        planning_evidence_ids=planning_evidence_ids,
        status="FAILED",
        warnings=[warning],
        required_obligations=required,
        covered_obligations=list(coverage.covered_ids) if coverage else [],
        missing_obligations=(
            list(coverage.missing_ids)
            if coverage
            else [item.obligation_id for item in required]
        ),
        repair_attempted=repair_attempted,
        coverage_validation_reason=warning,
    )


async def decompose(
    provider,
    query: str,
    planning_context: str,
    metrics: RunMetrics,
    *,
    conversation_context: str = "",
) -> DecompositionResult:
    """Create a validated P-lite task plan from one bounded planning context.

    Only malformed structured output receives one repair attempt. Provider
    failures return a terminal failed result without exposing provider details.
    """

    if not isinstance(query, str) or not query.strip():
        safe_query = query if isinstance(query, str) else ""
        return _failed_result(safe_query, [], "request must be a non-empty string")
    if not isinstance(planning_context, str):
        return _failed_result(query, [], "planning context must be a string")
    if not isinstance(conversation_context, str):
        return _failed_result(query, [], "conversation context must be a string")

    request = query
    planning_evidence_ids = _extract_planning_evidence_ids(planning_context)
    required_obligations = _derive_required_obligations(request)
    explicit_concerns = _derive_explicit_concerns(request)
    system = _SYSTEM_PROMPT
    retry_reason: str | None = None
    previous_plan = ""
    coverage = _CoverageState(
        [],
        [item.obligation_id for item in required_obligations],
        "coverage not validated",
        missing_concern_ids=[item.concern_id for item in explicit_concerns],
    )

    for attempt in range(2):
        try:
            result = await _generate_structured(
                provider,
                system,
                _prompt(
                    request,
                    planning_context,
                    required_obligations,
                    conversation_context,
                    explicit_concerns,
                    retry_reason,
                    previous_plan,
                    coverage,
                ),
            )
            metrics.add_usage(result.usage)
            previous_plan = result.text if isinstance(result.text, str) else ""
            tasks = _parse_tasks(_extract_json(result.text))
            coverage = _validate_obligation_coverage(
                request,
                tasks,
                required_obligations,
                explicit_concerns,
            )
            return DecompositionResult(
                request=request,
                tasks=tasks,
                planning_evidence_ids=planning_evidence_ids,
                status="COMPLETE",
                warnings=[],
                required_obligations=required_obligations,
                covered_obligations=coverage.covered_ids,
                missing_obligations=[],
                repair_attempted=attempt > 0,
                coverage_validation_reason=coverage.reason,
            )
        except _CoverageValidationError as exc:
            coverage = exc.state
            retry_reason = _safe_warning(exc)
            if attempt == 1:
                return _failed_result(
                    request,
                    planning_evidence_ids,
                    retry_reason,
                    required_obligations=required_obligations,
                    coverage=coverage,
                    repair_attempted=True,
                )
        except _DecompositionOutputError as exc:
            retry_reason = _safe_warning(exc)
            if attempt == 1:
                return _failed_result(
                    request,
                    planning_evidence_ids,
                    retry_reason,
                    required_obligations=required_obligations,
                    coverage=coverage,
                    repair_attempted=True,
                )
        except Exception as exc:
            return _failed_result(
                request,
                planning_evidence_ids,
                _safe_warning(exc),
                required_obligations=required_obligations,
                coverage=coverage,
                repair_attempted=bool(retry_reason),
            )

    return _failed_result(
        request,
        planning_evidence_ids,
        "planner output could not be validated",
        required_obligations=required_obligations,
        coverage=coverage,
        repair_attempted=True,
    )


__all__ = ["DecompositionResult", "TaskItem", "decompose"]
