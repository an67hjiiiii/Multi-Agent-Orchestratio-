import type { RunEvidenceResponse, SourceChunk } from "../../types/api";

export interface EvidenceSnapshot {
  runId: string;
  sourceSnapshotId: string | null;
  evidenceIds: string[];
  items: SourceChunk[];
  missingIds: string[];
  /** Original API response retained for additive fields and provenance. */
  raw: RunEvidenceResponse;
}

/**
 * Convert the evidence endpoint's two item aliases into one stable frontend
 * view while preserving canonical IDs and unresolved locator state.
 */
export function normalizeRunEvidence(response: RunEvidenceResponse): EvidenceSnapshot {
  const items = response.items?.length ? response.items : response.evidence ?? [];
  return {
    runId: response.run_id,
    sourceSnapshotId: response.source_snapshot_id ?? null,
    evidenceIds: [...(response.evidence_ids ?? [])],
    items: items.map((item) => ({ ...item })),
    missingIds: [...(response.missing_ids ?? [])],
    raw: response,
  };
}
