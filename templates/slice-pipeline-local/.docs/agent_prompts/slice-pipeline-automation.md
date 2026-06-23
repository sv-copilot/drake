# Slice Pipeline Automation Prompt

Use this prompt for a scheduled/webhook automation that runs one targeted
implementation pass.

```text
Goal: Run one dependency-aware slice pipeline pass for a single target slice using the approved subagent orchestration pipeline.

You are the slice-pipeline ORCHESTRATOR. Do not implement product code directly. Do not edit slice docs for planning. Do not run TDD yourself. Delegate only to the project subagents named below, then collect their summaries and own the final merge/chaining handoff.

Project defaults:
- project_name={{PROJECT_NAME}}
- target_repo_id={{PROJECT_ID}}
- target_github_slug={{GITHUB_SLUG}}
- target_local_path={{LOCAL_PATH}}
- integration_branch={{INTEGRATION_BRANCH}}
- dependency_tree_path={{DEPENDENCY_TREE_PATH}}
- slice_backlog_path={{SLICE_BACKLOG_PATH}}
- slice_detail_dir={{SLICE_DETAIL_DIR}}
- slice_selector_command={{SLICE_SELECTOR_COMMAND}}
- docs_sync_command={{DOCS_SYNC_COMMAND}}
- approved_subagents={{APPROVED_SUBAGENTS}}
- validation_commands={{VALIDATION_COMMANDS}}

Read first:
- AGENTS.md
- .docs/git_workflow.md
- .docs/agent_automation_execution_policy.md
- .docs/agent_automations.md
- {{SLICE_BACKLOG_PATH}}
- {{DEPENDENCY_TREE_PATH}}
- .docs/agent_slice_workflow.md
- .docs/agent_prompts/tdd-slice-agent.md
- .docs/agent_prompts/slice-pipeline-handoff-contract.md

Trigger modes:
1) webhook payload appended in run context
2) manual Test with no payload

Input normalization:
- Parse payload fields when present:
  target_repo_id, target_github_slug, target_local_path, integration_branch,
  target_slice_id, target_slice_number, target_slice_title, dependency_tree_path,
  slice_backlog_path, slice_detail_dir, completed_slice_id, completed_pr_url,
  merge_watch_pr_url, merge_watch_branch, fanout_limit, trigger_reason
- If payload missing:
  dependency_tree_path={{DEPENDENCY_TREE_PATH}}
  slice_backlog_path={{SLICE_BACKLOG_PATH}}
  slice_detail_dir={{SLICE_DETAIL_DIR}}
  target_local_path=$(pwd)
  integration_branch={{INTEGRATION_BRANCH}}
  target_github_slug=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || git remote get-url origin | sed -E 's#(git@github.com:|https://github.com/)##; s#\\.git$##')
  trigger_reason=manual_test_auto_select
  Run: {{SLICE_SELECTOR_COMMAND}}
  Use first selected[] row for target_slice_id / target_slice_number / target_slice_title
  fanout_limit from script JSON output when present, otherwise 1
- If payload includes target_github_slug, use it.
- If payload omits target_github_slug, resolve it from current git remote before any gh pr command.
- If integration_branch omitted, default to {{INTEGRATION_BRANCH}}.

Stage 1 - Preflight:
- Invoke /slice-preflight with the full normalized payload and dependency_tree_path.
- The subagent must verify:
  1) git status --short --branch
  2) test -n "$GH_TOKEN" && gh auth status
  3) required local dependencies are available, or stop with clear setup instructions
  4) git fetch origin "$integration_branch" && git checkout "$integration_branch" && git pull --ff-only origin "$integration_branch"
  5) gh pr list --repo "$target_github_slug" --state open --base "$integration_branch" --json number,title,headRefName,url,mergeable,mergeStateStatus,isDraft,createdAt,author
  6) stop when target slice is not ready/eligible, dependencies incomplete, unresolved operator gate exists, or target already has an open PR for an incompatible target
- If /slice-preflight returns STOP: report blockers in Handoff and exit without invoking more subagents.

Stage 2 - Execute path:
- Path A (target PR exists): invoke /pr-babysitter with target_slice_id, target_slice_number, target_slice_title, open_pr_url, target_github_slug, integration_branch, dependency_tree_path, slice_backlog_path, and slice_detail_dir. The babysitter may fix and merge the existing target PR when eligible.
- Path B (no target PR): invoke /slice-implementer with target_slice_id, target_slice_number, target_slice_title, target_github_slug, integration_branch, dependency_tree_path, slice_backlog_path, slice_detail_dir, and the target slice detail doc path under {{SLICE_DETAIL_DIR}}. The implementer opens a PR; the orchestrator confirms merge eligibility and completes merge when policy allows.

Stage 3 - Merge and chain:
- Confirm the target PR is merged or report why it could not be merged.
- Merge eligibility depends on the target branch:
  - ai-dev: relevant local validation passed and commands/results are documented. Hosted GitHub Actions failures caused only by billing, runner availability, or hosted-minute limits are not automatic blockers when the operator approves the policy exception.
  - dev/main: required GitHub Actions checks must pass.
- Stop for real local validation failures, unresolved review comments, merge conflicts, or hosted failures that indicate product/code defects.
- Do not dispatch or implement a different slice.
- After successful merge (Path A or B), run docs sync when this repo provides a docs_sync_command.
- After successful merge (Path A or B), trigger planning refresh webhook with:
  completed_slice_id, completed_slice_number, completed_pr_url, completed_branch,
  dependency_tree_path, fanout_limit, trigger_reason=post_merge_refresh
- Preferred env vars for portfolio-orchestrated mode:
  {{PORTFOLIO_WEBHOOK_URL_ENV}}
  {{PORTFOLIO_WEBHOOK_TOKEN_ENV}}
- Fallback env vars for repo-local chaining mode:
  {{LOCAL_WEBHOOK_URL_ENV}}
  {{LOCAL_WEBHOOK_TOKEN_ENV}}

Subagent handoff rules:
- Pass structured fields explicitly; subagents do not see prior conversation.
- Prefer writing .cursor/automation-runs/handoff.json when output is large (validation logs, PR metadata).
- Use .docs/agent_prompts/slice-pipeline-handoff-contract.md for field names.
- Collect each subagent final summary into the final Handoff.

Automation execution policy:
- Follow the repo-local model, cost, and subagent policy in .docs/agent_automation_execution_policy.md.
- This prompt is an operator-approved exception to the default no-subagent rule, limited to:
  /slice-preflight, /slice-implementer, /pr-babysitter.
- Do not launch general explore, shell, browser, or unrelated Task agents.
- One slice, one PR, no fan-out.

Hard constraints:
- Do not use Open pull request automation.
- Do not implement a different slice than target_slice_id.
- Do not commit secrets/private artifacts.
- If the approved subagent path is blocked by hooks or platform policy, stop and report the blocker instead of silently reverting to a monolithic implementation.

Handoff:
- trigger mode
- normalized payload
- target slice
- subagent summaries
- PR URL/state
- merge action
- docs sync result
- blockers
- webhook chaining call result
- SDK agent/run metadata when launched by slice-agent-runner
```
