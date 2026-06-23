---
name: slice-pipeline-local
description: Run the drake slice-pipeline orchestration locally in Cursor. Use when the operator invokes /slice-pipeline-local or asks to locally test the repo's slice-pipeline worker/subagent flow.
disable-model-invocation: true
---

# Slice Pipeline Local

Use this skill to exercise the `drake` slice-pipeline worker flow
inside the Cursor IDE.

## Project Defaults

| Setting | Value |
| --- | --- |
| Project ID | `drake` |
| GitHub slug | `sv-copilot/drake` |
| Local path | `<workspace-root>` |
| Integration branch | `ai-dev` |
| Dependency tree | `.docs/slice_dependency_tree.json` |
| Slice backlog | `.docs/slice_backlog.md` |
| Slice detail directory | `.docs/slices` |
| Slice selector | `python3 scripts/select_next_automation_slice.py --tree .docs/slice_dependency_tree.json` |
| Docs sync command | `not configured` |
| Validation commands | `python3 -m json.tool .docs/projects-registry.json >/dev/null && git diff --check` |

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
   python3 scripts/select_next_automation_slice.py --tree .docs/slice_dependency_tree.json
   ```
4. Use only the first `selected[]` row.
5. Invoke `/slice-preflight` with the normalized payload.
6. If preflight returns `STOP`, report blockers and stop unless the repo-local automation policy explicitly documents a safe local-only override.
7. If preflight returns Path A, invoke `/pr-babysitter` only.
8. If preflight returns Path B, invoke `/slice-implementer` only.
9. Keep one slice, one PR, no fan-out.
10. After a fresh merge or already-merged detection, run the configured docs sync command when this repo provides one:
    ```bash
    not configured
    ```
11. Re-run the configured slice selector to confirm the next runnable slice advanced.
12. After a fresh merge, trigger webhook chaining per `.docs/agent_prompts/slice-pipeline-automation.md` when env vars are set. Skip webhook chaining when the slice was already merged before this run.

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
