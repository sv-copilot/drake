import fs from "node:fs";
import path from "node:path";

import type { RunnerConfig } from "./types.js";

const DEFAULT_CONFIG_FILE = ".cursor/slice-pipeline-local.config.json";

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
  model: string;
  portfolioWebhookUrlEnv: string;
  portfolioWebhookTokenEnv: string;
  localWebhookUrlEnv: string;
  localWebhookTokenEnv: string;
}>;

export function loadRunnerConfig(repoPath: string): RunnerConfig {
  const localPath = path.resolve(repoPath);
  const configPath = path.join(localPath, DEFAULT_CONFIG_FILE);
  const raw = readJsonConfig(configPath);
  const projectName = raw.projectName ?? path.basename(localPath);
  const projectId = raw.projectId ?? slugify(projectName);
  const dependencyTreePath =
    raw.dependencyTreePath ?? ".docs/slice_dependency_tree.json";
  const configuredLocalPath = raw.localPath
    ? path.resolve(raw.localPath)
    : localPath;
  const effectiveLocalPath = fs.existsSync(configuredLocalPath)
    ? configuredLocalPath
    : localPath;

  return {
    projectName,
    projectId,
    githubSlug: raw.githubSlug ?? "OWNER/REPO",
    localPath: effectiveLocalPath,
    integrationBranch: raw.integrationBranch ?? "ai-dev",
    featureBranchPrefix: raw.featureBranchPrefix ?? "agent/",
    legacyFeatureBranchPrefixes: raw.legacyFeatureBranchPrefixes ?? ["cursor/"],
    dependencyTreePath,
    sliceBacklogPath: raw.sliceBacklogPath ?? ".docs/slice_backlog.md",
    sliceDetailDir: raw.sliceDetailDir ?? ".docs/slices",
    sliceSelectorCommand:
      raw.sliceSelectorCommand ??
      `python3 scripts/select_next_automation_slice.py --tree ${dependencyTreePath}`,
    docsSyncCommand:
      raw.docsSyncCommand === undefined ? null : raw.docsSyncCommand,
    validationCommands: normalizeCommands(raw.validationCommands),
    approvedSubagents: raw.approvedSubagents ?? [
      "slice-preflight",
      "slice-implementer",
      "pr-babysitter",
    ],
    model: raw.model ?? process.env.CURSOR_MODEL ?? "composer-2.5",
    portfolioWebhookUrlEnv:
      raw.portfolioWebhookUrlEnv ?? "PORTFOLIO_PLAN_ORCHESTRATOR_WEBHOOK_URL",
    portfolioWebhookTokenEnv:
      raw.portfolioWebhookTokenEnv ??
      "PORTFOLIO_PLAN_ORCHESTRATOR_WEBHOOK_TOKEN",
    localWebhookUrlEnv: raw.localWebhookUrlEnv ?? "PLAN_NEXT_SLICE_WEBHOOK_URL",
    localWebhookTokenEnv:
      raw.localWebhookTokenEnv ?? "PLAN_NEXT_SLICE_WEBHOOK_TOKEN",
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

  if (!config.model.trim()) {
    errors.push("model is empty");
  }

  return errors;
}

export function configPathFor(repoPath: string): string {
  return path.join(path.resolve(repoPath), DEFAULT_CONFIG_FILE);
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
