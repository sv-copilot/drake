#!/usr/bin/env node
import path from "node:path";

import {
  createArtifactWriter,
  printDryRunArtifacts,
  runDirFor,
  writeJsonFile,
} from "./artifacts.js";
import { buildBlockedEvidence, buildEvidence, buildTaskPacket, collectChangedFiles } from "./contracts.js";
import { runHarness } from "./harness-session.js";
import {
  binaryOnPath,
  buildInvocation,
  findHarness,
  HARNESSES,
  harnessIds,
  type HarnessPreset,
} from "./harnesses.js";
import { buildPayload, buildSlicePrompt, type PromptKind } from "./prompts.js";
import { CONFIG_FILE, loadRunnerConfig, validateConfig } from "./slice-config.js";
import { NoRunnableSliceError, selectNextSlice } from "./slice-selector.js";
import type { RunnerConfig } from "./types.js";
import { RUNNER_VERSION } from "./version.js";

type CommandName = "check" | "harnesses" | "preflight" | "run-next";

type CliOptions = {
  command?: CommandName;
  repo: string;
  dryRun: boolean;
  printPrompt: boolean;
  help: boolean;
  harness?: string;
  harnessCommand?: string;
  model?: string;
};

async function main(): Promise<void> {
  const options = parseArgs(process.argv.slice(2));

  if (options.help || !options.command) {
    printHelp();
    return;
  }

  if (options.command === "harnesses") {
    printHarnesses();
    return;
  }

  const loaded = loadRunnerConfig(options.repo);
  const config = applyOverrides(loaded.config, options);
  for (const warning of loaded.warnings) {
    console.error(`[warn] ${warning}`);
  }

  if (options.command === "check") {
    await runCheck(config, loaded.configPath);
    return;
  }

  await runSliceCommand(options.command, config, options);
}

/**
 * Nothing runnable is a normal scheduler state, not a crash: report it and exit 3
 * so a cron job can tell "no work" apart from "the harness or config is broken".
 */
async function selectSliceOrExit(config: RunnerConfig) {
  try {
    return await selectNextSlice(config);
  } catch (error) {
    if (error instanceof NoRunnableSliceError) {
      console.error(
        "no runnable slice: nothing is ready, unblocked, and automation-eligible"
      );
      process.exitCode = 3;
      return undefined;
    }
    throw error;
  }
}

async function runCheck(config: RunnerConfig, configPath: string): Promise<void> {
  const errors: string[] = [];
  const notes: string[] = [];

  console.log(`repo:        ${config.localPath}`);
  console.log(`config:      ${configPath}`);
  console.log(`project:     ${config.projectName} (${config.projectId})`);
  console.log(`harness:     ${config.harness || "(unset)"}`);
  console.log(`model:       ${config.harnessModel ?? "(harness default)"}`);

  const preset = resolvePresetOrUndefined(config, errors);
  if (preset) {
    if (preset.binary) {
      const resolved = binaryOnPath(preset.binary);
      if (resolved) {
        console.log(`binary:      ${resolved}`);
      } else {
        errors.push(
          `harness binary not found on PATH: ${preset.binary} (docs: ${preset.docsUrl})`
        );
      }
    } else if (!config.harnessCommand?.trim()) {
      errors.push(
        `harness "${preset.id}" needs harness.command; set it in ${CONFIG_FILE} or pass --harness-command (docs: ${preset.docsUrl})`
      );
    } else {
      console.log(`command:     ${config.harnessCommand.trim()}`);
    }

    if (preset.authEnv.length) {
      const missing = preset.authEnv.filter((name) => !process.env[name]);
      notes.push(
        `credential env not set: ${missing.join(", ")} — harnesses may also use their own stored login`
      );
    }
  }

  errors.push(...validateConfig(config));

  try {
    const selected = await selectNextSlice(config);
    console.log(`next slice:  ${selected.targetSliceId} — ${selected.targetSliceTitle}`);
  } catch (error) {
    if (error instanceof NoRunnableSliceError) {
      console.log("next slice:  none runnable");
    } else {
      errors.push(messageFromError(error));
    }
  }

  for (const note of notes) {
    console.log(`note:        ${note}`);
  }

  if (errors.length) {
    console.error("");
    for (const error of errors) {
      console.error(`[fail] ${error}`);
    }
    console.error("");
    console.error("check: failed");
    process.exitCode = 1;
    return;
  }

  console.log("");
  console.log("check: passed");
}

async function runSliceCommand(
  command: "preflight" | "run-next",
  config: RunnerConfig,
  options: CliOptions
): Promise<void> {
  const preset = resolvePreset(config);
  const selected = await selectSliceOrExit(config);
  if (!selected) {
    return;
  }
  const kind: PromptKind = promptKind(command);
  const payload = buildPayload(
    config,
    selected,
    `${preset.id} harness via slice-agent-runner`
  );
  const prompt = buildSlicePrompt(kind, config, payload, preset);
  const runLabel = buildRunLabel(command, preset, selected.targetSliceId);

  if (options.printPrompt) {
    console.log(prompt);
    return;
  }

  if (options.dryRun) {
    const previewDir = runDirFor(config, runLabel);
    const invocation = buildInvocation(preset, {
      prompt,
      promptFile: path.join(previewDir, "prompt.txt"),
      model: config.harnessModel,
      command: config.harnessCommand,
    });
    printDryRunArtifacts(prompt, payload, config, invocation, preset);
    return;
  }

  const artifacts = createArtifactWriter(config, runLabel, prompt, payload, {
    id: preset.id,
    model: config.harnessModel,
  });
  const invocation = buildInvocation(preset, {
    prompt,
    promptFile: artifacts.promptPath,
    model: config.harnessModel,
    command: config.harnessCommand,
  });
  const startedAt = new Date().toISOString();

  writeJsonFile(
    artifacts.runDir,
    "task-packet.json",
    buildTaskPacket({
      config,
      payload,
      prompt,
      preset,
      runLabel,
      promptFile: artifacts.promptPath,
      kind,
    })
  );

  console.log(`harness: ${preset.name} (${preset.id})`);
  console.log(`command: ${invocation.display}`);
  console.log(`run dir: ${artifacts.runDir}`);
  console.log("");

  artifacts.writeEvent({
    type: "HARNESS_STARTED",
    harness: preset.id,
    command: invocation.display,
  });

  try {
    const outcome = await runHarness({
      harness: preset.id,
      invocation,
      cwd: config.localPath,
      runDir: artifacts.runDir,
      env: process.env,
      stdin: preset.promptDelivery === "stdin" ? prompt : undefined,
    });

    const changed = collectChangedFiles(config.localPath);
    const evidence = buildEvidence({
      config,
      payload,
      preset,
      outcome,
      changedFiles: changed.files,
      changedNote: changed.note,
      runLabel,
      startedAt,
      promptFile: artifacts.promptPath,
    });
    writeJsonFile(artifacts.runDir, "evidence.json", evidence);
    artifacts.writeEvent({
      type: "HARNESS_EXITED",
      harness: preset.id,
      exitCode: outcome.exitCode,
      durationMs: outcome.durationMs,
      changedFiles: changed.files.length,
    });
    artifacts.writeResult({
      harness: preset.id,
      command: outcome.command,
      exit_code: outcome.exitCode,
      duration_ms: outcome.durationMs,
      status: outcome.status,
      run_dir: artifacts.runDir,
    });

    console.log("");
    console.log(`exit:     ${outcome.exitCode}`);
    console.log(`evidence: ${path.join(artifacts.runDir, "evidence.json")}`);

    if (outcome.exitCode !== 0) {
      console.error(`harness exited ${outcome.exitCode}: the slice run did not finish`);
      process.exitCode = 2;
    }
  } catch (error) {
    const message = messageFromError(error);
    artifacts.writeEvent({ type: "HARNESS_FAILED", harness: preset.id, message });
    writeJsonFile(
      artifacts.runDir,
      "evidence.json",
      buildBlockedEvidence({
        config,
        payload,
        preset,
        runLabel,
        startedAt,
        promptFile: artifacts.promptPath,
        command: invocation.display,
        message,
      })
    );
    console.error(`[fail] ${message}`);
    process.exitCode = 1;
  }
}

function applyOverrides(config: RunnerConfig, options: CliOptions): RunnerConfig {
  return {
    ...config,
    harness: options.harness ?? config.harness,
    harnessCommand: options.harnessCommand ?? config.harnessCommand,
    harnessModel: options.model ?? config.harnessModel,
  };
}

function resolvePreset(config: RunnerConfig): HarnessPreset {
  const preset = findHarness(config.harness);
  if (!preset) {
    throw new Error(
      `unknown harness "${config.harness}": known harnesses are ${harnessIds().join(", ")}`
    );
  }
  return preset;
}

function resolvePresetOrUndefined(
  config: RunnerConfig,
  errors: string[]
): HarnessPreset | undefined {
  if (!config.harness.trim()) {
    return undefined;
  }
  try {
    return resolvePreset(config);
  } catch (error) {
    errors.push(messageFromError(error));
    return undefined;
  }
}

function printHarnesses(): void {
  console.log(`slice-agent-runner ${RUNNER_VERSION} — harness catalogue`);
  console.log("");
  for (const preset of HARNESSES) {
    const binary = preset.binary ?? "(your command)";
    const status = preset.binary
      ? binaryOnPath(preset.binary)
        ? "found on PATH"
        : "NOT on PATH"
      : "set harness.command";
    console.log(`${preset.id}  —  ${preset.name}`);
    console.log(`  binary:  ${binary} (${status})`);
    console.log(`  prompt:  ${preset.promptDelivery}`);
    console.log(`  config:  ${preset.configDir ?? "n/a"}`);
    console.log(`  auth:    ${preset.authEnv.join(", ") || "n/a"}`);
    console.log(`  docs:    ${preset.docsUrl} (checked ${preset.verifiedOn})`);
    console.log(`  note:    ${preset.notes}`);
    console.log("");
  }
}

function promptKind(command: "preflight" | "run-next"): PromptKind {
  return command === "preflight" ? "preflight" : "run-next";
}

function buildRunLabel(
  command: "preflight" | "run-next",
  preset: HarnessPreset,
  sliceId: string
): string {
  return [
    new Date().toISOString().replace(/[:.]/g, "-"),
    command,
    preset.id,
    sliceId,
  ].join("-");
}

function parseArgs(argv: string[]): CliOptions {
  const options: CliOptions = {
    repo: process.cwd(),
    dryRun: false,
    printPrompt: false,
    help: false,
  };

  const [maybeCommand, ...rest] = argv;
  if (isCommand(maybeCommand)) {
    options.command = maybeCommand;
  } else if (maybeCommand === "models") {
    throw new Error(
      "the `models` command was specific to the Cursor SDK and is gone; use `harnesses` to list harnesses"
    );
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
    if (arg === "--harness") {
      options.harness = readValue(rest, index, arg);
      index += 1;
      continue;
    }
    if (arg.startsWith("--harness=")) {
      options.harness = arg.slice("--harness=".length);
      continue;
    }
    if (arg === "--harness-command") {
      options.harnessCommand = readValueAllowEmpty(rest, index, arg);
      index += 1;
      continue;
    }
    if (arg.startsWith("--harness-command=")) {
      options.harnessCommand = arg.slice("--harness-command=".length);
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
    if (arg === "--dry-run") {
      options.dryRun = true;
      continue;
    }
    if (arg === "--print-prompt") {
      options.printPrompt = true;
      continue;
    }
    if (arg === "--local") {
      continue;
    }
    if (arg === "--cloud" || arg === "--auto-pr" || arg === "--force") {
      throw new Error(
        `${arg} was specific to the retired Cursor SDK adapter and is gone: drive your harness's own remote or permission mode instead (see docs/harnesses.md)`
      );
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
    value === "harnesses" ||
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

/** A harness command legitimately starts with a dash (rare) or is quoted by the shell. */
function readValueAllowEmpty(argv: string[], index: number, option: string): string {
  const value = argv[index + 1];
  if (value === undefined) {
    throw new Error(`Expected a value after ${option}.`);
  }
  return value;
}

function messageFromError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function printHelp(): void {
  console.log(`slice-agent-runner ${RUNNER_VERSION}

Pick the next ready slice, hand it to a coding harness, and record the evidence.

Usage:
  slice-agent-runner <command> [options]

Commands:
  check          Validate config, harness availability and the selector
  harnesses      List known harnesses and whether their binary is on PATH
  preflight      Run the slice preflight prompt through the harness
  run-next       Run the next ready slice through the harness

Options:
  -C, --repo <path>            Repository to operate on (default: cwd)
      --harness <id>           Harness preset: ${harnessIds().join(", ")}
      --harness-command <cmd>  Command for the "generic" harness
                               ({prompt}, {prompt_file}, {model} placeholders)
  -m, --model <name>           Model passed to the harness (default: harness's own)
      --dry-run                Print the task packet and command without running
      --print-prompt           Print the rendered prompt and exit
  -h, --help                   Show this help

Exit codes:
  0  harness ran and exited 0
  1  configuration, harness startup, or selector error
  2  harness ran but exited non-zero (slice run unfinished)
  3  nothing to do: no slice is ready, unblocked and automation-eligible

Config:
  ${CONFIG_FILE} in the target repository (docs/harnesses.md)
`);
}

main().catch((error: unknown) => {
  console.error(`[fail] ${messageFromError(error)}`);
  process.exitCode = 1;
});
