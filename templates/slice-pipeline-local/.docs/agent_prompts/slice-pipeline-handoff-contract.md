# Slice Pipeline Handoff Contract

This contract keeps the `slice-pipeline` parent automation and its approved
project subagents aligned. Use it when a subagent summary is large enough to
write a runtime handoff file under `.cursor/automation-runs/`.

Runtime handoff files are private execution artifacts and must not be committed.

## JSON Shape

```json
{
  "path": "A|B|STOP",
  "target_repo_id": "{{PROJECT_ID}}",
  "target_slice_id": "SLICE-...",
  "target_slice_number": null,
  "target_slice_title": "",
  "target_github_slug": "{{GITHUB_SLUG}}",
  "target_local_path": "{{LOCAL_PATH}}",
  "integration_branch": "{{INTEGRATION_BRANCH}}",
  "dependency_tree_path": "{{DEPENDENCY_TREE_PATH}}",
  "slice_backlog_path": "{{SLICE_BACKLOG_PATH}}",
  "slice_detail_dir": "{{SLICE_DETAIL_DIR}}",
  "fanout_limit": 1,
  "trigger_reason": "manual_test_auto_select",
  "open_pr_url": null,
  "branch": null,
  "pr_url": null,
  "pr_state": null,
  "merge_action": null,
  "docs_sync_result": null,
  "validation_summary": "",
  "subagent_summaries": [],
  "webhook_chaining_result": null,
  "sdk_agent_id": null,
  "sdk_run_id": null,
  "sdk_runtime": null,
  "sdk_model": null,
  "events_jsonl": null,
  "blockers": []
}
```

## Field Rules

- `path` is the routing decision from `/slice-preflight`.
- `A` means `/pr-babysitter` owns an existing target PR.
- `B` means `/slice-implementer` creates the target PR.
- `STOP` means no implementation or babysitting subagent should run.
- `target_slice_id`, `target_github_slug`, and `integration_branch` are required
  for all paths.
- `open_pr_url` is required for Path A.
- `pr_url` is required after Path B opens a PR.
- `docs_sync_result` should state the command run, whether docs changed, and
  whether the next selected slice advanced.
- `sdk_agent_id` and `sdk_run_id` should be set when the run was launched by
  `slice-agent-runner`.
- `sdk_runtime` should be `local` or `cloud` when applicable.
- `sdk_model` should record the Cursor model used by the SDK runner.
- `events_jsonl` should point to the relative `.cursor/automation-runs/...`
  event stream written by the SDK runner.
- `blockers` must be an array of plain strings, empty only when the run can
  proceed or has completed successfully.
- `subagent_summaries` should contain concise final summaries from the invoked
  subagents, not full transcripts.

## Handoff Discipline

The parent orchestrator must pass explicit structured fields to each subagent.
Subagents start with isolated context and should not rely on prior parent-chat
history.

Use the inline final summary when the run is simple. Use a runtime JSON file
when validation logs, PR metadata, or webhook responses would make the chat
handoff noisy.

When using the SDK runner, keep `events_jsonl`, `prompt.txt`, `payload.json`,
`metadata.json`, and `result.json` under `.cursor/automation-runs/<run-id>/`.
These files are private runtime artifacts and must not be committed.
