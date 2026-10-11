export type RunStatus = "COMPLETE" | "PARTIAL" | "NO_EVIDENCE" | "FAILED" | string;

export interface HealthResponse {
  ok?: boolean;
  app?: string;
  version?: string;
  implementation_profile?: string;
  allowed_conditions?: string[];
  default_provider?: string;
  source_snapshot_id?: string;
  config_hash?: string;
}
export interface SourceSummary {
  source_id: string;
  source_name: string;
  chunk_count: number;
  /** Optional lifecycle state returned by richer source backends. */
  status?: string;
  index_status?: string;
  source_type?: string;
  source_format?: string;
}

export interface SourcesResponse {
  snapshot_id?: string;
  sources: SourceSummary[];
}

export interface SourceChunk {
  chunk_id: string;
  source_id: string;
  source_name: string;
  text: string;
  index: number;
  score?: number;
}

export interface SourceDetail {
  source_id: string;
  source_name: string;
  chunks: SourceChunk[];
  status?: string;
}

/**
 * Authenticated retrieval contract. The server resolves the owner from the
 * current local session; no client-supplied owner identifier is accepted.
 */
export interface OwnerScopedRetrievalClient {
  listSources: () => Promise<SourcesResponse>;
  getSource: (sourceId: string) => Promise<SourceDetail>;
  getChunk: (chunkId: string) => Promise<SourceChunk>;
  listRuns: () => Promise<RunListItem[]>;
  getRun: (runId: string) => Promise<RunRecord>;
}

export interface Task {
  task_id: string;
  goal: string;
  domain?: string;
  depends_on?: string[];
  evidence_needs?: string[];
}

export interface TaskResult {
  task_id: string;
  domain?: string;
  status?: RunStatus;
  answer?: string;
  evidence_ids?: string[];
  citations?: string[];
  invalid_citations?: string[];
  missing_information?: string[];
}

export interface DroppedEvidence {
  chunk_id?: string;
  reason?: string;
  estimated_tokens?: number;
}

export interface RunEvent {
  stage: string;
  ts?: string;
  task_id?: string;
  selected?: string[];
  dropped?: DroppedEvidence[];
  candidates?: string[];
  result?: TaskResult;
  [key: string]: unknown;
}

export interface RunMetrics {
  llm_calls?: number;
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  context_tokens_est?: number;
  retrieved_chunks?: number;
  selected_chunks?: number;
  dropped_chunks?: number;
  citations_emitted?: number;
  citations_valid?: number;
  citation_locator_validity?: number | null;
  latency_ms?: number;
  retrieval_latency_ms?: number;
  generation_latency_ms?: number;
  peak_rss_mb?: number | null;
  gpu_memory_mb?: number | null;
  [key: string]: number | string | null | undefined;
}

export interface EffectiveConfig {
  condition?: string;
  implementation_profile?: string;
  flags?: Record<string, boolean>;
  [key: string]: number | string | boolean | Record<string, boolean> | undefined;
}

export interface RunRecord {
  run_id: string;
  created_at?: string;
  condition?: string;
  implementation_profile?: string;
  provider?: string;
  model?: string;
  query?: string;
  status: RunStatus;
  answer?: string;
  source_snapshot_id?: string;
  config_hash?: string;
  tasks?: Task[];
  task_results?: TaskResult[];
  metrics?: RunMetrics;
  events?: RunEvent[];
  effective_config?: EffectiveConfig;
  error?: string;
}

export interface RunListItem {
  run_id: string;
  created_at?: string;
  condition?: string;
  query?: string;
  status?: RunStatus;
}

export interface SourceImportResult {
  source_id?: string;
  source_name?: string;
  chunks_added?: number;
  total_chunks_for_source?: number;
  snapshot_id?: string;
}
