# Deployment (example)

Copy to `.docs/deployment.md` in the product repo. Record **who owns** UAT and
production, **where** apps run, and **how** to deploy and roll back. Use env var
**names** only — values belong in Cursor secrets, CI secrets, or the host.

Canonical references:

- [automation_ci_deploy_practices.md](../automation_ci_deploy_practices.md)
- [secrets_environment_practices.md](../secrets_environment_practices.md)
- [stack_decisions.example.md](stack_decisions.example.md) (UAT/production targets)

## Project identity

| Field | Value |
| --- | --- |
| Project ID | `<project-id>` |
| GitHub slug | `sv-copilot/<project-id>` |
| Deploy owner (human) | `<name or team>` |
| Last reviewed | `YYYY-MM-DD` |

## UAT (staging)

| Field | Value |
| --- | --- |
| Environment | Shared DigitalOcean staging (example) |
| Branch deployed | `dev` |
| App / service name | `<project-id>-uat` |
| Public URL | `https://<host>/` (placeholder) |
| Process model | systemd unit \| Docker container \| static nginx site |
| Build artifact | `dist/` from `npm run build` on CI |
| Deploy command | Document operator or CI job name (no secrets in repo) |
| Health check | `GET /health` → `200` |
| Rollback | Redeploy previous artifact tag or `git checkout` previous release pointer |

### UAT environment variables (names only)

| Name | Layer | Notes |
| --- | --- | --- |
| `VITE_API_BASE_URL` | Client (Vite) | Public API base for browser |
| `DATABASE_URL` | Server | Managed Postgres connection string — value in host secret store |
| `NODE_ENV` | Server | Set to `production` on UAT host |

List full names in `.env.example` and `SECRETS.example.md`. Do not paste values here.

### UAT isolation

| Question | Answer |
| --- | --- |
| Shared host with other projects? | Yes (shared staging) — separate app directory or container |
| Shared database? | No — dedicated schema or instance per project |
| Private data paths mixed across apps? | No |

## Production

| Field | Value |
| --- | --- |
| Status | Deferred until owner names host and release process |
| Branch deployed | `main` |
| Target | Project-owned VPS or managed host (document when chosen) |
| Release gate | Manual approval + passing GitHub Actions on `main` |
| Secret owner | `<name>` — rotation via host/CI secret store |
| Backup / restore | Document if stateful (DB snapshots, object storage) |

When production goes live, fill the same tables as UAT with production URLs and
rollback steps. Until then, keep this section explicit so agents do not deploy to
prod by mistake.

## CI and automation notes

- Local validation on `ai-dev` validates build artifacts before integration; GitHub Actions checks gate `dev` / `main` promotion.
- Do not enable `automation_enabled=true` until UAT ownership and smoke slice are documented in [WORKSPACE.md](../../WORKSPACE.md) maturity checklist (portfolio repo).
- Smoke slice must not deploy to production or touch real secrets.

## Related product-repo files

```text
.env.example
SECRETS.example.md
.docs/stack_decisions.md
.docs/development_playbook.md
.github/workflows/ci.yml
```

## Review triggers

Update this file when:

- UAT or production host, URL, or deploy owner changes;
- a new env var is required at deploy time;
- rollback or health-check procedure changes;
- production moves from deferred to active.
