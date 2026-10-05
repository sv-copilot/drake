import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import type { HarnessInvocation } from "./harnesses.js";

export type HarnessRunOutcome = {
  harness: string;
  command: string;
  exitCode: number;
  durationMs: number;
  status: "success" | "failure";
  stdoutPath: string;
  stderrPath: string;
};

export type HarnessRunOptions = {
  harness: string;
  invocation: HarnessInvocation;
  cwd: string;
  runDir: string;
  env: NodeJS.ProcessEnv;
  /** Delivered on stdin when the preset asks for it. */
  stdin?: string;
  onOutput?: (stream: "stdout" | "stderr", chunk: string) => void;
};

/**
 * Run one harness invocation, capturing output to the run directory.
 *
 * The harness is the only thing Drake does not own: it runs as an ordinary child
 * process, its stdout and stderr are kept verbatim, and its exit code decides
 * whether the slice attempt succeeded. No SDK, no credentials held by the runner.
 */
export async function runHarness(
  options: HarnessRunOptions
): Promise<HarnessRunOutcome> {
  const startedAt = Date.now();
  const stdoutPath = path.join(options.runDir, "harness-stdout.log");
  const stderrPath = path.join(options.runDir, "harness-stderr.log");
  const [binary, ...args] = options.invocation.argv;

  if (!binary) {
    throw new Error("harness invocation is empty");
  }

  const outFd = fs.openSync(stdoutPath, "a");
  const errFd = fs.openSync(stderrPath, "a");
  let child: ReturnType<typeof spawn>;

  try {
    child = spawn(binary, args, {
      cwd: options.cwd,
      env: options.env,
      stdio: [options.stdin === undefined ? "ignore" : "pipe", "pipe", "pipe"],
    });
  } catch (error) {
    fs.closeSync(outFd);
    fs.closeSync(errFd);
    throw error;
  }

  const exitCode = await new Promise<number>((resolve, reject) => {
    child.on("error", (error: NodeJS.ErrnoException) => {
      const message =
        error.code === "ENOENT"
          ? `harness binary not found: ${binary}. Install it, or set harness.command / --harness-command.`
          : `could not start ${binary}: ${error.message}`;
      reject(new Error(message));
    });

    child.stdout?.on("data", (chunk: Buffer) => {
      fs.writeSync(outFd, chunk);
      process.stdout.write(chunk);
      options.onOutput?.("stdout", chunk.toString());
    });
    child.stderr?.on("data", (chunk: Buffer) => {
      fs.writeSync(errFd, chunk);
      process.stderr.write(chunk);
      options.onOutput?.("stderr", chunk.toString());
    });

    if (options.stdin !== undefined && child.stdin) {
      child.stdin.write(options.stdin);
      child.stdin.end();
    }

    child.on("close", (code) => resolve(code ?? 1));
  });

  fs.closeSync(outFd);
  fs.closeSync(errFd);

  const durationMs = Date.now() - startedAt;

  return {
    harness: options.harness,
    command: options.invocation.display,
    exitCode,
    durationMs,
    status: exitCode === 0 ? "success" : "failure",
    stdoutPath,
    stderrPath,
  };
}
