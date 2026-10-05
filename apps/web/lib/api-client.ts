/**
 * Typed client for the Drake hosted read API (`/api/v1`).
 *
 * One place owns: the base URL, URL normalisation, request headers, error
 * shape, the response types, and one fetch helper per read route. The API
 * contract lives in `services/api/src/hosted_api/routers/` — keep the types
 * here in step with those response models.
 */

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

/**
 * Base URL of the hosted read API.
 *
 * Read at call time (not module load) so a stubbed or late-bound
 * `NEXT_PUBLIC_API_URL` is honoured, and trailing slashes never produce a
 * double slash in request paths.
 */
export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  const base = configured && configured.length > 0 ? configured : DEFAULT_API_BASE_URL;
  return base.replace(/\/+$/, "");
}

/** Absolute URL for a route path, with or without a leading slash. */
export function apiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${getApiBaseUrl()}${normalized}`;
}

/**
 * GET a JSON route. Throws `API request failed: <status> <path>` on a
 * non-OK response so callers (and react-query error states) see the route.
 */
export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const { headers: initHeaders, ...rest } = init ?? {};
  const headers = new Headers(initHeaders);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  const response = await fetch(apiUrl(path), { ...rest, headers });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${path}`);
  }

  return (await response.json()) as T;
}

function encodePathSegment(value: string): string {
  return encodeURIComponent(value);
}

/* ------------------------------------------------------------------ types */

export interface PortfolioSummary {
  global_fanout_limit: number;
  same_repo_max_when_others_idle?: number | null;
  repo_count: number;
  automation_enabled_count: number;
  ready_slice_count: number;
  running_slice_count: number;
}

export interface WorkerSummary {
  worker_id: string;
  adapter_type: string;
  role: string;
  enabled: boolean;
  primary: boolean;
  model_slug?: string | null;
  credential_ref_names: string[];
  webhook_env_names?: Record<string, string>;
}

export interface SliceSummaryCounts {
  ready_count: number;
  running_count: number;
  blocked_count: number;
  validated_count: number;
}

export interface RepoSummary {
  id: string;
  github_slug: string;
  integration_branch: string;
  automation_enabled: boolean;
  priority?: number | null;
  readiness: Record<string, boolean>;
  repo_native_paths: Record<string, string>;
  workers: WorkerSummary[];
  slice_summary: SliceSummaryCounts;
}

export interface SliceSummary {
  slice_id: string;
  slice_number: number;
  title: string;
  state: string;
  repo_id: string;
  github_slug?: string | null;
  automation_eligible: boolean;
  operator_gates: string[];
  dependencies: number[];
  repo_native_path: string;
}

export interface RunSummary {
  run_id: string;
  repo_id: string;
  slice_id?: string | null;
  task_id?: string | null;
  runtime: string;
  status: string;
  started_at: string;
  completed_at?: string | null;
  model_slug?: string | null;
  artifact_source?: string | null;
  repo_native_artifact_path?: string | null;
  evidence_status?: string | null;
  pr_url?: string | null;
  handoff_path?: string | null;
}

export interface DispatchSummary {
  dispatch_id: string;
  orchestrator_run_id: string;
  repo_id: string;
  worker_id: string;
  slice_id: string;
  adapter_type?: string | null;
  status: string;
  dispatched_at: string;
  webhook_url_env_name?: string | null;
  chain_back?: boolean | null;
  retry_count: number;
  task_packet_id?: string | null;
  error_summary?: string | null;
}

export interface SyncFileSummary {
  repo: string;
  ref: string;
  path: string;
  sha?: string | null;
  source?: string | null;
}

export interface SyncStatusSummary {
  status: string;
  last_synced_at?: string | null;
  stale_after_seconds: number;
  is_stale: boolean;
  project_count: number;
  dependency_tree_count: number;
  files: SyncFileSummary[];
}

/* --------------------------------------------------------------- fetchers */

export function fetchPortfolio(): Promise<PortfolioSummary> {
  return apiGet<PortfolioSummary>("/api/v1/portfolio");
}

export function fetchRepos(): Promise<RepoSummary[]> {
  return apiGet<RepoSummary[]>("/api/v1/repos");
}

export function fetchRepo(repoId: string): Promise<RepoSummary> {
  return apiGet<RepoSummary>(`/api/v1/repos/${encodePathSegment(repoId)}`);
}

export function fetchRepoSlices(repoId: string): Promise<SliceSummary[]> {
  return apiGet<SliceSummary[]>(
    `/api/v1/repos/${encodePathSegment(repoId)}/slices`,
  );
}

export function fetchRuns(): Promise<RunSummary[]> {
  return apiGet<RunSummary[]>("/api/v1/runs");
}

export function fetchRun(runId: string): Promise<RunSummary> {
  return apiGet<RunSummary>(`/api/v1/runs/${encodePathSegment(runId)}`);
}

export function fetchDispatches(): Promise<DispatchSummary[]> {
  return apiGet<DispatchSummary[]>("/api/v1/dispatches");
}

export function fetchDispatch(dispatchId: string): Promise<DispatchSummary> {
  return apiGet<DispatchSummary>(
    `/api/v1/dispatches/${encodePathSegment(dispatchId)}`,
  );
}

export function fetchSyncStatus(): Promise<SyncStatusSummary> {
  return apiGet<SyncStatusSummary>("/api/v1/sync/status");
}
