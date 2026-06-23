# Agent Automations

This file defines automation guardrails for `{{PROJECT_NAME}}`.

## Shared Rules

- Allow bounded concurrent `{{FEATURE_BRANCH_PREFIX}}*` PRs only for distinct dependency-independent slices from `{{DEPENDENCY_TREE_PATH}}`. Legacy {{LEGACY_FEATURE_BRANCH_PREFIXES}} branches are tolerated during migration but should not be used for new work.
- The reusable `slice-pipeline-local` profile keeps local runs strict: one slice, one PR, no fan-out.
- Never run the same target slice concurrently.
- `ai-dev` integration merges require documented passing local validation. Hosted CI failures caused only by billing, runner availability, or hosted-minute limits may be bypassed for `ai-dev` with operator approval.
- `dev` promotion and `main` protection require GitHub Actions checks to pass.
- Keep webhook secrets in automation settings or local secret stores, never in committed docs.

## Automation Execution Policy

Canonical policy: `.docs/agent_automation_execution_policy.md`

- Follow the repo-approved automation model.
- No subagents / Task / explore unless operator explicitly asks in-thread or the run uses the approved slice-pipeline exception.
- One slice, one PR, no fan-out.

Enforcement: `.cursor/hooks.json` can block Task/subagent usage by default and
allowlist only the approved slice-pipeline subagents.

## Slice-Pipeline Subagent Orchestration

The `slice-pipeline` worker is an operator-approved exception to the default
no-subagent rule. The parent automation remains the orchestrator and may invoke
only these project subagents:

- `.cursor/agents/slice-preflight.md` - normalize payload, verify preflight, and return Path A, Path B, or STOP.
- `.cursor/agents/pr-babysitter.md` - Path A only; fix and merge an existing target slice PR when eligible.
- `.cursor/agents/slice-implementer.md` - Path B only; implement exactly one target slice and open its PR.

The shared handoff schema is `.docs/agent_prompts/slice-pipeline-handoff-contract.md`.
Runtime handoff artifacts belong under `.cursor/automation-runs/` and must not
be committed.

SDK runner defaults are stored in `.cursor/slice-pipeline-local.config.json`.
When `slice-agent-runner` launches a run, it writes prompt, payload, event, and
result artifacts under `.cursor/automation-runs/<run-id>/`; those files are
runtime-only and must stay untracked.

## Chaining Modes

### Portfolio-Orchestrated Mode

- Scheduler: portfolio orchestrator.
- Worker: repo-local `slice-pipeline`.
- Worker chaining target:
  - `{{PORTFOLIO_WEBHOOK_URL_ENV}}`
  - `{{PORTFOLIO_WEBHOOK_TOKEN_ENV}}`
- Orchestrator dispatch payload should include:
  - `target_repo_id`
  - `target_github_slug`
  - `target_local_path`
  - `integration_branch`

### Repo-Local Mode

- Scheduler: repo-local `plan-next-slice`.
- Worker chaining target:
  - `{{LOCAL_WEBHOOK_URL_ENV}}`
  - `{{LOCAL_WEBHOOK_TOKEN_ENV}}`
- Use only when portfolio orchestration is intentionally paused or unavailable.

## Required Repo Contracts

- `AGENTS.md`, `.docs/git_workflow.md`, and `.docs/branch_conventions.md` document branch and safety policy.
- `{{SLICE_BACKLOG_PATH}}` is the human-readable slice backlog.
- `{{DEPENDENCY_TREE_PATH}}` is the machine-readable dependency graph.
- `{{SLICE_DETAIL_DIR}}/` contains target slice detail docs when the repo uses detailed slice specs.
- The selector command exists and returns a JSON object with a `selected` array:
  `{{SLICE_SELECTOR_COMMAND}}`
- Validation commands are documented and runnable without private external
  services by default:
  `{{VALIDATION_COMMANDS}}`
