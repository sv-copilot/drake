# AGENTS.md

Operating contract for AI agents working in a **Drake** governance repository.

Drake provides repository-native governance for AI-assisted development: slice
planning, dependency graphs, adapter contracts, and validation tooling.

## Branch policy

- `main` — stable production branch for adopters.
- `rc` — release candidate (staging verification) branch.
- `dev` — agent integration branch when using Drake automations.
- `agent/*` — feature branches for isolated slices (legacy `slice/*` retired).

## Validation before PR

From repo root:

```bash
bash scripts/ci_preflight.sh
```

## Scope

- Keep product runtime code in its own repositories.
- Use `.docs/examples/` for fictional registry and slice-tree samples.
- Do not commit secrets, live automation tokens, or operator registry data.

See `docs/getting-started.md` for a minimal adoption path.

## Cursor Cloud specific instructions## Working in this repository

This repo is the **public OSS export** of a private Drake workspace: documentation,
JSON schemas, Python tooling, and one TypeScript CLI. There are **no long-running
services / servers / databases** — nothing to "boot up".

### Runtimes & deps
- Python 3, stdlib-only scripts. The gate creates a repo-local `.venv` for
  `pytest`/`jsonschema` when the system interpreter refuses installs (PEP 668).
- Node.js 22 + npm. CLI deps: `npm --prefix tools/slice-agent-runner ci`.

### Runnable application: `tools/slice-agent-runner` (TypeScript CLI)
- Typecheck / build / run via the package scripts (`typecheck`, `build`, `dev`,
  `start`).
- Commands: `check`, `harnesses`, `preflight`, `run-next` (see `--help`).
- The runner is **harness agnostic**. It renders a task packet and a prompt, launches
  whichever coding harness the repository configures (Claude Code, Codex, Cursor,
  Aider, or a command you supply), then records evidence. There is no model SDK in
  this repository and the runner holds no model credential: the harness owns its own
  authentication.
- Catalogue, per-harness invocations, generated entry points and exit codes:
  `docs/harnesses.md`.
- To exercise the whole path without credentials or a model call, install with
  `--harnesses generic --harness-command "bash scripts/harness_stub.sh {prompt_file}"`
  and run `run-next`. `scripts/harness_matrix_smoke.sh` does exactly that across the
  catalogue.
- The selector needs a repo with `.drake/slice-pipeline.config.json` (pre-0.2
  configs at `.cursor/slice-pipeline-local.config.json` still load, with a warning)
  and a slice dependency tree. `.docs/examples/slice_dependency_tree.example.json`
  provides a runnable `SMOKE-1` slice for demos.

### The gate
`bash scripts/ci_preflight.sh` is the whole gate, and it passes on a clean checkout:
compilation, export validation, dependency-tree and MCP-profile validation, the
Python suites, the runner typecheck and build, the adoption smoke, the harness matrix
smoke, and — when those directories are present — the hosted API and web suites.
**Every check is blocking**: a check that cannot run fails the gate rather than being
skipped, because a gate that hides a broken build is worse than no gate.
