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

const DEFAULT_API_URL = "http://127.0.0.1:8000";

export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL;
}

export async function apiGet<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...init.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
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
