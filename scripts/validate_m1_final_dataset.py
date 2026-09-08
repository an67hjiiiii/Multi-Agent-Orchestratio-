"""Static readiness validation for the frozen M1 final scenario dataset.

This module reads only readiness artifacts and frozen corpus metadata. It does
not call Ollama, execute the pilot runner, or import scenario gold into any
generation module.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

# Direct execution places ``scripts`` (rather than the repository root) on
# sys.path. Add the root so the existing static isolation guard is importable.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.evaluation.gold_isolation import verify_gold_isolation


REQUEST_PATH = Path("datasets/final/final_benchmark_v1.json")
GOLD_PATH = Path("datasets/final/final_gold_v1.json")
DEV_PATH = Path("datasets/pilot/m1_dev_cases.json")
CORPUS_MANIFEST_PATH = Path("reports/pre_pilot_freeze/corpus-manifest.json")
EVIDENCE_MANIFEST_PATH = Path("reports/final_experiment/corpus-evidence-manifest.json")
PACKET_MANIFEST_PATH = Path("reports/final_experiment/manifest.json")
PACKET_CSV_PATH = Path("reports/final_experiment/scenario-gold-template.csv")

ALLOWED_DOMAINS = frozenset({"security", "database", "api_architecture"})
ROLE_BY_DOMAIN = {
    "security": "Security Analyst",
    "database": "Database Analyst",
    "api_architecture": "API/Architecture Analyst",
}
ALLOWED_ROLES = frozenset(ROLE_BY_DOMAIN.values())
PENDING = "PENDING_HUMAN_APPROVAL"
GROUP_PATTERN = re.compile(r"^M1F-S(?:0[1-9]|[12][0-9]|30)$")
GOLD_PATTERN = re.compile(r"^M1F-G(?:0[1-9]|[12][0-9]|30)$")
VARIANT_PATTERN = re.compile(r"^M1F-S(?:0[1-9]|[12][0-9]|30)-V0[1-4]$")
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# These markers must not occur in app/research or app/providers generation
# sources. The readiness artifacts remain outside the generation path.
RUNTIME_GOLD_MARKERS = (
    "m1_final_frozen_requests",
    "m1_final_scenario_gold",
    "m1_final_approval_packet",
    "m1-final-scenario-gold-v1",
    "scenario-gold-template.csv",
    "PENDING_HUMAN_APPROVAL",
    "scenario_gold_id",
    "expected_answer_points",
    "gold_obligation_id",
    "relevant_evidence_ids",
)


def _load_json(root: Path, relative: Path, errors: list[str]) -> Any:
    path = root / relative
    if not path.is_file():
        errors.append(f"missing JSON artifact: {relative.as_posix()}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid JSON {relative.as_posix()}: {exc}")
        return None


def _tokens(value: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(value.lower()))


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _expected_group_ids() -> set[str]:
    return {f"M1F-S{i:02d}" for i in range(1, 31)}


def _expected_gold_ids() -> set[str]:
    return {f"M1F-G{i:02d}" for i in range(1, 31)}


def _validate_corpus_metadata(
    request_data: dict[str, Any],
    evidence_data: dict[str, Any],
    corpus_data: dict[str, Any] | None,
    errors: list[str],
) -> set[str]:
    expected_chunks: set[str] = set()
    snapshot = request_data.get("corpus_snapshot")
    if not isinstance(snapshot, dict):
        errors.append("requests.corpus_snapshot must be an object")
        return expected_chunks
    if snapshot.get("snapshot_id") != "m1-pilot-authorized-v1":
        errors.append("requests.corpus_snapshot.snapshot_id is not the authorized snapshot")
    if snapshot.get("evidence_manifest_path") != EVIDENCE_MANIFEST_PATH.as_posix():
        errors.append("requests.corpus_snapshot.evidence_manifest_path is not canonical")
    if evidence_data.get("snapshot_id") != snapshot.get("snapshot_id"):
        errors.append("evidence manifest snapshot_id does not match requests")
    if not isinstance(corpus_data, dict):
        errors.append("corpus manifest must be an object")
        return expected_chunks

    corpus_items = corpus_data.get("items")
    if not isinstance(corpus_items, list) or len(corpus_items) != 1:
        errors.append("corpus manifest must contain exactly one frozen source item")
    else:
        item = corpus_items[0]
        if item.get("path") != "data/m1-pilot-authorized-v1/sources.json":
            errors.append("corpus manifest source path is unexpected")
        if item.get("sha256") != snapshot.get("source_manifest_sha256"):
            errors.append("source manifest SHA-256 does not match corpus manifest")
        if item.get("chunk_count") != 3:
            errors.append("authorized corpus chunk_count must remain 3")

    if evidence_data.get("source_manifest_sha256") != snapshot.get("source_manifest_sha256"):
        errors.append("evidence manifest source SHA-256 does not match requests")
    chunks = evidence_data.get("chunks")
    if not isinstance(chunks, list) or len(chunks) != 3:
        errors.append("evidence manifest must contain exactly three chunk records")
        chunks = []
    for item in chunks:
        if not isinstance(item, dict):
            errors.append("evidence manifest chunk record must be an object")
            continue
        chunk_id = item.get("chunk_id")
        source_id = item.get("source_id")
        if not isinstance(chunk_id, str) or not chunk_id:
            errors.append("evidence manifest has an empty chunk_id")
            continue
        if not isinstance(source_id, str) or not source_id:
            errors.append(f"evidence manifest chunk {chunk_id!r} has no source_id")
        if chunk_id in expected_chunks:
            errors.append(f"duplicate corpus chunk_id: {chunk_id}")
        expected_chunks.add(chunk_id)
    return expected_chunks


def _validate_requests(
    data: dict[str, Any],
    dev_data: dict[str, Any],
    evidence_ids: set[str],
    errors: list[str],
) -> tuple[set[str], set[str], int]:
    if not isinstance(data, dict):
        errors.append("request manifest must be an object")
        return set(), set(), 0
    if data.get("schema_version") != "m1-final-frozen-requests-v1":
        errors.append("unexpected request schema_version")
    if data.get("dataset_id") != "m1-final-experiment-v1":
        errors.append("unexpected request dataset_id")
    if data.get("status") != "FROZEN_PENDING_HUMAN_APPROVAL":
        errors.append("request manifest must remain frozen and pending approval")
    if data.get("frozen_before_execution") is not True:
        errors.append("request manifest must declare frozen_before_execution=true")
    if data.get("source_development_dataset") != DEV_PATH.as_posix():
        errors.append("request manifest must identify the development exclusion set")
    policy = data.get("holdout_policy")
    if not isinstance(policy, dict):
        errors.append("holdout_policy is missing")
    if data.get("variant_labels") != ["V01", "V02", "V03", "V04"]:
        errors.append("variant_labels must be V01..V04")
    groups = data.get("scenario_groups")
    if not isinstance(groups, list):
        errors.append("scenario_groups must be a list")
        return set(), set(), 0
    if len(groups) != 30:
        errors.append(f"expected 30 scenario groups, found {len(groups)}")

    dev_queries = []
    if isinstance(dev_data, dict) and isinstance(dev_data.get("cases"), list):
        dev_queries = [
            (item.get("id"), item.get("query"))
            for item in dev_data["cases"]
            if isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and isinstance(item.get("query"), str)
        ]
        if len(dev_queries) != 15:
            errors.append(f"development exclusion set must contain 15 cases, found {len(dev_queries)}")
    else:
        errors.append("development exclusion set is not readable")
    dev_tokens = [(case_id, _tokens(query)) for case_id, query in dev_queries]

    group_ids: set[str] = set()
    case_ids: set[str] = set()
    request_texts: set[str] = set()
    holdout_bases: set[str] = set()
    total_requests = 0
    for group in groups:
        if not isinstance(group, dict):
            errors.append("each scenario group must be an object")
            continue
        group_id = group.get("scenario_group_id")
        if not isinstance(group_id, str) or not GROUP_PATTERN.fullmatch(group_id):
            errors.append(f"invalid scenario_group_id: {group_id!r}")
        elif group_id in group_ids:
            errors.append(f"duplicate scenario_group_id: {group_id}")
        else:
            group_ids.add(group_id)

        domain = group.get("canonical_domain")
        role = group.get("role_profile")
        if domain not in ALLOWED_DOMAINS:
            errors.append(f"{group_id}: unapproved canonical_domain {domain!r}")
        if role not in ALLOWED_ROLES:
            errors.append(f"{group_id}: unapproved role_profile {role!r}")
        if ROLE_BY_DOMAIN.get(domain) != role:
            errors.append(f"{group_id}: role_profile does not match canonical_domain")

        holdout = group.get("holdout_basis")
        if not isinstance(holdout, str) or not holdout:
            errors.append(f"{group_id}: holdout_basis is required")
        elif holdout in holdout_bases:
            errors.append(f"duplicate holdout_basis: {holdout}")
        else:
            holdout_bases.add(holdout)
        provenance = group.get("provenance")
        if not isinstance(provenance, dict) or provenance.get("development_overlap") != (
            "NONE_BY_EXACT_TEXT_CHECK; SEMANTIC_REVIEW_REQUIRED"
        ):
            errors.append(f"{group_id}: missing explicit development-overlap boundary")
            provenance = provenance if isinstance(provenance, dict) else {}

        expectation = group.get("evidence_expectation")
        source_refs = provenance.get("source_evidence_ids")
        if not isinstance(source_refs, list):
            errors.append(f"{group_id}: provenance.source_evidence_ids must be a list")
            source_refs = []
        if any(ref not in evidence_ids for ref in source_refs):
            errors.append(f"{group_id}: provenance references an unknown corpus chunk")
        if expectation == "EVIDENCE_PRESENT" and not source_refs:
            errors.append(f"{group_id}: evidence-present group has no corpus refs")
        if expectation == "NO_EVIDENCE" and source_refs:
            errors.append(f"{group_id}: no-evidence group must have no corpus refs")

        variants = group.get("variants")
        if not isinstance(variants, list) or len(variants) != 4:
            errors.append(f"{group_id}: expected exactly four variants")
            variants = []
        variant_ids: set[str] = set()
        variant_orders: set[int] = set()
        for variant in variants:
            if not isinstance(variant, dict):
                errors.append(f"{group_id}: variant must be an object")
                continue
            case_id = variant.get("case_id")
            variant_id = variant.get("variant_id")
            request_text = variant.get("request_text")
            if not isinstance(case_id, str) or not VARIANT_PATTERN.fullmatch(case_id):
                errors.append(f"{group_id}: invalid case_id {case_id!r}")
            elif case_id in case_ids:
                errors.append(f"duplicate case_id: {case_id}")
            else:
                case_ids.add(case_id)
            if not isinstance(variant_id, str) or variant_id not in {"V01", "V02", "V03", "V04"}:
                errors.append(f"{group_id}: invalid variant_id {variant_id!r}")
            elif variant_id in variant_ids:
                errors.append(f"{group_id}: duplicate variant_id {variant_id}")
            else:
                variant_ids.add(variant_id)
            variant_order = variant.get("variant_order")
            if not isinstance(variant_order, int) or variant_order not in {1, 2, 3, 4}:
                errors.append(f"{group_id}: invalid variant_order {variant_order!r}")
            elif variant_order in variant_orders:
                errors.append(f"{group_id}: duplicate variant_order {variant_order}")
            else:
                variant_orders.add(variant_order)
            if isinstance(case_id, str) and isinstance(variant_id, str):
                if not case_id.startswith(f"{group_id}-{variant_id}"):
                    errors.append(f"{group_id}: case_id and variant_id disagree")
            if not isinstance(request_text, str) or len(request_text.strip()) < 20:
                errors.append(f"{group_id}: request_text is empty or too short")
                continue
            normalized = " ".join(request_text.lower().split())
            if normalized in request_texts:
                errors.append(f"{case_id}: duplicate frozen request text")
            request_texts.add(normalized)
            for dev_id, dev_query in dev_queries:
                if normalized == " ".join(dev_query.lower().split()):
                    errors.append(f"{case_id}: exact request reuse from {dev_id}")
            tokens = _tokens(request_text)
            for dev_id, old_tokens in dev_tokens:
                if _jaccard(tokens, old_tokens) >= 0.80:
                    errors.append(f"{case_id}: near-text overlap with development case {dev_id}")
            variant_provenance = variant.get("provenance")
            if not isinstance(variant_provenance, dict):
                errors.append(f"{case_id}: variant provenance is missing")
            else:
                if variant_provenance.get("scenario_group_id") != group_id:
                    errors.append(f"{case_id}: provenance group mismatch")
                refs = variant_provenance.get("source_evidence_ids")
                if refs != source_refs:
                    errors.append(f"{case_id}: variant refs must match its group refs")
                if any(ref not in evidence_ids for ref in refs or []):
                    errors.append(f"{case_id}: variant references an unknown corpus chunk")
            total_requests += 1
        if variant_ids != {"V01", "V02", "V03", "V04"}:
            errors.append(f"{group_id}: variants must contain exactly V01..V04")
        if variant_orders != {1, 2, 3, 4}:
            errors.append(f"{group_id}: variant_order must contain exactly 1..4")

    if group_ids != _expected_group_ids():
        errors.append("scenario_group_id set is not exactly M1F-S01..M1F-S30")
    if len(case_ids) != 120:
        errors.append(f"expected 120 unique case IDs, found {len(case_ids)}")
    if total_requests != 120:
        errors.append(f"expected 120 frozen requests, found {total_requests}")
    if data.get("scenario_group_count") != 30 or data.get("request_count") != 120:
        errors.append("request count declarations do not match 30 groups × 4 variants")
    return group_ids, case_ids, total_requests


def _validate_gold(
    data: dict[str, Any],
    group_ids: set[str],
    evidence_ids: set[str],
    errors: list[str],
) -> set[str]:
    if not isinstance(data, dict):
        errors.append("gold manifest must be an object")
        return set()
    if data.get("schema_version") != "m1-final-scenario-gold-v1":
        errors.append("unexpected scenario gold schema_version")
    if data.get("gold_granularity") != "SCENARIO":
        errors.append("gold granularity must be SCENARIO")
    if data.get("case_level_annotations") is not False:
        errors.append("gold must explicitly disable case-level annotations")
    if data.get("status") != PENDING:
        errors.append("scenario gold must remain PENDING_HUMAN_APPROVAL")
    gold_snapshot = data.get("corpus_snapshot")
    if isinstance(gold_snapshot, dict) and gold_snapshot.get("evidence_manifest_path") != EVIDENCE_MANIFEST_PATH.as_posix():
        errors.append("gold corpus_snapshot.evidence_manifest_path is not canonical")
    rows = data.get("scenario_gold")
    if not isinstance(rows, list) or len(rows) != 30:
        errors.append("scenario gold must contain exactly 30 rows")
        rows = []
    gold_ids: set[str] = set()
    forbidden = {
        "gold_obligation_id",
        "obligation_id",
        "task_id",
        "case_id",
        "variant_id",
        "gold_task_or_obligation",
        "task_annotations",
    }
    expected_keys = {
        "scenario_gold_id",
        "scenario_group_id",
        "scenario_label",
        "expected_role",
        "expected_domain",
        "relevant_evidence_ids",
        "expected_answer_points",
        "expected_missing_information",
        "dependency_expectation",
        "overlap_expectation",
        "reviewer_status",
        "reviewer_id_or_initials",
        "reviewer_notes",
        "approved_at",
    }
    for row in rows:
        if not isinstance(row, dict):
            errors.append("each scenario gold row must be an object")
            continue
        if set(row) != expected_keys:
            errors.append(
                f"{row.get('scenario_group_id', '<unknown>')}: scenario gold keys must be scenario-level only"
            )
        if forbidden.intersection(row):
            errors.append(f"{row.get('scenario_group_id', '<unknown>')}: per-case/task gold field found")
        gold_id = row.get("scenario_gold_id")
        group_id = row.get("scenario_group_id")
        if not isinstance(gold_id, str) or not GOLD_PATTERN.fullmatch(gold_id):
            errors.append(f"invalid scenario_gold_id: {gold_id!r}")
        elif gold_id in gold_ids:
            errors.append(f"duplicate scenario_gold_id: {gold_id}")
        else:
            gold_ids.add(gold_id)
        if group_id not in group_ids:
            errors.append(f"{gold_id}: gold references unknown scenario group {group_id!r}")
        if row.get("expected_domain") not in ALLOWED_DOMAINS:
            errors.append(f"{gold_id}: unapproved expected_domain")
        if ROLE_BY_DOMAIN.get(row.get("expected_domain")) != row.get("expected_role"):
            errors.append(f"{gold_id}: expected role/domain mismatch")
        refs = row.get("relevant_evidence_ids")
        if not isinstance(refs, list) or any(ref not in evidence_ids for ref in refs):
            errors.append(f"{gold_id}: gold evidence ref does not resolve in corpus manifest")
        missing = row.get("expected_missing_information")
        if not isinstance(missing, str) or not missing.strip():
            if refs == []:
                errors.append(f"{gold_id}: empty evidence requires expected_missing_information")
        elif refs:
            errors.append(f"{gold_id}: evidence-present gold must not claim missing evidence")
        points = row.get("expected_answer_points")
        if not isinstance(points, list) or not points or not all(
            isinstance(point, str) and point.strip() for point in points
        ):
            errors.append(f"{gold_id}: expected_answer_points must be a non-empty scenario-level list")
        if row.get("reviewer_status") != PENDING:
            errors.append(f"{gold_id}: reviewer_status must remain pending")
        if (
            row.get("reviewer_id_or_initials") != ""
            or row.get("reviewer_notes") != ""
            or row.get("approved_at") is not None
        ):
            errors.append(f"{gold_id}: Human approval fields must remain blank")
    if gold_ids != _expected_gold_ids():
        errors.append("scenario_gold_id set is not exactly M1F-G01..M1F-G30")
    return gold_ids


def _validate_packet(
    root: Path,
    gold_ids: set[str],
    group_ids: set[str],
    errors: list[str],
) -> None:
    packet = _load_json(root, PACKET_MANIFEST_PATH, errors)
    if isinstance(packet, dict):
        if packet.get("readiness_status") != PENDING:
            errors.append("approval packet readiness_status must remain pending")
        if packet.get("execution_status") != "NOT_RUN":
            errors.append("approval packet execution_status must remain NOT_RUN")
        if packet.get("scenario_group_count") != 30 or packet.get("frozen_request_count") != 120:
            errors.append("approval packet count declarations are incorrect")
        if packet.get("gold_granularity") != "SCENARIO" or packet.get("gold_row_count") != 30:
            errors.append("approval packet must declare scenario-level gold with 30 rows")
        if packet.get("reviewer_fields_blank") is not True or packet.get("self_approval") is not False:
            errors.append("approval packet must declare blank Human fields and no self-approval")
        declared_files = packet.get("artifact_files")
        required_files = {
            REQUEST_PATH.as_posix(),
            GOLD_PATH.as_posix(),
            PACKET_CSV_PATH.as_posix(),
            EVIDENCE_MANIFEST_PATH.as_posix(),
            Path("reports/final_experiment/final_dataset_approval.md").as_posix(),
            Path("reports/final_experiment/human-review-checklist.md").as_posix(),
        }
        if not isinstance(declared_files, list) or not required_files.issubset(declared_files):
            errors.append("approval packet manifest does not declare canonical artifact paths")
        for relative in required_files:
            if not (root / relative).is_file():
                errors.append(f"approval packet artifact is missing: {relative}")
    csv_path = root / PACKET_CSV_PATH
    if not csv_path.is_file():
        errors.append(f"missing approval CSV: {PACKET_CSV_PATH.as_posix()}")
        return
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, csv.Error) as exc:
        errors.append(f"invalid approval CSV: {exc}")
        return
    if len(rows) != 30:
        errors.append(f"approval CSV must contain 30 rows, found {len(rows)}")
    seen_groups: set[str] = set()
    for row in rows:
        group_id = row.get("scenario_group_id", "")
        gold_id = row.get("scenario_gold_id", "")
        seen_groups.add(group_id)
        if gold_id not in gold_ids or group_id not in group_ids:
            errors.append(f"approval CSV has unknown gold/group ID: {gold_id}/{group_id}")
        case_ids = [value for value in row.get("variant_case_ids", "").split(";") if value]
        if len(case_ids) != 4 or len(set(case_ids)) != 4:
            errors.append(f"{group_id}: approval CSV must list four unique variants")
        if row.get("reviewer_status") != PENDING:
            errors.append(f"{group_id}: approval CSV reviewer status must remain pending")
        if row.get("reviewer_id_or_initials") or row.get("reviewer_notes") or row.get("approved_at"):
            errors.append(f"{group_id}: approval CSV Human fields must remain blank")
    if seen_groups != group_ids:
        errors.append("approval CSV group coverage does not match frozen request groups")


def _validate_runtime_isolation(root: Path, errors: list[str]) -> dict[str, Any]:
    existing_guard = verify_gold_isolation(root)
    if existing_guard.get("decision") != "PASS":
        errors.append("existing generation gold isolation guard is not PASS")
    generation_files: list[str] = []
    source_markers: list[dict[str, str]] = []
    for relative_root in (Path("app/research"), Path("app/providers")):
        directory = root / relative_root
        if not directory.is_dir():
            errors.append(f"missing generation source directory: {relative_root.as_posix()}")
            continue
        for path in sorted(directory.rglob("*.py")):
            relative = path.relative_to(root).as_posix()
            generation_files.append(relative)
            text = path.read_text(encoding="utf-8")
            for marker in RUNTIME_GOLD_MARKERS:
                if marker in text:
                    source_markers.append({"path": relative, "marker": marker})
    if source_markers:
        errors.append("final scenario gold/request artifact markers occur in generation source")
    return {
        "existing_guard_decision": existing_guard.get("decision"),
        "generation_files_scanned": len(generation_files),
        "marker_hits": source_markers,
        "scope": "static source scan only; no runtime generation was executed",
    }


def validate(root: Path | None = None) -> dict[str, Any]:
    """Validate all final readiness artifacts without model/provider execution."""

    root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    errors: list[str] = []
    requests = _load_json(root, REQUEST_PATH, errors)
    gold = _load_json(root, GOLD_PATH, errors)
    dev = _load_json(root, DEV_PATH, errors)
    evidence = _load_json(root, EVIDENCE_MANIFEST_PATH, errors)
    corpus = _load_json(root, CORPUS_MANIFEST_PATH, errors)
    if not isinstance(requests, dict):
        requests = {}
    if not isinstance(gold, dict):
        gold = {}
    if not isinstance(dev, dict):
        dev = {}
    if not isinstance(evidence, dict):
        evidence = {}
    evidence_ids = _validate_corpus_metadata(requests, evidence, corpus, errors)
    group_ids, case_ids, request_count = _validate_requests(requests, dev, evidence_ids, errors)
    gold_ids = _validate_gold(gold, group_ids, evidence_ids, errors)
    _validate_packet(root, gold_ids, group_ids, errors)
    isolation = _validate_runtime_isolation(root, errors)
    return {
        "decision": "PASS" if not errors else "FAIL",
        "dataset_id": requests.get("dataset_id"),
        "scenario_group_count": len(group_ids),
        "frozen_request_count": request_count,
        "scenario_gold_count": len(gold_ids),
        "approval_status": gold.get("status"),
        "human_approval_blocker": PENDING,
        "static_checks": [
            "schema_counts_and_ids",
            "development_exact_and_near_text_exclusion",
            "corpus_evidence_references",
            "role_domain_vocabulary",
            "scenario_level_gold_only",
            "approval_packet_blank_human_fields",
            "generation_source_gold_isolation",
        ],
        "runtime_isolation": isolation,
        "errors": errors,
    }


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["decision"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
