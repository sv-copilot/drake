import { execFileSync } from "node:child_process";

import type { HarnessRunOutcome } from "./harness-session.js";
import type { HarnessPreset } from "./harnesses.js";
import type { PromptKind } from "./prompts.js";
import type { NormalizedPayload, RunnerConfig } from "./types.js";
import { RUNNER_VERSION } from "./version.js";

export type ChangedFile = {
  path: string;
  changeType: "added" | "modified" | "deleted" | "renamed";
};

export type ChangedFiles = {
  files: ChangedFile[];
  /**
   * Why the list is empty, when it is. An empty list with no explanation reads as
   * "the harness changed nothing", which may be false: the working tree may simply
   * not be inspectable.
   */
  note?: string;
};

/**
 * Task packets and evidence records are the public half of the ADAPTER CONTRACT:
 * whatever harness runs a slice, these two documents are what the pipeline reads
 * afterwards. They are validated against adapters/*.schema.json by the test suite.
 */
export function buildTaskPacket(input: {
  config: RunnerConfig;
  payload: NormalizedPayload;
  prompt: string;
  preset: HarnessPreset;
  runLabel: string;
  promptFile: string;
  kind: PromptKind;
}): Record<string, unknown> {
  const { config, payload, preset, runLabel } = input;

  return {
    id: runLabel,
    task_type: input.kind === "preflight" ? "audit_repo" : "implement_slice",
    slice_ref: {
      slice_id: payload.target_slice_id,
      slice_number: payload.target_slice_number ?? 0,
      slice_title: payload.target_slice_title,
      dependency_tree_path: payload.dependency_tree_path,
      slice_detail_dir: payload.slice_detail_dir,
    },
    orchestrator_ref: {
      run_id: runLabel,
      orchestrator_type: "slice_pipeline",
      dispatched_at: new Date().toISOString(),
    },
    adapter_type: preset.id,
    payload: {
      instructions: input.prompt,
      working_directory: config.localPath,
      branch_prefix: config.featureBranchPrefix,
      target_branch: config.integrationBranch,
    },
    context: {
      repo_url: `https://github.com/${config.githubSlug}`,
      github_slug: config.githubSlug,
      integration_branch: config.integrationBranch,
      environment: "local",
      model_hint: config.harnessModel ?? undefined,
      tags: {
        harness: preset.id,
        prompt_file: input.promptFile,
      },
    },
    created_at: new Date().toISOString(),
  };
}

export function buildEvidence(input: {
  config: RunnerConfig;
  payload: NormalizedPayload;
  preset: HarnessPreset;
  outcome: HarnessRunOutcome;
  changedFiles: ChangedFile[];
  changedNote?: string;
  runLabel: string;
  startedAt: string;
  promptFile: string;
}): Record<string, unknown> {
  const { config, payload, preset, outcome, runLabel } = input;
  const completedAt = new Date().toISOString();

  return {
    task_id: runLabel,
    status: outcome.exitCode === 0 ? "success" : "failure",
    summary:
      `${preset.name} (${preset.id}) ran slice ${payload.target_slice_id} ` +
      `and exited ${outcome.exitCode} after ${Math.round(outcome.durationMs / 1000)}s`,
    evidence_items: input.changedFiles.map((file) => ({
      path: file.path,
      change_type: file.changeType,
      description: `${file.changeType} by harness run ${runLabel}`,
    })),
    adapter_info: {
      adapter_type: preset.id,
      adapter_version: RUNNER_VERSION,
      runtime: "local",
    },
    completed_at: completedAt,
    logs: [
      { timestamp: input.startedAt, level: "info", message: `command: ${outcome.command}` },
      {
        timestamp: completedAt,
        level: outcome.exitCode === 0 ? "info" : "error",
        message: `exit code ${outcome.exitCode} after ${outcome.durationMs}ms`,
      },
      ...(input.changedNote
        ? [{ timestamp: completedAt, level: "warn", message: input.changedNote }]
        : []),
    ],
    timestamps: {
      started_at: input.startedAt,
      completed_at: completedAt,
      duration_ms: outcome.durationMs,
    },
    harness: {
      id: preset.id,
      command: outcome.command,
      exit_code: outcome.exitCode,
      stdout_log: outcome.stdoutPath,
      stderr_log: outcome.stderrPath,
      prompt_file: input.promptFile,
      model: config.harnessModel,
      docs: preset.docsUrl,
    },
  };
}

export function buildBlockedEvidence(input: {
  config: RunnerConfig;
  payload: NormalizedPayload;
  preset: HarnessPreset;
  runLabel: string;
  startedAt: string;
  promptFile: string;
  command: string;
  message: string;
}): Record<string, unknown> {
  const completedAt = new Date().toISOString();

  return {
    task_id: input.runLabel,
    status: "blocked",
    summary: `harness ${input.preset.id} could not start for slice ${input.payload.target_slice_id}: ${input.message}`,
    evidence_items: [],
    adapter_info: {
      adapter_type: input.preset.id,
      adapter_version: RUNNER_VERSION,
      runtime: "local",
    },
    completed_at: completedAt,
    logs: [{ timestamp: completedAt, level: "error", message: input.message }],
    timestamps: {
      started_at: input.startedAt,
      completed_at: completedAt,
      duration_ms: 0,
    },
    harness: {
      id: input.preset.id,
      command: input.command,
      exit_code: null,
      prompt_file: input.promptFile,
      model: input.config.harnessModel,
      docs: input.preset.docsUrl,
    },
  };
}

/** Working-tree changes the harness made, so evidence names them explicitly. */
export function collectChangedFiles(cwd: string): ChangedFiles {
  let output: string;
  try {
    output = execFileSync("git", ["-C", cwd, "status", "--porcelain"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    });
  } catch {
    return {
      files: [],
      note: `could not read the working tree with git in ${cwd}; evidence lists no changed files`,
    };
  }

  const files = output
    .split("\n")
    .filter((line) => line.trim().length > 0)
    .map(parsePorcelainLine)
    .filter((entry): entry is ChangedFile => entry !== undefined);

  if (files.length === 0) {
    return { files, note: "the harness left no working-tree changes behind" };
  }

  return { files };
}

function parsePorcelainLine(line: string): ChangedFile | undefined {
  const index = line.slice(0, 2);
  const rawPath = line.slice(3).trim();
  if (!rawPath) {
    return undefined;
  }

  // Renames render as "old -> new": keep the destination, which is what changed.
  const target = rawPath.includes(" -> ") ? rawPath.split(" -> ")[1] : rawPath;
  const path = target.replace(/^"|"$/g, "");
  const code = `${index[0]}${index[1]}`.replace(/\s/g, "");

  if (code === "??" || code.includes("A")) {
    return { path, changeType: "added" };
  }
  if (code.includes("D")) {
    return { path, changeType: "deleted" };
  }
  if (code.includes("R")) {
    return { path, changeType: "renamed" };
  }
  return { path, changeType: "modified" };
}
