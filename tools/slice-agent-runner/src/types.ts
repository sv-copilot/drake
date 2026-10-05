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
  /** Harness preset id from the catalogue ("claude", "codex", "cursor", "aider", "generic"). */
  harness: string;
  /** Shell command for the "generic" harness; null for built-in presets. */
  harnessCommand: string | null;
  /** Model passed to the harness; null means "use whatever the harness is configured with". */
  harnessModel: string | null;
  /** Legacy alias kept so older configs keep loading. */
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

export type RunnerEvent = Record<string, unknown>;
