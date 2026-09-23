import type {
  EffectiveConfig,
  RunEvent,
  RunMetrics,
  RunStatus,
  RunTraceResponse,
} from "../../types/api";

export interface TraceSnapshot {
  runId: string;
  status: RunStatus | null;
  events: RunEvent[];
  effectiveConfig: EffectiveConfig | null;
  metrics: RunMetrics;
  /** Original API response retained for additive fields and provenance. */
  raw: RunTraceResponse;
}

/**
 * Convert the trace endpoint's two compatibility aliases into one stable
 * frontend view without changing event order or dropping unknown fields.
 */
export function normalizeRunTrace(response: RunTraceResponse): TraceSnapshot {
  const events = response.events?.length ? response.events : response.trace ?? [];
  return {
    runId: response.run_id,
    status: response.status ?? null,
    events: events.map((event) => ({ ...event })),
    effectiveConfig: response.effective_config ?? null,
    metrics: response.metrics ?? {},
    raw: response,
  };
}
