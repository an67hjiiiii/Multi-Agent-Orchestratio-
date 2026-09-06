export type PlanningEvidenceState = "AVAILABLE" | "WEAK" | "NO_EVIDENCE";

/** The frontend shape of the locked Sprint 3 PlanningRetrievalResult contract. */
export interface PlanningRetrievalResult {
  item_ids: readonly string[];
  scores?: readonly (number | null)[] | null;
  context?: string | null;
}

export interface PlanningEvidencePanelProps {
  result?: PlanningRetrievalResult | null;
}

const stateLabels: Record<PlanningEvidenceState, string> = {
  AVAILABLE: "Planning evidence available",
  WEAK: "Weak planning evidence",
  NO_EVIDENCE: "No planning evidence",
};

const stateTones: Record<PlanningEvidenceState, string> = {
  AVAILABLE: "complete",
  WEAK: "partial",
  NO_EVIDENCE: "no-evidence",
};

function evidenceIds(result: PlanningRetrievalResult | null | undefined): string[] {
  return Array.from(new Set((result?.item_ids ?? []).filter((id) => id.trim().length > 0)));
}

function hasBoundedContext(result: PlanningRetrievalResult | null | undefined): boolean {
  return Boolean(result?.context?.trim());
}

export function getPlanningEvidenceState(
  result: PlanningRetrievalResult | null | undefined,
): PlanningEvidenceState {
  const ids = evidenceIds(result);
  if (ids.length === 0) return "NO_EVIDENCE";

  // P-lite has no UI score threshold; missing bounded context is the observable weak state.
  return hasBoundedContext(result) ? "AVAILABLE" : "WEAK";
}

export function formatPlanningScore(score: number | null | undefined): string {
  return typeof score === "number" && Number.isFinite(score) ? score.toFixed(3) : "—";
}

function PlanningStateBadge({ state }: { state: PlanningEvidenceState }) {
  return (
    <span
      className={`status-badge status-${stateTones[state]}`}
      role="status"
      aria-label={`Planning evidence state: ${stateLabels[state]}`}
    >
      <span className="status-dot" aria-hidden="true" />
      {stateLabels[state]}
    </span>
  );
}

function PlanningScores({
  ids,
  scores,
}: {
  ids: string[];
  scores?: readonly (number | null)[] | null;
}) {
  const supplied = Boolean(scores?.length);

  return (
    <>
      <div className="evidence-row">
        <span>Retrieval scores</span>
        <strong>{ids.length === 0 ? "No IDs" : supplied ? "Supplied" : "Not supplied"}</strong>
      </div>
      {ids.length > 0 && supplied && (
        <div role="list" aria-label="Planning retrieval scores">
          {ids.map((id, index) => (
            <div className="evidence-row" role="listitem" key={`${id}-${index}`}>
              <code className="evidence-id">{id}</code>
              <strong>{formatPlanningScore(scores?.[index])}</strong>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export function PlanningEvidencePanel({ result = null }: PlanningEvidencePanelProps) {
  const ids = evidenceIds(result);
  const state = getPlanningEvidenceState(result);
  const contextAvailable = hasBoundedContext(result);

  return (
    <section className="evidence-card planning-evidence-panel" aria-label="Planning evidence">
      <div className="evidence-card-heading">
        <span>Planning evidence</span>
        <span className="evidence-stage">P-lite · planning only</span>
      </div>

      <div className="evidence-row">
        <span>Planning retrieval state</span>
        <PlanningStateBadge state={state} />
      </div>

      <p className="run-metrics-empty">
        Planning evidence guides decomposition only and is distinct from answer-domain evidence.
      </p>

      <div className="evidence-row">
        <span>Planning evidence IDs</span>
        <strong>{ids.length}</strong>
      </div>
      {ids.length > 0 ? (
        <div role="list" aria-label="Planning evidence IDs">
          {ids.map((id) => (
            <code className="evidence-id" role="listitem" key={id}>{id}</code>
          ))}
        </div>
      ) : (
        <p className="run-metrics-empty">No planning evidence IDs were returned.</p>
      )}

      <PlanningScores ids={ids} scores={result?.scores} />

      <div className="evidence-row">
        <span>Bounded planning context</span>
        <strong>{contextAvailable ? "Available" : "Not available"}</strong>
      </div>
      {state === "WEAK" && (
        <p className="run-metrics-empty">
          Retrieved IDs are present, but the bounded planning context is unavailable.
        </p>
      )}
      {state === "NO_EVIDENCE" && (
        <p className="run-metrics-empty">
          No planning guidance was retrieved for this decomposition.
        </p>
      )}
    </section>
  );
}
