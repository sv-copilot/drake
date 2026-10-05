import fs from "node:fs";
import path from "node:path";

import type { HarnessInvocation, HarnessPreset } from "./harnesses.js";
import type { NormalizedPayload, RunnerConfig, RunnerEvent } from "./types.js";

/** Run artifacts live here: neutral, gitignored, never harness-specific. */
export const RUNS_DIR = ".drake/runs";

export type ArtifactWriter = {
  runDir: string;
  promptPath: string;
  eventsPath: string;
  writeEvent(event: RunnerEvent): void;
  writeResult(result: unknown): void;
};

export function runDirFor(config: RunnerConfig, runLabel: string): string {
  return path.join(config.localPath, RUNS_DIR, sanitizeLabel(runLabel));
}

export function createArtifactWriter(
  config: RunnerConfig,
  runLabel: string,
  prompt: string,
  payload: NormalizedPayload,
  harness: { id: string; model: string | null }
): ArtifactWriter {
  const runDir = runDirFor(config, runLabel);
  fs.mkdirSync(runDir, { recursive: true });

  const eventsPath = path.join(runDir, "events.jsonl");
  const promptPath = path.join(runDir, "prompt.txt");
  fs.writeFileSync(promptPath, `${prompt.trim()}\n`, "utf8");
  writeJsonFile(runDir, "payload.json", payload);
  writeJsonFile(runDir, "metadata.json", {
    harness: harness.id,
    model: harness.model,
    runner: "slice-agent-runner",
    createdAt: new Date().toISOString(),
  });
  fs.writeFileSync(eventsPath, "", "utf8");

  return {
    runDir,
    promptPath,
    eventsPath,
    writeEvent(event) {
      appendJsonLine(eventsPath, { ts: new Date().toISOString(), ...event });
    },
    writeResult(result) {
      writeJsonFile(runDir, "result.json", result);
    },
  };
}

export function writeJsonFile(dir: string, name: string, value: unknown): string {
  const target = path.join(dir, name);
  fs.writeFileSync(target, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  return target;
}

export function printDryRunArtifacts(
  prompt: string,
  payload: NormalizedPayload,
  config: RunnerConfig,
  invocation: HarnessInvocation,
  preset: HarnessPreset
): void {
  console.log("Dry run: no harness was started.");
  console.log("");
  console.log("Harness:");
  console.log(
    JSON.stringify(
      {
        id: preset.id,
        name: preset.name,
        command: invocation.display,
        prompt_delivery: preset.promptDelivery,
        model: config.harnessModel ?? "(harness default)",
        docs: preset.docsUrl,
      },
      null,
      2
    )
  );
  console.log("");
  console.log("Payload:");
  console.log(JSON.stringify(payload, null, 2));
  console.log("");
  console.log("Prompt:");
  console.log(prompt);
  console.log("");
  console.log("Config:");
  console.log(
    JSON.stringify(
      {
        projectName: config.projectName,
        githubSlug: config.githubSlug,
        localPath: config.localPath,
        integrationBranch: config.integrationBranch,
        harness: config.harness,
      },
      null,
      2
    )
  );
  console.log("");
  console.log(`Run directory: ${path.join(config.localPath, RUNS_DIR)}/<run-label>`);
}

function sanitizeLabel(runLabel: string): string {
  return runLabel.replace(/[^a-zA-Z0-9._-]+/g, "-");
}

function appendJsonLine(filePath: string, value: unknown): void {
  fs.appendFileSync(filePath, `${JSON.stringify(value)}\n`, "utf8");
}
