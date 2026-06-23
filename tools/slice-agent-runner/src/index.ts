#!/usr/bin/env node
import path from "node:path";

import {
  createArtifactWriter,
  printDryRunArtifacts,
} from "./artifacts.js";
import {
  configPathFor,
  loadRunnerConfig,
  validateConfig,
} from "./slice-config.js";
import { selectNextSlice } from "./slice-selector.js";
import { buildPayload, buildSlicePrompt, type PromptKind } from "./prompts.js";
import { listModels, runSdkPrompt } from "./sdk-session.js";
import type { RunnerConfig, RuntimeMode, SelectedSlice } from "./types.js";

type CommandName = "check" | "models" | "preflight" | "run-next";

type CliOptions = {
  command?: CommandName;
  repo: string;
  runtime: RuntimeMode;
  autoPr: boolean;
  dryRun: boolean;
  printPrompt: boolean;
  force: boolean;
  help: boolean;
  model?: string;
};

async function main(): Promise<void> {
  const options = parseArgs(process.argv.slice(2));

  if (options.help || !options.command) {
    printHelp();
    return;
  }

  if (options.command === "models") {
    await listModels(requireApiKey());
    return;
  }

  const config = loadRunnerConfig(options.repo);
  const effectiveConfig = options.model
    ? { ...config, model: options.model }
    : config;

  if (options.command === "check") {
    await runCheck(effectiveConfig);
    return;
  }

  await runSliceCommand(options.command, effectiveConfig, options);
}

async function runCheck(config: RunnerConfig): Promise<void> {
  const errors = validateConfig(config);

  console.log(`repo: ${config.localPath}`);
  console.log(`config: ${configPathFor(config.localPath)}`);
  console.log(`model: ${config.model}`);

  if (process.env.CURSOR_API_KEY) {
    console.log("CURSOR_API_KEY: present");
  } else {
    console.log("CURSOR_API_KEY: missing (required for SDK runs)");
  }

  try {
    const selected = await selectNextSlice(config);
    console.log(
      `selector: ok (${selected.targetSliceId} ${selected.targetSliceTitle})`
    );
  } catch (error) {
    errors.push(`selector failed: ${messageFromError(error)}`);
  }

  if (errors.length) {
    console.error("check: failed");
    for (const error of errors) {
      console.error(`- ${error}`);
    }
    process.exitCode = 1;
    return;
  }

  console.log("check: passed");
}

async function runSliceCommand(
  command: "preflight" | "run-next",
  config: RunnerConfig,
  options: CliOptions
): Promise<void> {
  const selected = await selectNextSlice(config);
  const triggerReason =
    command === "preflight"
      ? "sdk_runner_preflight"
      : "sdk_runner_run_next";
  const payload = buildPayload(config, selected, triggerReason);
  const prompt = buildSlicePrompt(promptKind(command), config, payload);

  if (options.dryRun || options.printPrompt) {
    printDryRunArtifacts(prompt, payload, config);
    return;
  }

  const artifactLabel = buildRunLabel(command, options.runtime, selected);
  const artifacts = createArtifactWriter(
    config,
    artifactLabel,
    prompt,
    payload,
    options.runtime,
    config.model
  );

  console.error(`artifacts: ${artifacts.runDir}`);

  const sdkResult = await runSdkPrompt({
    apiKey: requireApiKey(),
    config,
    mode: options.runtime,
    model: config.model,
    autoPr: options.autoPr,
    force: options.force,
    prompt,
    onEvent: (event) => {
      artifacts.writeEvent(event);
      renderEvent(event);
    },
  });

  artifacts.writeResult({
    sdk_agent_id: sdkResult.agentId,
    sdk_run_id: sdkResult.runId,
    sdk_runtime: options.runtime,
    sdk_model: config.model,
    events_jsonl: path.relative(config.localPath, artifacts.eventsPath),
    result: sdkResult.result,
  });

  if (sdkResult.result.status !== "finished") {
    process.exitCode = 2;
  }
}

function parseArgs(argv: string[]): CliOptions {
  const options: CliOptions = {
    repo: process.cwd(),
    runtime: "local",
    autoPr: false,
    dryRun: false,
    printPrompt: false,
    force: false,
    help: false,
  };

  const [maybeCommand, ...rest] = argv;
  if (isCommand(maybeCommand)) {
    options.command = maybeCommand;
  } else if (maybeCommand === "--help" || maybeCommand === "-h" || !maybeCommand) {
    options.help = true;
  } else {
    throw new Error(`Unknown command: ${maybeCommand}`);
  }

  for (let index = 0; index < rest.length; index += 1) {
    const arg = rest[index];

    if (arg === "--repo" || arg === "-C") {
      options.repo = readValue(rest, index, arg);
      index += 1;
      continue;
    }
    if (arg.startsWith("--repo=")) {
      options.repo = arg.slice("--repo=".length);
      continue;
    }
    if (arg === "--model" || arg === "-m") {
      options.model = readValue(rest, index, arg);
      index += 1;
      continue;
    }
    if (arg.startsWith("--model=")) {
      options.model = arg.slice("--model=".length);
      continue;
    }
    if (arg === "--local") {
      options.runtime = "local";
      continue;
    }
    if (arg === "--cloud") {
      options.runtime = "cloud";
      continue;
    }
    if (arg === "--auto-pr") {
      options.autoPr = true;
      continue;
    }
    if (arg === "--dry-run") {
      options.dryRun = true;
      continue;
    }
    if (arg === "--print-prompt") {
      options.printPrompt = true;
      continue;
    }
    if (arg === "--force") {
      options.force = true;
      continue;
    }
    if (arg === "--help" || arg === "-h") {
      options.help = true;
      continue;
    }

    throw new Error(`Unknown option: ${arg}`);
  }

  options.repo = path.resolve(options.repo);
  return options;
}

function isCommand(value: string | undefined): value is CommandName {
  return (
    value === "check" ||
    value === "models" ||
    value === "preflight" ||
    value === "run-next"
  );
}

function readValue(argv: string[], index: number, option: string): string {
  const value = argv[index + 1];
  if (!value || value.startsWith("-")) {
    throw new Error(`Expected a value after ${option}.`);
  }
  return value;
}

function requireApiKey(): string {
  const apiKey = process.env.CURSOR_API_KEY;
  if (!apiKey) {
    throw new Error("Set CURSOR_API_KEY before running SDK commands.");
  }
  return apiKey;
}

function promptKind(command: "preflight" | "run-next"): PromptKind {
  return command === "preflight" ? "preflight" : "run-next";
}

function buildRunLabel(
  command: "preflight" | "run-next",
  runtime: RuntimeMode,
  selected: SelectedSlice
): string {
  return [
    new Date().toISOString().replace(/[:.]/g, "-"),
    command,
    runtime,
    selected.targetSliceId,
  ].join("-");
}

function renderEvent(event: { type: string } & Record<string, unknown>): void {
  switch (event.type) {
    case "assistant_delta":
      process.stdout.write(String(event.text ?? ""));
      break;
    case "tool":
      console.error(
        `[tool] ${event.status ?? ""} ${event.name ?? ""} ${event.params ?? ""}`.trim()
      );
      break;
    case "status":
      console.error(
        `[status] ${event.status ?? ""} ${event.message ?? ""}`.trim()
      );
      break;
    case "thinking":
      console.error(`[thinking] ${compact(String(event.text ?? ""))}`);
      break;
    case "task":
      console.error(
        `[task] ${compact([event.status, event.text].filter(Boolean).join(" "))}`
      );
      break;
    case "result":
      console.error(
        `[done] status=${event.status ?? ""} run=${event.runId ?? ""}`
      );
      break;
    default:
      break;
  }
}

function compact(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function messageFromError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function printHelp(): void {
  console.log(`slice-agent-runner

Usage:
  slice-agent-runner check --repo <path>
  slice-agent-runner preflight --repo <path> --local [--dry-run]
  slice-agent-runner run-next --repo <path> --local [--dry-run]
  slice-agent-runner run-next --repo <path> --cloud --auto-pr
  slice-agent-runner models

Options:
  -C, --repo <path>      Target repository path. Defaults to cwd.
  -m, --model <id>      Cursor model id. Defaults to config or CURSOR_MODEL.
  --local               Run against the local repo checkout. Default.
  --cloud               Run in Cursor cloud against the configured GitHub repo.
  --auto-pr             Enable cloud autoCreatePR.
  --dry-run             Render selector payload and prompt without SDK call.
  --print-prompt        Alias-style prompt render without SDK call.
  --force               Expire a stuck active local run before sending.
  -h, --help            Show this help.
`);
}

main().catch((error) => {
  console.error(`Error: ${messageFromError(error)}`);
  process.exitCode = 1;
});
