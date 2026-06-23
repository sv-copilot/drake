import type {
  NormalizedPayload,
  RunnerConfig,
  SelectedSlice,
} from "./types.js";

export type PromptKind = "preflight" | "run-next";

export function buildPayload(
  config: RunnerConfig,
  selected: SelectedSlice,
  triggerReason: string
): NormalizedPayload {
  return {
    target_repo_id: config.projectId,
    target_github_slug: config.githubSlug,
    target_local_path: config.localPath,
    integration_branch: config.integrationBranch,
    target_slice_id: selected.targetSliceId,
    target_slice_number: selected.targetSliceNumber,
    target_slice_title: selected.targetSliceTitle,
    dependency_tree_path: config.dependencyTreePath,
    slice_backlog_path: config.sliceBacklogPath,
    slice_detail_dir: config.sliceDetailDir,
    fanout_limit: selected.fanoutLimit,
    trigger_reason: triggerReason,
  };
}

export function buildSlicePrompt(
  kind: PromptKind,
  config: RunnerConfig,
  payload: NormalizedPayload
): string {
  const preflightOnly =
    kind === "preflight"
      ? "\nPreflight-only mode: stop after /slice-preflight returns Path A, Path B, or STOP. Do not invoke /slice-implementer or /pr-babysitter.\n"
      : "";

  return [
    "You are running the repo-local slice-pipeline-local workflow through the Cursor SDK.",
    "",
    "Hard constraints:",
    "- Read and follow AGENTS.md and repo-local policy before any git operation.",
    "- Use only the approved slice-pipeline subagents: slice-preflight, slice-implementer, pr-babysitter.",
    "- Keep one slice, one PR, no fan-out.",
    "- Do not implement a different slice.",
    "- Do not commit secrets, tokens, browser sessions, local MCP config, or runtime handoff artifacts.",
    "- Runtime handoff files belong under .cursor/automation-runs/ and must not be committed.",
    preflightOnly.trim(),
    "",
    "Read first:",
    "- AGENTS.md",
    "- .docs/git_workflow.md",
    "- .docs/agent_automation_execution_policy.md",
    "- .docs/agent_automations.md",
    "- .docs/agent_prompts/slice-pipeline-automation.md",
    "- .docs/agent_prompts/slice-pipeline-handoff-contract.md",
    "",
    "Configured project values:",
    fencedJson({
      projectName: config.projectName,
      projectId: config.projectId,
      githubSlug: config.githubSlug,
      localPath: config.localPath,
      integrationBranch: config.integrationBranch,
      featureBranchPrefix: config.featureBranchPrefix,
      legacyFeatureBranchPrefixes: config.legacyFeatureBranchPrefixes,
      selectorCommand: config.sliceSelectorCommand,
      validationCommands: config.validationCommands,
      docsSyncCommand: config.docsSyncCommand,
    }),
    "",
    "Normalized payload:",
    fencedJson(payload),
    "",
    "Required final handoff:",
    "- routing path: A, B, or STOP",
    "- selected slice",
    "- PR URL/state if any",
    "- merge action if any",
    "- validation summary",
    "- docs sync result if any",
    "- webhook chaining result if any",
    "- blockers",
  ]
    .filter(Boolean)
    .join("\n");
}

function fencedJson(value: unknown): string {
  return ["```json", JSON.stringify(value, null, 2), "```"].join("\n");
}
