# Example workspace configuration

A copyable Drake configuration: a dependency tree, a backlog, slice detail docs, a harness
config and a wrapper script — the shape a repository has once Drake is installed in it.

This is deliberately small. Its job is to be parroted: copy the files into your repository,
replace the slices with your own, point the config at your harness, and delete what you do
not need.

## What is here

| Path | What it is |
| --- | --- |
| `.drake/slice-pipeline.config.json` | The harness-neutral config. Harness id, tree/backlog paths, validation commands, branch prefix. |
| `.docs/slice_dependency_tree.json` | What the selector reads: state, dependencies, automation eligibility, priority. |
| `.docs/slice_backlog.md` | The same work in prose, for people. |
| `.docs/slices/*.md` | One detail document per slice, with its acceptance and validation. |
| `.clinerules` | Guardrails Cline reads. Equivalent files exist for other harnesses (`AGENTS.md`, `CLAUDE.md`). |
| `scripts/run-slice.sh` | Wrapper: runs the next ready slice through the configured harness. |

## Use it

1. Install the pipeline into your repository (see `docs/getting-started.md`). The installer
   writes the canonical assets; this directory shows the *content* you author on top of them.
2. Copy `.drake/slice-pipeline.config.json`, `.docs/` and `.clinerules` in, and fill in the
   placeholders — `githubSlug` is the one the runner refuses to accept as `OWNER/REPO`, which
   is deliberate: an unfilled config should fail loudly rather than run somewhere unintended.
3. Verify the wiring before spending a token:

```bash
./scripts/run-slice.sh --dry-run
./scripts/run-slice.sh --harness generic \
  --harness-command "bash scripts/harness_stub.sh {prompt_file}"
```

4. Run a slice: `./scripts/run-slice.sh`.

## Choosing a harness

`harness.id` names who does the editing: `claude`, `codex`, `cursor`, `cline`, `aider`, or
`generic` with a command you supply. The catalogue, the exact invocations and the entry
points each harness reads are in [`docs/harnesses.md`](../../docs/harnesses.md).

Cline is configured here, so the worked example is Cline: install it, authenticate once, and
let the runner hand it one slice at a time.

```bash
npm i -g cline      # then:
cline auth
```

`--auto-approve true` (what the catalogue preset passes) means Cline may edit files and run
commands without asking. Treat the branch as disposable, review the evidence record the run
leaves in `.drake/runs/`, and constrain shell access with `CLINE_COMMAND_PERMISSIONS`:

```bash
export CLINE_COMMAND_PERMISSIONS='{"allow": ["git *", "pytest *"], "deny": ["sudo *", "rm -rf *"]}'
```

## What is mine and what is Drake's

- **Drake owns the machinery and the recommendations**: the installer, the harness catalogue,
  the schemas, this example, the gate, the run chain and its exit codes.
- **You own the configuration and the content**: your tree, your backlog, your slice documents,
  your rules, your validation commands — and anything private, which stays in your own
  repository.

That split is why a workspace like this can be private while the system it runs is public.
