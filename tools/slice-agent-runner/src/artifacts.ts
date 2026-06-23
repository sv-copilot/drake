import fs from "node:fs";
import path from "node:path";

import type { NormalizedPayload, RunnerConfig, RunnerEvent } from "./types.js";

export type ArtifactWriter = {
  runDir: string;
  eventsPath: string;
  writeEvent(event: RunnerEvent): void;
  writeResult(result: unknown): void;
};

export function createArtifactWriter(
  config: RunnerConfig,
  runLabel: string,
  prompt: string,
  payload: NormalizedPayload,
  runtime: string,
  model: string
): ArtifactWriter {
  const safeLabel = runLabel.replace(/[^a-zA-Z0-9._-]+/g, "-");
  const runDir = path.join(
    config.localPath,
    ".cursor",
    "automation-runs",
    safeLabel
  );
  fs.mkdirSync(runDir, { recursive: true });

  const eventsPath = path.join(runDir, "events.jsonl");
  fs.writeFileSync(
    path.join(runDir, "prompt.txt"),
    `${prompt.trim()}\n`,
    "utf8"
  );
  fs.writeFileSync(
    path.join(runDir, "payload.json"),
    `${JSON.stringify(payload, null, 2)}\n`,
    "utf8"
  );
  fs.writeFileSync(
    path.join(runDir, "metadata.json"),
    `${JSON.stringify({ runtime, model, createdAt: new Date().toISOString() }, null, 2)}\n`,
    "utf8"
  );
  fs.writeFileSync(eventsPath, "", "utf8");

  return {
    runDir,
    eventsPath,
    writeEvent(event) {
      appendJsonLine(eventsPath, {
        ts: new Date().toISOString(),
        ...event,
      });
    },
    writeResult(result) {
      fs.writeFileSync(
        path.join(runDir, "result.json"),
        `${JSON.stringify(result, null, 2)}\n`,
        "utf8"
      );
    },
  };
}

export function printDryRunArtifacts(
  prompt: string,
  payload: NormalizedPayload,
  config: RunnerConfig
): void {
  console.log("Dry run: SDK agent was not started.");
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
        model: config.model,
      },
      null,
      2
    )
  );
}

function appendJsonLine(filePath: string, value: unknown): void {
  fs.appendFileSync(filePath, `${JSON.stringify(value)}\n`, "utf8");
}
