import type {
  RunEvent,
  RunMetrics,
  RunRecord,
  RunStatus,
  Task,
  TaskResult,
} from "../types/api";

type StringStatus = RunStatus | null;

export interface NormalizedUiTask {
  taskId: string;
  goal: string | null;
  domain: string | null;
  dependsOn: string[];
  evidenceNeeds: string[];
  status: StringStatus;
  answer: string | null;
  evidenceIds: string[];
  citations: string[];
  invalidCitations: string[];
  missingInformation: string[];
}

export interface UiTraceFailure {
  stage: string;
  errorType: string | null;
  hasDiagnostic: boolean;
}

export interface UiTraceSummary {
  eventCount: number;
  stages: string[];
  selectedEvidenceIds: string[];
  candidateEvidenceIds: string[];
  droppedEvidenceIds: string[];
  selectedCount: number;
  droppedCount: number;
  taskStatusCounts: Record<string, number>;
  terminalStatus: StringStatus;
  hasFailure: boolean;
  failure: UiTraceFailure | null;
  /** Ordered shallow copies retain timestamps and additive event fields. */
  events: RunEvent[];
}

export type UiRunStateKind = "COMPLETE" | "PARTIAL" | "NO_EVIDENCE" | "FAILED" | "UNKNOWN";

export interface UiRunState {
  kind: UiRunStateKind;
  isNoEvidence: boolean;
  isError: boolean;
  message: string;
}

export interface UiRunError {
  kind: "FAILED";
  message: string;
  errorType: string | null;
}

export interface UiResearchFlags {
  /** FakeProvider is a wiring/test double, never semantic or milestone evidence. */
  isFakeProvider: boolean;
  isWiringOnly: boolean;
  evidenceBoundary: "WIRING_ONLY" | "LOCAL_RUNTIME" | "UNCONFIRMED";
  /** UI normalization cannot establish either human quality score. */
  manualCorrectness: "UNSCORED";
  manualFaithfulness: "UNSCORED";
  /** A normalized UI record never promotes a run to milestone evidence. */
  isMilestoneEvidence: false;
  effectiveConfigFlags: Record<string, boolean>;
}

export interface NormalizedUiRun {
  runId: string;
  condition: string | null;
  status: RunStatus;
  answer: string;
  citations: string[];
  invalidCitations: string[];
  tasks: NormalizedUiTask[];
  /** These arrays only contain explicitly recorded additive fields. */
  agents: string[];
  roles: string[];
  metrics: RunMetrics | null;
  traceSummary: UiTraceSummary;
  /** Flattened unique values; task association remains in tasks[].missingInformation. */
  missingInformation: string[];
  state: UiRunState;
  error: UiRunError | null;
  researchFlags: UiResearchFlags;
  /** Original run object, including additive/unknown fields, for provenance. */
  raw: RunRecord;
}

interface TaskEntry {
  task?: Task;
  result?: TaskResult;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : null;
}

function asNonEmptyString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const normalized = value.trim();
  return normalized || null;
}

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];

  const values: string[] = [];
  for (const item of value) {
    const text = asNonEmptyString(item);
    if (text && !values.includes(text)) values.push(text);
  }
  return values;
}

function asBooleanFlags(value: unknown): Record<string, boolean> {
  const record = asRecord(value);
  if (!record) return {};

  const flags: Record<string, boolean> = {};
  for (const [name, flag] of Object.entries(record)) {
    if (typeof flag === "boolean") flags[name] = flag;
  }
  return flags;
}

function unique(values: string[]): string[] {
  return Array.from(new Set(values));
}

function statusValue(value: unknown): StringStatus {
  return asNonEmptyString(value) as StringStatus;
}

function recordRunResults(run: RunRecord, events: RunEvent[]): Map<string, TaskResult> {
  const results = new Map<string, TaskResult>();

  for (const result of run.task_results ?? []) {
    if (result && typeof result.task_id === "string") results.set(result.task_id, result);
  }

  // Older/persisted records may carry a result in the trace but not in the
  // top-level task_results list. Use it only as a fallback and never replace
  // the canonical top-level result.
  for (const event of events) {
    const result = event.result;
    if (result && typeof result.task_id === "string" && !results.has(result.task_id)) {
      results.set(result.task_id, result);
    }
  }

  return results;
}

function normalizeTasks(run: RunRecord, events: RunEvent[]): NormalizedUiTask[] {
  const entries = new Map<string, TaskEntry>();
  const results = recordRunResults(run, events);

  for (const task of run.tasks ?? []) {
    if (!task || typeof task.task_id !== "string") continue;
    entries.set(task.task_id, { task, result: results.get(task.task_id) });
  }

  for (const [taskId, result] of results) {
    if (!entries.has(taskId)) entries.set(taskId, { result });
  }

  return Array.from(entries, ([taskId, entry]) => {
    const task = entry.task;
    const result = entry.result;
    return {
      taskId,
      goal: asNonEmptyString(task?.goal),
      domain: asNonEmptyString(result?.domain ?? task?.domain),
      dependsOn: asStringList(task?.depends_on),
      evidenceNeeds: asStringList(task?.evidence_needs),
      status: statusValue(result?.status),
      answer: asNonEmptyString(result?.answer),
      evidenceIds: asStringList(result?.evidence_ids),
      citations: asStringList(result?.citations),
      invalidCitations: asStringList(result?.invalid_citations),
      missingInformation: asStringList(result?.missing_information),
    };
  });
}

function buildTraceSummary(run: RunRecord, events: RunEvent[], tasks: NormalizedUiTask[]): UiTraceSummary {
  const stages = events
    .map((event) => (typeof event.stage === "string" ? event.stage : ""))
    .filter((stage) => stage.length > 0);
  const selectedEvidenceIds = unique(events.flatMap((event) => asStringList(event.selected)));
  const candidateEvidenceIds = unique(events.flatMap((event) => asStringList(event.candidates)));
  const droppedEvidenceIds = unique(
    events.flatMap((event) =>
      (Array.isArray(event.dropped) ? event.dropped : [])
        .map((dropped) => asNonEmptyString(dropped?.chunk_id))
        .filter((chunkId): chunkId is string => Boolean(chunkId)),
    ),
  );
  const droppedCount = events.reduce(
    (count, event) => count + (Array.isArray(event.dropped) ? event.dropped.length : 0),
    0,
  );
  const taskStatusCounts: Record<string, number> = {};
  for (const task of tasks) {
    if (!task.status) continue;
    taskStatusCounts[task.status] = (taskStatusCounts[task.status] ?? 0) + 1;
  }

  let terminalStatus: StringStatus = null;
  for (const event of events) {
    const eventStatus = statusValue(event.status);
    if (eventStatus) terminalStatus = eventStatus;
    if (event.stage === "run_finished" || event.stage === "run_failed") {
      terminalStatus = eventStatus ?? terminalStatus;
    }
  }
  terminalStatus ??= statusValue(run.status);

  const failureEvent = [...events]
    .reverse()
    .find(
      (event) =>
        event.stage === "run_failed" ||
        typeof event.error_type === "string" ||
        typeof event.error === "string",
    );
  const failure = failureEvent
    ? {
        stage: failureEvent.stage,
        errorType: asNonEmptyString(failureEvent.error_type),
        hasDiagnostic: Boolean(asNonEmptyString(failureEvent.error)),
      }
    : null;

  return {
    eventCount: events.length,
    stages,
    selectedEvidenceIds,
    candidateEvidenceIds,
    droppedEvidenceIds,
    selectedCount: selectedEvidenceIds.length,
    droppedCount,
    taskStatusCounts,
    terminalStatus,
    hasFailure: failure !== null,
    failure,
    events: events.map((event) => ({ ...event })),
  };
}

function deriveState(status: RunStatus): UiRunState {
  const key = status.toUpperCase();
  switch (key) {
    case "COMPLETE":
      return {
        kind: "COMPLETE",
        isNoEvidence: false,
        isError: false,
        message: "Answer ready with validated evidence.",
      };
    case "PARTIAL":
      return {
        kind: "PARTIAL",
        isNoEvidence: false,
        isError: false,
        message: "Answer is partial; review missing information and citation validation.",
      };
    case "NO_EVIDENCE":
      return {
        kind: "NO_EVIDENCE",
        isNoEvidence: true,
        isError: false,
        message: "No validated answer-domain evidence was found.",
      };
    case "FAILED":
      return {
        kind: "FAILED",
        isNoEvidence: false,
        isError: true,
        message: "The run failed before a validated answer was produced.",
      };
    default:
      return {
        kind: "UNKNOWN",
        isNoEvidence: false,
        isError: false,
        message: "Run status received.",
      };
  }
}

function getExplicitLabels(run: RunRecord, key: "agents" | "roles"): string[] {
  const record = run as unknown as Record<string, unknown>;
  const aliases = key === "agents" ? ["agents", "agent_ids"] : ["roles", "role_profiles"];
  for (const alias of aliases) {
    const labels = asStringList(record[alias]);
    if (labels.length > 0) return labels;
  }
  return [];
}

function buildResearchFlags(run: RunRecord): UiResearchFlags {
  const provider = asNonEmptyString(run.provider)?.toLowerCase() ?? null;
  const isFakeProvider = provider === "fake";
  const evidenceBoundary = isFakeProvider
    ? "WIRING_ONLY"
    : provider === "ollama" || provider === "local"
      ? "LOCAL_RUNTIME"
      : "UNCONFIRMED";
  return {
    isFakeProvider,
    isWiringOnly: isFakeProvider,
    evidenceBoundary,
    manualCorrectness: "UNSCORED",
    manualFaithfulness: "UNSCORED",
    isMilestoneEvidence: false,
    effectiveConfigFlags: asBooleanFlags(run.effective_config?.flags),
  };
}

/**
 * Convert one persisted API run into the stable view-model boundary used by
 * redesigned UI surfaces. This function is deliberately read-only: `raw` and
 * trace event copies retain the backend record for provenance and unknown
 * additive fields are never turned into invented research claims.
 */
export function normalizeRun(run: RunRecord): NormalizedUiRun {
  const status = statusValue(run.status) ?? "UNKNOWN";
  const events = Array.isArray(run.events) ? run.events.filter(Boolean) : [];
  const tasks = normalizeTasks(run, events);
  const citations = unique(tasks.flatMap((task) => task.citations));
  const invalidCitations = unique(tasks.flatMap((task) => task.invalidCitations));
  const missingInformation = unique(tasks.flatMap((task) => task.missingInformation));
  const traceSummary = buildTraceSummary(run, events, tasks);
  const state = deriveState(status);
  const error = state.isError
    ? {
        kind: "FAILED" as const,
        message: state.message,
        errorType: traceSummary.failure?.errorType ?? null,
      }
    : null;

  return {
    runId: run.run_id,
    condition: asNonEmptyString(run.condition),
    status,
    answer: typeof run.answer === "string" ? run.answer : "",
    citations,
    invalidCitations,
    tasks,
    agents: getExplicitLabels(run, "agents"),
    roles: getExplicitLabels(run, "roles"),
    metrics: run.metrics ?? null,
    traceSummary,
    missingInformation,
    state,
    error,
    researchFlags: buildResearchFlags(run),
    raw: run,
  };
}
