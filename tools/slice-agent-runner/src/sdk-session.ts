import { execFileSync } from "node:child_process";
import {
  Agent,
  Cursor,
  CursorAgentError,
  type ModelSelection,
  type Run,
  type RunResult,
  type SDKAgent,
  type SDKMessage,
} from "@cursor/sdk";

import type { RunnerConfig, RunnerEvent, RuntimeMode } from "./types.js";

export type SdkRunOptions = {
  apiKey: string;
  config: RunnerConfig;
  mode: RuntimeMode;
  model: string;
  autoPr: boolean;
  force: boolean;
  prompt: string;
  onEvent: (event: RunnerEvent) => void;
};

export type SdkRunSuccess = {
  agentId: string;
  runId: string;
  result: RunResult;
};

export async function runSdkPrompt(
  options: SdkRunOptions
): Promise<SdkRunSuccess> {
  const session = await SdkSession.create(options);
  try {
    return await session.send(options.prompt, options.onEvent);
  } finally {
    await session.dispose();
  }
}

export async function listModels(apiKey: string): Promise<void> {
  const models = await Cursor.models.list({ apiKey });

  for (const model of models) {
    const variants = model.variants?.length
      ? ` variants=${model.variants.map((variant) => variant.displayName).join(", ")}`
      : "";
    console.log(`${model.id}\t${model.displayName}${variants}`);
  }
}

class SdkSession {
  private constructor(
    private readonly agent: SDKAgent,
    private readonly force: boolean,
    private readonly mode: RuntimeMode,
    private readonly model: ModelSelection
  ) {}

  static async create(options: SdkRunOptions): Promise<SdkSession> {
    const model: ModelSelection = { id: options.model };
    const common = {
      apiKey: options.apiKey,
      model,
      name: `slice-agent-runner ${options.config.projectId}`,
    };

    const agent =
      options.mode === "cloud"
        ? await Agent.create({
            ...common,
            cloud: {
              repos: [
                {
                  url: githubUrl(options.config),
                  startingRef: options.config.integrationBranch,
                },
              ],
              autoCreatePR: options.autoPr,
              skipReviewerRequest: true,
            },
          })
        : await Agent.create({
            ...common,
            local: {
              cwd: options.config.localPath,
            },
          });

    return new SdkSession(agent, options.force, options.mode, model);
  }

  async send(
    prompt: string,
    onEvent: (event: RunnerEvent) => void
  ): Promise<SdkRunSuccess> {
    let run: Run;

    try {
      run = await this.agent.send(prompt, {
        ...(this.mode === "local" ? { model: this.model } : {}),
        ...(this.mode === "local" && this.force
          ? { local: { force: true } }
          : {}),
      });
    } catch (error) {
      if (error instanceof CursorAgentError) {
        throw new Error(
          `Cursor SDK startup failed: ${error.message}; retryable=${error.isRetryable}`
        );
      }
      throw error;
    }

    onEvent({
      type: "status",
      status: "RUN_STARTED",
      message: `agentId=${this.agent.agentId} runId=${run.id}`,
    });

    for await (const event of run.stream()) {
      emitSdkMessage(event, onEvent);
    }

    const result = await run.wait();
    onEvent({
      type: "result",
      status: result.status,
      durationMs: result.durationMs,
      agentId: this.agent.agentId,
      runId: run.id,
    });

    return {
      agentId: this.agent.agentId,
      runId: run.id,
      result,
    };
  }

  async dispose(): Promise<void> {
    await this.agent[Symbol.asyncDispose]();
  }
}

function githubUrl(config: RunnerConfig): string {
  if (config.githubSlug && config.githubSlug !== "OWNER/REPO") {
    return `https://github.com/${config.githubSlug.replace(/\.git$/, "")}`;
  }

  const remote = runGit(config.localPath, ["config", "--get", "remote.origin.url"]);
  const normalized = remote ? normalizeGitHubRemote(remote) : undefined;

  if (!normalized) {
    throw new Error(
      "Cloud mode requires githubSlug or a GitHub remote.origin.url."
    );
  }

  return normalized;
}

function runGit(cwd: string, args: string[]): string | undefined {
  try {
    return execFileSync("git", ["-C", cwd, ...args], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return undefined;
  }
}

function normalizeGitHubRemote(remote: string): string | undefined {
  const trimmed = remote.trim().replace(/\.git$/, "");
  const sshMatch = trimmed.match(/^git@github\.com:(.+\/.+)$/);
  const sshUrlMatch = trimmed.match(/^ssh:\/\/git@github\.com\/(.+\/.+)$/);
  const httpsMatch = trimmed.match(/^https:\/\/github\.com\/(.+\/.+)$/);
  const repoPath = sshMatch?.[1] ?? sshUrlMatch?.[1] ?? httpsMatch?.[1];

  return repoPath ? `https://github.com/${repoPath}` : undefined;
}

function emitSdkMessage(
  event: SDKMessage,
  emit: (event: RunnerEvent) => void
): void {
  switch (event.type) {
    case "assistant":
      for (const block of event.message.content) {
        if (block.type === "text") {
          emit({ type: "assistant_delta", text: block.text });
        } else {
          emit({
            type: "tool",
            callId: block.id,
            name: block.name,
            params: summarizeToolArgs(block.name, block.input),
            status: "requested",
          });
        }
      }
      break;
    case "thinking":
      emit({ type: "thinking", text: event.text });
      break;
    case "tool_call":
      emit({
        type: "tool",
        callId: event.call_id,
        name: event.name,
        params: summarizeToolArgs(event.name, event.args),
        status: event.status,
      });
      break;
    case "status":
      emit({
        type: "status",
        status: event.status,
        message: event.message,
      });
      break;
    case "task":
      emit({ type: "task", status: event.status, text: event.text });
      break;
    default:
      break;
  }
}

function summarizeToolArgs(toolName: string, args: unknown): string | undefined {
  if (!args || typeof args !== "object") {
    return undefined;
  }

  const record = args as Record<string, unknown>;
  const lowerName = toolName.toLowerCase();
  const keys = lowerName.includes("shell")
    ? ["command", "cwd", "working_directory"]
    : ["path", "file", "target_file", "pattern", "query", "command"];
  const parts: string[] = [];

  for (const key of keys) {
    const value = formatArgValue(record[key]);
    if (value) {
      parts.push(`${key}=${value}`);
    }
  }

  return parts.length ? parts.join(" ") : undefined;
}

function formatArgValue(value: unknown): string | undefined {
  if (typeof value === "string") {
    return shorten(value.replace(/\s+/g, " ").trim());
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return `[${value.slice(0, 3).map(formatArgValue).filter(Boolean).join(",")}]`;
  }
  return undefined;
}

function shorten(value: string, maxLength = 120): string {
  return value.length <= maxLength ? value : `${value.slice(0, maxLength - 3)}...`;
}
