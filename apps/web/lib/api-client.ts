export type HealthResponse = {
  status: "ok";
  service: string;
  version: string;
};

export type PortfolioSummary = {
  global_fanout_limit: number;
  same_repo_max_when_others_idle?: number;
  repo_count: number;
  automation_enabled_count: number;
  ready_slice_count: number;
  running_slice_count: number;
};

export type WorkerSummary = {
  worker_id: string;
  adapter_type: string;
  role: string;
  enabled: boolean;
  primary: boolean;
  model_slug?: string;
  credential_ref_names?: string[];
  webhook_env_names?: Record<string, string>;
};

export type RepoSummary = {
  id: string;
  github_slug: string;
  integration_branch: string;
  automation_enabled: boolean;
  priority?: number;
  readiness: Record<string, boolean>;
  repo_native_paths: Record<string, string>;
  workers: WorkerSummary[];
  slice_summary: {
    ready_count: number;
    running_count: number;
    blocked_count: number;
    validated_count: number;
  };
};

export type SliceSummary = {
  slice_id: string;
  slice_number: number;
  title: string;
  state: string;
  repo_id: string;
  github_slug?: string;
  automation_eligible: boolean;
  operator_gates: string[];
  dependencies: number[];
  repo_native_path: string;
};

export type DispatchSummary = {
  dispatch_id: string;
  orchestrator_run_id: string;
  repo_id: string;
  worker_id: string;
  slice_id: string;
  adapter_type?: string;
  status: string;
  dispatched_at: string;
  webhook_url_env_name?: string;
  chain_back?: boolean;
  retry_count: number;
  task_packet_id?: string;
  error_summary?: string;
};

export type RunSummary = {
  run_id: string;
  repo_id: string;
  slice_id?: string;
  task_id?: string;
  runtime: string;
  status: string;
  started_at: string;
  completed_at?: string;
  model_slug?: string;
  artifact_source?: string;
  repo_native_artifact_path?: string;
  evidence_status?: string;
  pr_url?: string;
  handoff_path?: string;
};

export type SyncedFileSummary = {
  repo: string;
  ref: string;
  path: string;
  sha?: string;
  source: string;
};

export type SyncStatusSummary = {
  status: string;
  last_synced_at?: string;
  stale_after_seconds: number;
  is_stale: boolean;
  project_count: number;
  dependency_tree_count: number;
  files: SyncedFileSummary[];
};

const DEFAULT_API_URL = "http://127.0.0.1:8000";

export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL;
}

export function apiUrl(path: string) {
  const baseUrl = getApiBaseUrl().replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
}

export async function apiGet<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");

  const response = await fetch(apiUrl(path), {
    ...init,
    headers,
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${path}`);
  }

  return response.json() as Promise<T>;
}

export function fetchHealth() {
  return apiGet<HealthResponse>("/health");
}

export function fetchPortfolio() {
  return apiGet<PortfolioSummary>("/api/v1/portfolio");
}

export function fetchRepos() {
  return apiGet<RepoSummary[]>("/api/v1/repos");
}

export function fetchRepo(repoId: string) {
  return apiGet<RepoSummary>(`/api/v1/repos/${encodeURIComponent(repoId)}`);
}

export function fetchRepoSlices(repoId: string) {
  return apiGet<SliceSummary[]>(`/api/v1/repos/${encodeURIComponent(repoId)}/slices`);
}

export function fetchDispatches() {
  return apiGet<DispatchSummary[]>("/api/v1/dispatches");
}

export function fetchDispatch(dispatchId: string) {
  return apiGet<DispatchSummary>(
    `/api/v1/dispatches/${encodeURIComponent(dispatchId)}`,
  );
}

export function fetchRuns() {
  return apiGet<RunSummary[]>("/api/v1/runs");
}

export function fetchRun(runId: string) {
  return apiGet<RunSummary>(`/api/v1/runs/${encodeURIComponent(runId)}`);
}

export function fetchSyncStatus() {
  return apiGet<SyncStatusSummary>("/api/v1/sync/status");
}
