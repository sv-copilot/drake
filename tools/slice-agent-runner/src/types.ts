export type RuntimeMode = "local" | "cloud";

export type RunnerConfig = {
  projectName: string;
  projectId: string;
  githubSlug: string;
  localPath: string;
  integrationBranch: string;
  featureBranchPrefix: string;
  legacyFeatureBranchPrefixes: string[];
  dependencyTreePath: string;
  sliceBacklogPath: string;
  sliceDetailDir: string;
  sliceSelectorCommand: string;
  docsSyncCommand: string | null;
  validationCommands: string[];
  approvedSubagents: string[];
  model: string;
  portfolioWebhookUrlEnv: string;
  portfolioWebhookTokenEnv: string;
  localWebhookUrlEnv: string;
  localWebhookTokenEnv: string;
};

export type SelectedSlice = {
  targetSliceId: string;
  targetSliceNumber: number | null;
  targetSliceTitle: string;
  fanoutLimit: number;
  raw: unknown;
};

export type NormalizedPayload = {
  target_repo_id: string;
  target_github_slug: string;
  target_local_path: string;
  integration_branch: string;
  target_slice_id: string;
  target_slice_number: number | null;
  target_slice_title: string;
  dependency_tree_path: string;
  slice_backlog_path: string;
  slice_detail_dir: string;
  fanout_limit: number;
  trigger_reason: string;
};

export type RunnerEvent =
  | { type: "assistant_delta"; text: string }
  | { type: "thinking"; text: string }
  | {
      type: "tool";
      callId?: string;
      name: string;
      params?: string;
      status: string;
    }
  | { type: "status"; status: string; message?: string }
  | { type: "task"; status?: string; text?: string }
  | {
      type: "result";
      status: string;
      durationMs?: number;
      agentId?: string;
      runId?: string;
    };
