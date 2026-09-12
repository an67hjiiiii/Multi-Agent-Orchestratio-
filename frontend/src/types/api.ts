export type KnownRunStatus = "COMPLETE" | "PARTIAL" | "NO_EVIDENCE" | "FAILED";
export type RunStatus = KnownRunStatus | (string & {});
export type EvidenceId = string;

export interface ApiErrorPayload {
  detail?: string;
  error?: string;
  code?: string;
  message?: string;
  retryable?: boolean;
}

export interface AuthUser {
  id: string;
  user_id: string;
  email?: string | null;
  username?: string | null;
  name?: string;
  display_name?: string;
  role: string;
  status?: string;
  created_at?: string | null;
  updated_at?: string | null;
  last_login_at?: string | null;
}

export interface AuthSessionResponse {
  authenticated: boolean;
  user?: AuthUser | null;
  session?: {
    session_id: string;
    user_id: string;
    created_at: string;
    expires_at: string;
  } | null;
  access_token?: string;
  token_type?: string;
}

export interface AuthRegisterRequest {
  email: string;
  name: string;
  password: string;
}

export interface AuthLoginRequest {
  identifier: string;
  password: string;
}

export interface HealthResponse {
  ok?: boolean;
  app?: string;
  version?: string;
  implementation_profile?: string;
  allowed_conditions?: string[];
  default_provider?: string;
  source_snapshot_id?: string;
  config_hash?: string;
  knowledge_base?: KnowledgeBaseStatus;
}

export interface RuntimeConfigResponse {
  implementation_profile?: string;
  provider?: string;
  local_model?: string;
  retrieval_mode?: "LEXICAL" | "VECTOR" | "HYBRID" | string;
  vector_backend?: string | null;
  local_embedding_model?: string | null;
  allowed_conditions?: string[];
  config_hash?: string;
}

export interface SourceSummary {
  source_id: string;
  source_name: string;
  chunk_count: number;
  source_type?: string | null;
  source_format?: string | null;
  index_status?: string | null;
}

export interface SourcesResponse {
  snapshot_id: string;
  sources: SourceSummary[];
}

export interface KnowledgeBaseStatus {
  status: "EMPTY" | "READY" | "FAILED" | "UNAVAILABLE" | (string & {});
  backend: string;
  retrieval_backend?: string;
  retrieval_mode?: "LEXICAL" | "VECTOR" | "HYBRID" | string;
  embedding_version?: string | null;
  vector_indexed_chunks?: number;
  index_identity?: unknown;
  index_status?: string;
  source_count: number;
  chunk_count: number;
  snapshot_id: string;
  availability_error?: string | null;
}

export interface SourceChunk {
  chunk_id: string;
  source_id: string;
  source_name: string;
  text: string;
  index: number;
  score?: number;
  provenance?: Record<string, unknown>;
}

export interface SourceDetail {
  source_id: string;
  source_name: string;
  chunks: SourceChunk[];
}

export interface SourceTextRequest {
  source_name: string;
  text: string;
}

export interface PlanningRetrievalResult {
  request?: string;
  item_ids: string[];
  scores?: Array<number | null> | null;
  context?: string | null;
}

export interface DecompositionTask {
  task_id: string;
  title: string;
  objective: string;
  expected_output: string;
  domain: string;
  role_profile: string;
  depends_on: string[];
}

export interface DecompositionResult {
  request: string;
  tasks: DecompositionTask[];
  planning_evidence_ids: string[];
  status: string;
  warnings: string[];
}

export interface PLiteInspectionResponse extends DecompositionResult {
  planning?: PlanningRetrievalResult | null;
  planning_context?: string | null;
  latency_ms?: number;
  llm_calls?: number;
  metrics?: RunMetrics;
}

export interface DecompositionRequest {
  request: string;
  provider?: string | null;
}

export interface Task {
  task_id: string;
  goal: string;
  domain?: string;
  /** Optional additive labels returned by richer research profiles. */
  role_profile?: string;
  role?: string;
  agent?: string;
  agent_id?: string;
  depends_on?: string[];
  evidence_needs?: string[];
}

export interface TaskResult {
  task_id: string;
  domain?: string;
  /** Optional additive labels; older run records omit these fields. */
  role_profile?: string;
  role?: string;
  agent?: string;
  agent_id?: string;
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
  selected?: EvidenceId[];
  dropped?: DroppedEvidence[];
  candidates?: EvidenceId[];
  result?: TaskResult;
  status?: RunStatus;
  error_type?: string;
  error?: string;
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
  /** Optional additive labels used by richer research/demo run records. */
  agents?: string[];
  agent_ids?: string[];
  roles?: string[];
  role_profiles?: string[];
  source_snapshot_id?: string;
  config_hash?: string;
  tasks?: Task[];
  task_results?: TaskResult[];
  metrics?: RunMetrics;
  events?: RunEvent[];
  effective_config?: EffectiveConfig;
  error?: string;
}

export interface ChatRequest {
  message: string;
  condition: string;
  provider?: string | null;
}

export interface RunListItem {
  run_id: string;
  created_at?: string;
  condition?: string;
  query?: string;
  status?: RunStatus;
}

export interface SourceImportResult {
  source_id: string;
  source_name: string;
  chunks_added: number;
  total_chunks_for_source: number;
  snapshot_id: string;
  retrieval_backend?: string;
  embedding_version?: string | null;
  vector_indexed_chunks?: number;
  source_type?: string | null;
  source_format?: string | null;
  index_status?: string | null;
}
