---
name: slice-pipeline-local
description: Run the {{PROJECT_NAME}} slice-pipeline orchestration locally in Cursor. Use when the operator invokes /slice-pipeline-local or asks to locally test the repo's slice-pipeline worker/subagent flow.
disable-model-invocation: true
---

# Slice Pipeline Local

Use this skill to exercise the `{{PROJECT_NAME}}` slice-pipeline worker flow
inside the Cursor IDE.

## Project Defaults

| Setting | Value |
| --- | --- |
| Project ID | `{{PROJECT_ID}}` |
| GitHub slug | `{{GITHUB_SLUG}}` |
| Local path | `{{LOCAL_PATH}}` |
| Integration branch | `{{INTEGRATION_BRANCH}}` |
| Dependency tree | `{{DEPENDENCY_TREE_PATH}}` |
| Slice backlog | `{{SLICE_BACKLOG_PATH}}` |
| Slice detail directory | `{{SLICE_DETAIL_DIR}}` |
| Slice selector | `{{SLICE_SELECTOR_COMMAND}}` |
| Docs sync command | `{{DOCS_SYNC_COMMAND}}` |
| Validation commands | `{{VALIDATION_COMMANDS}}` |

## Default Mode

Run the local IDE flow as the slice-pipeline parent orchestrator:

1. Read:
   - `AGENTS.md`
   - `.docs/agent_automation_execution_policy.md`
   - `.docs/agent_automations.md`
   - `.docs/agent_prompts/slice-pipeline-automation.md`
   - `.docs/agent_prompts/slice-pipeline-handoff-contract.md`
2. Use the manual Test behavior from `.docs/agent_prompts/slice-pipeline-automation.md`.
3. Run the configured slice selector:
   ```bash
   {{SLICE_SELECTOR_COMMAND}}
   ```
4. Use only the first `selected[]` row.
5. Invoke `/slice-preflight` with the normalized payload.
6. If preflight returns `STOP`, apply **local STOP overrides** before exiting:
   - **GH_TOKEN:** continue when the only blocker is missing `GH_TOKEN` while `gh auth status` succeeds locally.
   - **Already-merged stale planning** (`stop_reason=already_merged_stale_planning`): run docs-sync recovery (step 6a) instead of stopping — do not re-implement.
   - **All other STOP reasons:** report blockers and stop unless the repo-local automation policy documents another safe local-only override.
7. If preflight returns Path A, invoke `/pr-babysitter` only.
8. If preflight returns Path B, invoke `/slice-implementer` only.
9. Keep one slice, one PR, no fan-out.
10. Before any `ai-dev` merge, confirm the configured validation commands passed
    locally and include the commands/results in the handoff. Promotion to `dev`
    or `main` requires passing GitHub Actions checks.
11. After a fresh merge in this pass **or** after step 6a recovery, run the configured docs sync command when this repo provides one:
    ```bash
    {{DOCS_SYNC_COMMAND}}
    ```
12. Re-run the configured slice selector to confirm the next runnable slice advanced.
13. After a fresh merge, trigger webhook chaining per `.docs/agent_prompts/slice-pipeline-automation.md` when env vars are set. Skip webhook chaining when the slice was already merged before this run.

### Docs-sync recovery (step 6a)

When preflight returns `STOP` with `stop_reason=already_merged_stale_planning`:

1. Prefer an existing open docs-sync PR when preflight supplies `docs_sync_pr_url` — invoke `/pr-babysitter` on that PR only.
2. Otherwise run `{{DOCS_SYNC_COMMAND}}` with preflight `--merge` and `--authoritative-next` args.
3. When the script reports changes: commit on `agent/*` (or legacy `cursor/*`), open PR to `{{INTEGRATION_BRANCH}}`, merge when validation passes.
4. Re-run the slice selector. Continue only when a runnable slice is selected.

Do not use general explore, shell, browser, or unrelated Task agents. The only
approved subagents for this workflow are `/slice-preflight`,
`/slice-implementer`, and `/pr-babysitter`.

## Preflight-Only Mode

If the operator says "preflight only", "dry run", or "wiring check":

1. Follow steps 1-5 above.
2. Do not invoke `/slice-implementer` or `/pr-babysitter`.
3. Stop after reporting the selected slice and Path A, Path B, or STOP decision.

## Required Handoff

Report:

- selected slice
- normalized payload
- preflight path
- invoked subagent summaries
- PR URL and state
- merge action
- docs sync commands run and whether selection advanced
- webhook chaining result
- SDK agent/run IDs and event artifact path when launched by `slice-agent-runner`
- blockers

For large validation logs or PR metadata, use the runtime handoff schema in
`.docs/agent_prompts/slice-pipeline-handoff-contract.md`. Runtime handoff files
belong under `.cursor/automation-runs/` and must not be committed.
