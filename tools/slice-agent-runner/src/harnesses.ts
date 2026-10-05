import fs from "node:fs";
import path from "node:path";

/**
 * The harness catalogue.
 *
 * Drake does not care which agent implements a slice: the runner renders a task
 * packet and a prompt, hands them to whatever harness the repository configures,
 * and records what happened. This file is the behavioural source of truth for the
 * built-in presets; docs/harnesses.md, adapters/harnesses.json and the installer
 * mirror the same ids, and a test fails if they drift apart.
 *
 * Every invocation below was checked against the vendor's own documentation on the
 * date in `verifiedOn`. Flags move between releases: the vendor's docs win.
 */

export type PromptDelivery = "argv" | "stdin" | "file";

export type HarnessPreset = {
  id: string;
  name: string;
  /** Binary looked up on PATH, or null when the harness is a custom command. */
  binary: string | null;
  promptDelivery: PromptDelivery;
  /**
   * Arguments after the binary. Placeholders: {prompt}, {prompt_file}, {model}.
   * An argument pair whose flag takes {model} is dropped entirely when no model
   * is configured, so the harness falls back to its own default.
   */
  args: string[];
  /** Where the harness keeps its own repo configuration, when it has one. */
  configDir: string | null;
  /** Environment variable names the harness authenticates with (names only). */
  authEnv: string[];
  docsUrl: string;
  verifiedOn: string;
  notes: string;
};

export const HARNESSES: HarnessPreset[] = [
  {
    id: "claude",
    name: "Claude Code",
    binary: "claude",
    promptDelivery: "argv",
    args: [
      "-p",
      "{prompt}",
      "--output-format",
      "json",
      "--permission-mode",
      "acceptEdits",
      "--model",
      "{model}",
    ],
    configDir: ".claude",
    authEnv: ["ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"],
    docsUrl: "https://code.claude.com/docs/en/headless",
    verifiedOn: "2026-10-05",
    notes:
      "-p prints and exits; --permission-mode acceptEdits lets it write files without prompting. Use dontAsk for locked-down CI.",
  },
  {
    id: "codex",
    name: "Codex CLI",
    binary: "codex",
    promptDelivery: "argv",
    args: [
      "exec",
      "--sandbox",
      "workspace-write",
      "--model",
      "{model}",
      "{prompt}",
    ],
    configDir: ".codex",
    authEnv: ["OPENAI_API_KEY", "CODEX_API_KEY"],
    docsUrl: "https://developers.openai.com/codex/",
    verifiedOn: "2026-10-05",
    notes:
      "exec runs headless; --sandbox workspace-write permits edits without network. Upstream deprecated --full-auto in favour of the explicit sandbox flag. Add --json for an event stream.",
  },
  {
    id: "cursor",
    name: "Cursor CLI",
    binary: "cursor-agent",
    promptDelivery: "argv",
    args: ["-p", "--force", "--model", "{model}", "{prompt}"],
    configDir: ".cursor",
    authEnv: ["CURSOR_API_KEY"],
    docsUrl: "https://cursor.com/docs/cli/headless",
    verifiedOn: "2026-10-05",
    notes:
      "Print mode without --force only proposes changes. Some installations expose the binary as `agent`.",
  },
  {
    id: "aider",
    name: "Aider",
    binary: "aider",
    promptDelivery: "file",
    args: [
      "--message-file",
      "{prompt_file}",
      "--yes-always",
      "--no-auto-commits",
      "--model",
      "{model}",
    ],
    configDir: ".aider",
    authEnv: ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
    docsUrl: "https://aider.chat/docs/scripting.html",
    verifiedOn: "2026-10-05",
    notes:
      "--no-auto-commits leaves committing to your promotion flow. --message-file avoids argv limits on long prompts.",
  },
  {
    id: "generic",
    name: "Any harness (bring your own command)",
    binary: null,
    promptDelivery: "file",
    args: [],
    configDir: null,
    authEnv: [],
    docsUrl: "docs/harnesses.md",
    verifiedOn: "2026-10-05",
    notes:
      "Set harness.command (or --harness-command) with {prompt_file}, {prompt} or {model} placeholders. The command runs through a shell, so the runner can drive any CLI, including Cline, Goose, OpenHands, or your own script.",
  },
];

export function findHarness(id: string): HarnessPreset | undefined {
  return HARNESSES.find((preset) => preset.id === id);
}

export function harnessIds(): string[] {
  return HARNESSES.map((preset) => preset.id);
}

export function binaryOnPath(binary: string): string | undefined {
  const pathValue = process.env.PATH ?? "";
  for (const dir of pathValue.split(path.delimiter)) {
    if (!dir) continue;
    const candidate = path.join(dir, binary);
    try {
      fs.accessSync(candidate, fs.constants.X_OK);
      return candidate;
    } catch {
      continue;
    }
  }
  return undefined;
}

export type HarnessInvocation = {
  argv: string[];
  useShell: boolean;
  display: string;
  promptDelivery: PromptDelivery;
};

export type InvocationInputs = {
  prompt: string;
  promptFile: string;
  model: string | null;
  command: string | null;
};

function substitute(template: string, inputs: InvocationInputs): string {
  return template
    .replaceAll("{prompt_file}", inputs.promptFile)
    .replaceAll("{prompt}", inputs.prompt)
    .replaceAll("{model}", inputs.model ?? "");
}

export function buildInvocation(
  preset: HarnessPreset,
  inputs: InvocationInputs
): HarnessInvocation {
  if (preset.binary === null) {
    const command = (inputs.command ?? "").trim();
    if (!command) {
      throw new Error(
        `harness "${preset.id}" needs a command: set harness.command in the config or pass --harness-command`
      );
    }
    const substituted = substitute(command, inputs);
    const shell = process.env.DRAKE_HARNESS_SHELL || "/bin/sh";
    return {
      argv: [shell, "-c", substituted],
      useShell: true,
      display: `[shell] ${substituted}`,
      promptDelivery: preset.promptDelivery,
    };
  }

  const argv: string[] = [];
  for (let index = 0; index < preset.args.length; index += 1) {
    const arg = preset.args[index];
    const next = preset.args[index + 1];

    // Drop a flag whose only value is an unconfigured {model}, so the harness
    // uses its own default instead of receiving an empty model name.
    if (next === "{model}" && !inputs.model) {
      index += 1;
      continue;
    }
    if (arg === "{model}" && !inputs.model) {
      continue;
    }
    if (arg === "{prompt}" && preset.promptDelivery !== "argv") {
      continue;
    }
    if (arg === "{prompt_file}" && preset.promptDelivery !== "file") {
      continue;
    }
    argv.push(substitute(arg, inputs));
  }

  return {
    argv: [preset.binary, ...argv],
    useShell: false,
    display: [preset.binary, ...argv].join(" "),
    promptDelivery: preset.promptDelivery,
  };
}
