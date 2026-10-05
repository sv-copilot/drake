import fs from "node:fs";
import path from "node:path";

import type { RunnerConfig } from "./types.js";

/** Harness-neutral config location. */
export const CONFIG_FILE = ".drake/slice-pipeline.config.json";

/** Pre-0.2 location (Cursor-branded). Read for compatibility, never written. */
export const LEGACY_CONFIG_FILE = ".cursor/slice-pipeline-local.config.json";

type HarnessBlock = {
  id?: string;
  model?: string | null;
  command?: string | null;
};

type RawConfig = Partial<{
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
  validationCommands: string[] | string;
  approvedSubagents: string[];
  harness: string | HarnessBlock;
  harnessCommand: string | null;
  harnessModel: string | null;
  /** Legacy pre-0.2 fields. */
  model: string;
  portfolioWebhookUrlEnv: string;
  portfolioWebhookTokenEnv: string;
  localWebhookUrlEnv: string;
  localWebhookTokenEnv: string;
}>;

export type LoadedConfig = {
  config: RunnerConfig;
  configPath: string;
  legacy: boolean;
  warnings: string[];
};

export function loadRunnerConfig(repoPath: string): LoadedConfig {
  const localPath = path.resolve(repoPath);
  const legacyPath = path.join(localPath, LEGACY_CONFIG_FILE);
  const neutralPath = path.join(localPath, CONFIG_FILE);
  const useLegacy = !fs.existsSync(neutralPath) && fs.existsSync(legacyPath);
  const configPath = useLegacy ? legacyPath : neutralPath;
  const raw = readJsonConfig(configPath);
  const warnings: string[] = [];

  if (useLegacy) {
    warnings.push(
      `${LEGACY_CONFIG_FILE} is the pre-0.2 location; move it to ${CONFIG_FILE} (Drake is harness agnostic and no longer keeps configuration under a single harness's directory).`
    );
  }

  const projectName = raw.projectName ?? path.basename(localPath);
  const projectId = raw.projectId ?? slugify(projectName);
  const dependencyTreePath = raw.dependencyTreePath ?? ".docs/slice_dependency_tree.json";
  const configuredLocalPath = raw.localPath ? path.resolve(raw.localPath) : localPath;
  const effectiveLocalPath = fs.existsSync(configuredLocalPath) ? configuredLocalPath : localPath;
  const harnessBlock: HarnessBlock =
    typeof raw.harness === "string" ? { id: raw.harness } : raw.harness ?? {};
  const harnessModel = harnessBlock.model ?? raw.harnessModel ?? raw.model ?? null;

  // A config still at the old path predates the catalogue: keep it working.
  const harness = harnessBlock.id ?? (useLegacy ? "cursor" : "");

  if (!harnessBlock.id && useLegacy) {
    warnings.push('harness not set in the legacy config: defaulting to "cursor".');
  }

  return {
    config: {
      projectName,
      projectId,
      githubSlug: raw.githubSlug ?? "OWNER/REPO",
      localPath: effectiveLocalPath,
      integrationBranch: raw.integrationBranch ?? "dev",
      featureBranchPrefix: raw.featureBranchPrefix ?? "agent/",
      legacyFeatureBranchPrefixes: raw.legacyFeatureBranchPrefixes ?? ["cursor/"],
      dependencyTreePath,
      sliceBacklogPath: raw.sliceBacklogPath ?? ".docs/slice_backlog.md",
      sliceDetailDir: raw.sliceDetailDir ?? ".docs/slices",
      sliceSelectorCommand:
        raw.sliceSelectorCommand ??
        `python3 scripts/select_next_automation_slice.py --tree ${dependencyTreePath}`,
      docsSyncCommand: raw.docsSyncCommand === undefined ? null : raw.docsSyncCommand,
      validationCommands: normalizeCommands(raw.validationCommands),
      approvedSubagents: raw.approvedSubagents ?? [
        "slice-preflight",
        "slice-implementer",
        "pr-babysitter",
      ],
      harness,
      harnessCommand: harnessBlock.command ?? raw.harnessCommand ?? null,
      harnessModel,
      model: harnessModel ?? "",
      portfolioWebhookUrlEnv:
        raw.portfolioWebhookUrlEnv ?? "PORTFOLIO_PLAN_ORCHESTRATOR_WEBHOOK_URL",
      portfolioWebhookTokenEnv:
        raw.portfolioWebhookTokenEnv ?? "PORTFOLIO_PLAN_ORCHESTRATOR_WEBHOOK_TOKEN",
      localWebhookUrlEnv: raw.localWebhookUrlEnv ?? "PLAN_NEXT_SLICE_WEBHOOK_URL",
      localWebhookTokenEnv: raw.localWebhookTokenEnv ?? "PLAN_NEXT_SLICE_WEBHOOK_TOKEN",
    },
    configPath,
    legacy: useLegacy,
    warnings,
  };
}

export function validateConfig(config: RunnerConfig): string[] {
  const errors: string[] = [];
  const requiredFiles = [
    "AGENTS.md",
    ".docs/git_workflow.md",
    ".docs/agent_automations.md",
    ".docs/agent_prompts/slice-pipeline-automation.md",
    ".docs/agent_prompts/slice-pipeline-handoff-contract.md",
    config.dependencyTreePath,
    config.sliceBacklogPath,
  ];

  for (const relPath of requiredFiles) {
    if (!fs.existsSync(path.join(config.localPath, relPath))) {
      errors.push(`missing required file: ${relPath}`);
    }
  }

  if (config.githubSlug === "OWNER/REPO") {
    errors.push("githubSlug is still OWNER/REPO placeholder");
  }

  if (!config.sliceSelectorCommand.trim()) {
    errors.push("sliceSelectorCommand is empty");
  }

  if (!config.harness.trim()) {
    errors.push(
      `harness is not configured: set "harness" in ${CONFIG_FILE} (see docs/harnesses.md)`
    );
  }

  return errors;
}

export function configPathFor(repoPath: string): string {
  return path.join(path.resolve(repoPath), CONFIG_FILE);
}

export function legacyConfigPathFor(repoPath: string): string {
  return path.join(path.resolve(repoPath), LEGACY_CONFIG_FILE);
}

function readJsonConfig(configPath: string): RawConfig {
  if (!fs.existsSync(configPath)) {
    return {};
  }

  try {
    return JSON.parse(fs.readFileSync(configPath, "utf8")) as RawConfig;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Could not parse ${configPath}: ${message}`);
  }
}

function normalizeCommands(value: RawConfig["validationCommands"]): string[] {
  if (Array.isArray(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim()) {
    return [value];
  }

  return [];
}

function slugify(value: string): string {
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "project"
  );
}
