import { exec } from "node:child_process";
import { promisify } from "node:util";

import type { RunnerConfig, SelectedSlice } from "./types.js";

const execAsync = promisify(exec);

/**
 * The selector exits non-zero when nothing is runnable, which is a normal state
 * (a repo can legitimately have no ready, unblocked, automation-eligible slice).
 * Surfacing that as "Error: Command failed: ..." makes a healthy scheduler look
 * broken, so it gets its own error type and its own message.
 */
export class NoRunnableSliceError extends Error {
  constructor() {
    super(
      "no runnable slice: nothing is ready, unblocked, and automation-eligible"
    );
    this.name = "NoRunnableSliceError";
  }
}

export async function selectNextSlice(
  config: RunnerConfig
): Promise<SelectedSlice> {
  let stdout: string;

  try {
    ({ stdout } = await execAsync(config.sliceSelectorCommand, {
      cwd: config.localPath,
      maxBuffer: 10 * 1024 * 1024,
    }));
  } catch (error) {
    const failure = error as {
      stdout?: string;
      stderr?: string;
      code?: number | string;
    };
    const payload = parseSelectorOutputOrUndefined(failure.stdout ?? "");

    if (payload && Array.isArray(payload.selected) && payload.selected.length === 0) {
      throw new NoRunnableSliceError();
    }

    const exit = failure.code === undefined ? "" : ` (exit ${failure.code})`;
    const stderr = (failure.stderr ?? "").trim();
    throw new Error(
      `selector command failed${exit}: ${config.sliceSelectorCommand}` +
        (stderr ? `\n${stderr}` : "")
    );
  }

  const parsed = parseSelectorOutput(stdout);
  const selected = Array.isArray(parsed.selected) ? parsed.selected[0] : undefined;

  if (!selected || typeof selected !== "object") {
    throw new Error("selector output did not contain selected[0]");
  }

  const record = selected as Record<string, unknown>;
  const targetSliceId = stringField(record, [
    "target_slice_id",
    "slice_id",
    "id",
  ]);
  const targetSliceTitle = stringField(record, [
    "target_slice_title",
    "title",
    "summary",
  ]);
  const targetSliceNumber = numberField(record, [
    "target_slice_number",
    "slice_number",
    "rank",
    "number",
  ]);
  const fanoutLimit =
    numberField(parsed as Record<string, unknown>, [
      "fanout_limit",
      "default_fanout_limit",
    ]) ?? 1;

  if (!targetSliceId) {
    throw new Error("selector selected[0] is missing a slice id");
  }

  return {
    targetSliceId,
    targetSliceTitle: targetSliceTitle ?? targetSliceId,
    targetSliceNumber,
    fanoutLimit,
    raw: parsed,
  };
}

function parseSelectorOutputOrUndefined(
  stdout: string
): Record<string, unknown> | undefined {
  try {
    return parseSelectorOutput(stdout);
  } catch {
    return undefined;
  }
}

function parseSelectorOutput(stdout: string): Record<string, unknown> {
  const trimmed = stdout.trim();

  if (!trimmed) {
    throw new Error("selector produced no stdout");
  }

  try {
    return JSON.parse(trimmed) as Record<string, unknown>;
  } catch {
    const jsonStart = trimmed.indexOf("{");
    const jsonEnd = trimmed.lastIndexOf("}");
    if (jsonStart === -1 || jsonEnd === -1 || jsonEnd <= jsonStart) {
      throw new Error("selector stdout was not JSON");
    }

    return JSON.parse(trimmed.slice(jsonStart, jsonEnd + 1)) as Record<
      string,
      unknown
    >;
  }
}

function stringField(
  record: Record<string, unknown>,
  keys: string[]
): string | undefined {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }

  return undefined;
}

function numberField(
  record: Record<string, unknown>,
  keys: string[]
): number | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === "string" && value.trim()) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
  }

  return null;
}
