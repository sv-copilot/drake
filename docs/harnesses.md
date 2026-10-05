# Harnesses

Drake is not a coding agent. It decides *which* slice is next, renders the task
packet and the prompt, hands that to a coding harness, and records what happened
afterwards as evidence. The harness — Claude Code, Codex, Cursor, Cline, Aider, or
your own script — does the editing.

That split is why there is no SDK in this repository and no model credential in the
runner: the runner starts a child process and records its output and exit code.
Nothing in the pipeline assumes a particular vendor.

## What a harness has to provide

1. **A non-interactive invocation.** One command that takes a prompt and returns
   when finished (`claude -p`, `codex exec`, `cursor-agent -p`, `aider --message-file`).
2. **The ability to write files** in the target repository, because the evidence
   record is built from the working tree the harness leaves behind.
3. **An honest exit code.** `0` means the run finished; anything else means it did
   not, and the runner reports exit `2` and records a `failure` evidence record.
4. Optionally, a place to keep its own repo config (`.claude/`, `.codex/`, `.cursor/`).

Anything that satisfies those four is a supported harness. AI coding CLIs change
their flags between releases, so each entry below carries the date its invocation
was last checked against the vendor's documentation — **the vendor's docs win**.

## Install for your harness

```bash
python3 scripts/sync_slice_pipeline_local.py --target /path/to/repo --mode install \
  --harnesses claude            # or: cursor, codex, aider, generic, or a comma list
```

The first id becomes the `harness.id` in `.drake/slice-pipeline.config.json`. The
installer always writes the harness-neutral assets, and adds only the entry points
the harnesses you selected actually read:

- `.drake/agents/*.md`, `.drake/skills/slice-pipeline-local/SKILL.md` — canonical prompts, every harness
- `AGENTS.md` — read by Codex, Cursor and others
- `.claude/agents/*.md` + `CLAUDE.md` — Claude Code subagents and memory file
- `.cursor/agents/*.md`, `.cursor/hooks/*`, `.cursor/hooks.json` — Cursor agents and guards

Per-harness files are generated *from* the canonical ones: edit `.drake/agents/`
and re-install, rather than editing a copy.

## The catalogue

| id | harness | non-interactive invocation | docs |
| --- | --- | --- | --- |
| `claude` | Claude Code | `claude -p <prompt> --output-format json --permission-mode acceptEdits [--model <model>]` | [headless](https://code.claude.com/docs/en/headless) |
| `codex` | Codex CLI | `codex exec --sandbox workspace-write [--model <model>] <prompt>` | [docs](https://developers.openai.com/codex/) |
| `cursor` | Cursor CLI | `cursor-agent -p --force [--model <model>] <prompt>` | [headless](https://cursor.com/docs/cli/headless) |
| `cline` | Cline | `cline --auto-approve true <prompt>` | [CLI overview](https://docs.cline.bot/usage/cli-overview) |
| `aider` | Aider | `aider --message-file <prompt-file> --yes-always --no-auto-commits [--model <model>]` | [scripting](https://aider.chat/docs/scripting.html) |
| `generic` | any harness | your command, with `{prompt_file}`, `{prompt}` or `{model}` placeholders | this file |

Checked against vendor docs on 2026-10-05 (Cline: 2026-10-05). `tools/slice-agent-runner run-next
--dry-run` prints the exact command for your config, which is the fastest way to see
what would run.

### claude — Claude Code

- Entry points: `AGENTS.md`, `CLAUDE.md`, `.claude/agents/{slice-preflight,slice-implementer,pr-babysitter}.md`
- Auth: `ANTHROPIC_API_KEY`, or your own Claude Code login
- `--permission-mode acceptEdits` lets it write files without prompting; `dontAsk` is
  the locked-down CI variant. Dropping `--output-format json` is fine too, you just
  get less structure to read back.

### codex — Codex CLI

- Entry points: `AGENTS.md`
- Auth: `OPENAI_API_KEY` or `CODEX_API_KEY`, or `codex login`
- `--sandbox workspace-write` permits edits without network access. Upstream
  deprecated `--full-auto` in favour of the explicit sandbox flag, so it is not used
  here. Add `--json` yourself if you want an event stream to parse.

### cursor — Cursor CLI

- Entry points: `AGENTS.md`, `.cursor/agents/*.md`, `.cursor/hooks/*`
- Auth: `CURSOR_API_KEY` for scripted runs
- Print mode without `--force` only proposes changes. Some installations expose the
  binary as `agent`; point `harness.command` at whichever you have.

### cline — Cline

- Entry points: `AGENTS.md`, `.clinerules`
- Auth: `cline auth` (Cline Provider, ClinePass, or your own provider key). Install with `npm i -g cline`.
- Headless mode engages when stdout is redirected, stdin is piped, or `--json` is passed — all three
  happen under this runner, so a slice run is a batch task.
- `--auto-approve true` is what makes it unattended: it may edit files and run commands without
  prompting. Use a disposable branch, review the evidence record afterwards, and constrain shell
  access with `CLINE_COMMAND_PERMISSIONS` (`{"allow": ["git *", "pytest *"], "deny": ["sudo *"]}`).
- The model is whatever `cline auth` is configured with; add `--timeout` to the command if you want a
  hard ceiling on a run.

### aider — Aider

- Entry points: `AGENTS.md`
- Auth: whichever model provider you configure
- `--no-auto-commits` leaves committing to your promotion flow. The prompt is passed
  as a file (`--message-file`) so long prompts do not hit argv limits.

### generic — bring your own command

For Cline, Goose, OpenHands, a wrapper around your own tooling, or a harness whose
flags you know better than this file does:

```bash
python3 scripts/sync_slice_pipeline_local.py --target /path/to/repo --mode install \
  --harnesses generic --harness-command "claude -p {prompt_file} --permission-mode acceptEdits"
```

The command runs through a shell (`/bin/sh` by default, `DRAKE_HARNESS_SHELL` to
override), with `{prompt_file}`, `{prompt}` and `{model}` substituted. It runs with
the target repository as its working directory.

**Prove the wiring before you spend a token.** `scripts/harness_stub.sh` is a harness
that does nothing: it writes one file and exits. Point the runner at it and you can
watch selection, packet, prompt, invocation, evidence and exit codes all work with no
credentials and no model call:

```bash
python3 scripts/sync_slice_pipeline_local.py --target . --mode install \
  --harnesses generic --harness-command "bash scripts/harness_stub.sh {prompt_file}"
node tools/slice-agent-runner/dist/index.js run-next --repo .
python3 scripts/validate_run_artifacts.py --run "$(ls -dt .drake/runs/*/ | head -1)"
```

## Exit codes

| code | meaning |
| --- | --- |
| `0` | the harness ran and exited 0 |
| `1` | configuration, harness startup or selector error |
| `2` | the harness ran but exited non-zero: the slice run did not finish |
| `3` | nothing to do: no slice is ready, unblocked and automation-eligible |

Exit `3` is a normal scheduler state, not a failure — cron jobs use it to tell "no
work" apart from "something is broken".

## What a run leaves behind

Under `.drake/runs/<run-label>/`:

- `task-packet.json` — the Task Packet, conforming to `adapters/task-packet.schema.json`
- `prompt.txt` — exactly what the harness was told
- `evidence.json` — the Evidence Contract record: status, changed files, harness, timings
- `harness-stdout.log`, `harness-stderr.log` — the harness's own output, verbatim
- `events.jsonl`, `result.json`, `payload.json`, `metadata.json`

Validate any of them offline:

```bash
python3 scripts/validate_run_artifacts.py --run .drake/runs/<run-label>
```

## Adding a harness to the catalogue

Four places must agree, and a test fails if they drift:

1. `tools/slice-agent-runner/src/harnesses.ts` — the behavioural source of truth
2. `scripts/sync_slice_pipeline_local.py` — `HARNESS_IDS` and any generated entry points
3. `adapters/harnesses.json` — the machine-readable mirror
4. this file — the table and the notes

Check the invocation against the vendor's own documentation, record the date in
`verifiedOn`, and add the entry points the harness reads.
