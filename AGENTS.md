# AGENTS.md

Operating contract for AI agents working in a **Drake** governance repository.

Drake provides repository-native governance for AI-assisted development: slice
planning, dependency graphs, adapter contracts, and validation tooling.

## Branch policy

- `main` — stable integration branch for adopters.
- `ai-dev` — agent integration branch when using Drake automations.
- `agent/*` or `cursor/*` — feature branches for isolated slices.

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

## Cursor Cloud specific instructions

This repo is the **public OSS export** of a private Drake workspace. It is a
documentation + JSON-schema + Python-tooling repo plus one TypeScript CLI. There
are **no long-running services / servers / databases** — nothing to "boot up".

### Runtimes & deps (already provided by the update script)
- Python 3 (stdlib-only scripts) with `pytest` + `jsonschema` installed via
  `python3 -m pip install --user ...`. They land in `~/.local` (not on `PATH`);
  invoke as `python3 -m pytest` / `import jsonschema`.
- Node.js 22 + npm. CLI deps via `npm --prefix tools/slice-agent-runner ci`.

### Runnable application: `tools/slice-agent-runner` (TypeScript CLI)
- Typecheck / build / run with the `package.json` scripts (`typecheck`, `build`,
  `dev` via tsx, `start` via `dist/`).
- Commands: `check`, `models`, `preflight`, `run-next` (see `--help`).
- SDK commands (`models`, and `preflight`/`run-next` **without** `--dry-run`)
  require `CURSOR_API_KEY`. To exercise the runner end-to-end **without**
  credentials, use `check` or `run-next/preflight --dry-run` (renders the slice
  selector payload + task-packet prompt). The selector subprocess needs a repo
  with a `.cursor/slice-pipeline-local.config.json` and a slice dependency tree;
  `.docs/examples/slice_dependency_tree.example.json` provides a runnable
  `SMOKE-1` slice for demos.

### Known: `bash scripts/ci_preflight.sh` does NOT pass on this public export
This is **intentional scrub fallout, not a bug to fix** (CI has been red since
the initial export). The public scrub rewrote internal codenames to the literal
placeholders `drake` / `example-app`, and several gates depend on private
`.docs/` files that were deliberately excluded:
- `scripts/validate_drake_export.py` flags the literal string `drake` (and the
  `example-app` slug) which appear throughout the public repo by design.
- `scripts/validate_slice_dependency_tree.py` / `validate_mcp_environment_profile.py`
  need `.docs/*.schema.json` files that are not shipped here.
- `tests/test_export_drake_public.py` needs `.docs/drake_public_export_manifest.md`,
  also not shipped.
Do not try to make `ci_preflight.sh` green by editing these. The genuinely
working validation subset on this repo is: `python3 -m py_compile scripts/*.py`,
`python3 -m json.tool` on the `.docs/examples/*.json`,
`python3 scripts/validate_validation_results.py --file tests/fixtures/validation-results/sample-passed.json`,
and the `slice-agent-runner` typecheck/build/run.
