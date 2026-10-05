# Cloud Secrets (names only)

Canonical practices: [.docs/secrets_environment_practices.md](.docs/secrets_environment_practices.md)

Store values in **Cursor → Cloud Agents → Secrets** for the environment each automation uses. **Do not commit real tokens** to this repo. For project-level `.env.example`, UAT, and production rules, follow [`.docs/secrets_environment_practices.md`](.docs/secrets_environment_practices.md).

Copy to `SECRETS.local.md` (gitignored) if you want a private local checklist with filled-in notes.

## Naming rules

- Store token values raw; do not include `Bearer ` in secret values.
- Use `_URL` for webhook URLs and `_TOKEN` for bearer tokens.
- Project-specific webhook env vars must match `.docs/projects-registry.json`.
- Keep browser-exposed env vars out of this file unless they are explicitly public and non-secret.

## Required for hands-off PR lifecycle

| Secret | Used by | Value shape |
| --- | --- | --- |
| `GH_TOKEN` | slice-pipeline workers (all repos) | GitHub PAT; classic `repo` scope or fine-grained with PR + Contents + Metadata |

## Model override (avoid premium defaults)

| Secret | Used by | Value shape |
| --- | --- | --- |
| `CURSOR_MODEL` | slice-agent-runner SDK / optional Cloud Agent override | **Omit** unless intentionally pinning `composer-2.5`. Do **not** set to `gpt-5.5` or other premium slugs — that overrides automation cost controls. |

Runtime model for **Cursor Automations** (slice-pipeline, orchestrator) is set in **Automations → Model dropdown**, not via prompt text. After editing an automation prompt in the UI, re-select **Composer 2.5** before Save (see [AUTOMATIONS.md](AUTOMATIONS.md) § Model drift troubleshooting).

## Portfolio orchestrator (drake)

The orchestrator uses **two webhook roles**:

1. **Outbound (orchestrator → workers):** secrets on the orchestrator automation
2. **Inbound (workers → orchestrator):** orchestrator's own webhook trigger URL/token, copied onto workers

### Outbound — set on portfolio-plan-orchestrator

| Secret | Purpose |
| --- | --- |
| `EXAMPLE_APP_SLICE_PIPELINE_WEBHOOK_URL` | Worker webhook URL for example-app slice-pipeline |
| `EXAMPLE_APP_SLICE_PIPELINE_WEBHOOK_TOKEN` | Raw token only (curl adds `Bearer ` prefix) |
| `EXAMPLE_PORTFOLIO_SLICE_PIPELINE_WEBHOOK_URL` | Worker webhook URL for the portfolio governance repo |
| `EXAMPLE_PORTFOLIO_SLICE_PIPELINE_WEBHOOK_TOKEN` | Raw token only |
| `EXAMPLE_SERVICE_SLICE_PIPELINE_WEBHOOK_URL` | Worker webhook URL for a second project (when enabled) |
| `EXAMPLE_SERVICE_SLICE_PIPELINE_WEBHOOK_TOKEN` | Raw token only |
| `EXAMPLE_SECOND_APP_SLICE_PIPELINE_WEBHOOK_URL` | Worker webhook URL for example-app (when enabled) |
| `EXAMPLE_SECOND_APP_SLICE_PIPELINE_WEBHOOK_TOKEN` | Raw token only |
| `EXAMPLE_APP_WEB_SLICE_PIPELINE_WEBHOOK_URL` | Worker webhook URL for example-app |
| `EXAMPLE_APP_WEB_SLICE_PIPELINE_WEBHOOK_TOKEN` | Raw token only |

Env var names must match your registry's `webhook_env` entries. See
[`.docs/examples/projects-registry.example.json`](.docs/examples/projects-registry.example.json)
for the shape.

### Inbound — orchestrator webhook trigger

Enable **Webhook** trigger on the orchestrator automation in Cursor UI. Copy that URL/token to workers (do not commit values).

## Worker chaining back to orchestrator

Set on each **slice-pipeline** worker automation environment:

| Secret | Purpose |
| --- | --- |
| `PORTFOLIO_PLAN_ORCHESTRATOR_WEBHOOK_URL` | Orchestrator's inbound webhook URL (from orchestrator automation settings) |
| `PORTFOLIO_PLAN_ORCHESTRATOR_WEBHOOK_TOKEN` | Raw token only |

## Legacy repo-local chaining (single-repo mode)

Use only when portfolio orchestrator is paused:

| Secret | Used on | Purpose |
| --- | --- | --- |
| `PLAN_NEXT_SLICE_WEBHOOK_URL` | slice-pipeline worker | Repo-local plan-next-slice webhook |
| `PLAN_NEXT_SLICE_WEBHOOK_TOKEN` | slice-pipeline worker | Raw token only |
| `SLICE_PIPELINE_WEBHOOK_URL` | plan-next-slice worker | Repo-local slice-pipeline webhook |
| `SLICE_PIPELINE_WEBHOOK_TOKEN` | plan-next-slice worker | Raw token only |

## Verification commands (local operator)

```bash
test -n "$GH_TOKEN" && gh auth status
# Webhook smoke (replace URL/token placeholders):
# curl -sS -X POST "$PORTFOLIO_PLAN_ORCHESTRATOR_WEBHOOK_URL" \
#   -H "Authorization: Bearer $PORTFOLIO_PLAN_ORCHESTRATOR_WEBHOOK_TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{"trigger_reason":"manual_smoke","fanout_limit":3}'
```
