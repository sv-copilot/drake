# Example configuration

Drake is the machinery. A **configuration** is what you author on top of it: which slices
exist, what order they run in, who implements them, and how a slice proves itself done.
This page is the recommendation for that configuration, so a workspace does not have to be
invented from scratch.

Worked example: [`examples/governed-workspace/`](../examples/governed-workspace/README.md) —
a complete, validated configuration you can copy.

## What you author

| Artifact | Purpose |
| --- | --- |
| `.drake/slice-pipeline.config.json` | Harness id, tree/backlog paths, branch prefix, validation commands |
| `.docs/slice_dependency_tree.json` | What the selector reads: state, dependencies, priority, automation eligibility |
| `.docs/slice_backlog.md` | The same work in prose, for people |
| `.docs/slices/<SLICE>.md` | One detail document per slice: goal, acceptance, validation |
| Your harness's entry points | `AGENTS.md` for most, `.clinerules` for Cline, `CLAUDE.md` + `.claude/agents/` for Claude Code |
| `.docs/examples/projects-registry.example.json` | Optional, multi-project: worker registrations (`id`, `name`, `local_path`, `github_slug`, `integration_branch`, `priority`, `bootstrap_maturity`, `readiness`) with worker entries (`worker_id`, `adapter_type`, `role`, `automation_id`, `model_slug`, `enabled`, `primary`, `webhook_env`, `credential_refs`) |

## 1. Install the machinery

```bash
python3 scripts/sync_slice_pipeline_local.py --target /path/to/your-repo --mode install \
  --project-name "Your Product" --project-id your-product --github-slug your-org/your-repo \
  --validation-commands "bash scripts/ci_preflight.sh" --harnesses cline
```

The installer writes the canonical assets and the entry points for the harnesses you name.
`--harnesses` takes a list (`--harnesses cline,cursor`): each harness gets exactly the files
it reads, generated from one canonical copy.

## 2. Write the config

The installer drafts `.drake/slice-pipeline.config.json`; fill in what it cannot know.
`githubSlug` is the exception to "fill everything in": the runner refuses the literal
`OWNER/REPO`, so an unfilled config fails loudly instead of running somewhere unintended.

`validationCommands` is the one field worth real thought: it is what "proves" a slice after
the fact. Point it at the check you would run before merging by hand.

## 3. Choose your harness

`harness.id` names who edits the code. It is a field, not an architectural decision: the same
workspace runs with a different entry when you change it.

| id | who implements | why you would pick it |
| --- | --- | --- |
| `cline` | Cline CLI | open source, headless, cheap models — the worked example here |
| `claude` | Claude Code | strongest at multi-file refactors, `-p` headless |
| `codex` | Codex CLI | sandboxed `codex exec`, good CI manners |
| `cursor` | Cursor CLI | `cursor-agent -p`, if Cursor is already your editor |
| `aider` | Aider | prompt-as-file, leaves committing to you |
| `generic` | any command | your own wrapper, or a harness we have not verified |

Per-harness invocations, entry points, auth and caveats: [`docs/harnesses.md`](harnesses.md).
Nothing here assumes any of them: no SDK, no vendor credential held by the framework.

**Cline specifically:** `npm i -g cline`, then `cline auth`. The preset passes
`--auto-approve true`, which is what allows unattended edits — so use a disposable branch,
read the evidence record afterwards, and restrict shell access with
`CLINE_COMMAND_PERMISSIONS. Headless mode triggers automatically because the runner is not a
terminal: it redirects output, which is exactly the condition Cline uses.

## 4. Author the tree

States do the work: `ready` is work the selector may hand out, `gated` waits for a person, and
`automation_eligible: false` keeps a slice out of unattended runs even when it is ready.
`operator_gates` must agree with the state — a slice with gates and `state: ready` is a
contradiction the validator rejects. Priority is ascending, and the slice number breaks ties.

```bash
python3 scripts/validate_slice_dependency_tree.py --tree .docs/slice_dependency_tree.json
```

## 5. Verify before spending a token

```bash
./scripts/run-slice.sh --dry-run     # the packet, the command and the prompt, nothing runs
./scripts/run-slice.sh --harness generic \
  --harness-command "bash scripts/harness_stub.sh {prompt_file}"
```

The stub harness writes one file and exits, so selection, packet, prompt, run directory and
evidence can all be checked before a model is involved.

## 6. Run, and read what it leaves

Each run writes `.drake/runs/<run-label>/`: `task-packet.json`, `prompt.txt`, the harness's
own `harness-stdout.log`/`harness-stderr.log`, and `evidence.json` with the changed files.
Validate them offline with `python3 scripts/validate_run_artifacts.py --run <dir>`.

Exit codes are the interface: `0` ran, `1` configuration or startup error, `2` the harness
ran but failed, `3` nothing runnable. `3` is a normal state, not a fault — that is what makes
this schedulable.

## 7. Put it in CI

Scope the check to your repository, and keep the same discipline Drake uses on itself: the
gate runs the adoption path, not just the unit tests. `scripts/ci_preflight.sh` +
`scripts/adoption_smoke.sh` + `scripts/adoption_chain_retest.sh` are the pieces; the reason
they exist is that a gate which only tests the framework flatters the framework.

## Our own workspace is one instantiation

The repository this ships from keeps its strategy, registry and live automation in a private
tree, and treats the public machinery as the source of the recommendations above. That is the
intended shape: **the system is public, the instantiation is yours.**
