# Stack decisions (example)

Copy to `.docs/stack_decisions.md` in the product repo and replace placeholders.
Keep this file **decision-focused** — link deployment detail to `.docs/deployment.md`
and UI stack notes to `.docs/frontend_stack.md` when those exist.

Canonical references:

- [new_project_practices.md](../new_project_practices.md)
- [project_bootstrap_scaffold_contract.md](../project_bootstrap_scaffold_contract.md)
- [frontend_scaffold_practices.md](../frontend_scaffold_practices.md)
- [testing_quality_practices.md](../testing_quality_practices.md)

## Project identity

| Field | Value |
| --- | --- |
| Project ID | `<project-id>` |
| GitHub slug | `sv-copilot/<project-id>` |
| Local path (current) | `<home>/<project-id>` |
| Sensitivity profile | `public-marketing` \| `private-data` \| `browser-automation` \| `rag` |
| Integration branch | `ai-dev` |
| Last reviewed | `YYYY-MM-DD` |

## Scaffold inputs (chosen at kickoff)

| Input | Choice | Notes |
| --- | --- | --- |
| Frontend profile | Product app default | Vite + React + TypeScript + TanStack Router + Tailwind + shadcn/ui |
| Backend/runtime profile | Node service | REST API colocated or separate service directory |
| Package manager | `npm` | Use `pnpm` only for workspaces/monorepos |
| UAT target | Shared DigitalOcean staging | Document host and deploy owner in `.docs/deployment.md` |
| Production target | Project-owned VPS (deferred) | No production deploy until owner and host are named |
| Secrets profile | Cursor cloud + local `.env` | Names in `.env.example` and `SECRETS.example.md` only |
| Shared-runtime intent | Local-only for now | Revisit when a second repo needs the same contract |

Frontend-only detail lives in `.docs/frontend_stack.md` when applicable.

## Stack decisions

| Area | Choice | Why | Revisit when |
| --- | --- | --- | --- |
| Language / runtime | TypeScript on Node 22 LTS | Team default; matches bootstrap web template | Node LTS EOL or major framework bump |
| Frontend | React + Vite | Fast local dev; aligns with product-app profile | Need SSR/SSG → consider Astro or Next.js |
| API style | REST over HTTP in same repo | Single deploy unit for v1 | Public third-party API consumers appear |
| Data store | Postgres 16 (managed) | Relational model fits domain | Read-heavy analytics → evaluate warehouse |
| Auth | Hosted provider (example) | Offloads OAuth/session; no custom auth in v1 | Enterprise SSO requirement |
| Hosting | Project-owned or shared UAT host | Document in `.docs/deployment.md` | Multi-region or GPU workloads |
| CI | Local validation on `ai-dev`; GitHub Actions on `dev` / `main` | Keeps agent integration fast while preserving staging and production gates | Hosted checks block promotion to staging or production |

## Validation commands

Stable script names (see [testing_quality_practices.md](../testing_quality_practices.md)):

| Gate | Command |
| --- | --- |
| Install | `npm ci` |
| Lint | `npm run lint` |
| Typecheck | `npm run typecheck` |
| Unit/component tests | `npm test` |
| Build | `npm run build` |
| Smoke/e2e | `npm run test:e2e` |

Local validation for `ai-dev` and GitHub Actions for `dev` promotion must run
all gates without real production secrets.

## Automation smoke slice

| Field | Value |
| --- | --- |
| Slice ID | `smoke-automation-001` |
| Status | `ready` |
| `automation_eligible` | `true` |
| Dependencies | none |
| Operator gate | none |
| Intent | Docs-only or trivial change proving worker dispatch and CI |

## Documented deviations from portfolio defaults

List only intentional deviations. If none, keep this section and write `None`.

| Default | Deviation | Rationale | Recorded in |
| --- | --- | --- | --- |
| Example: Vite product app | Next.js hybrid SSR | Auth-heavy SSR and dynamic SEO required | This file + `.docs/frontend_stack.md` |

## Rejected alternatives (short)

| Alternative | Reason not chosen |
| --- | --- |
| Next.js App Router for v1 | Team optimizing for Vite SPA first; SSR not required yet |
| Supabase as primary DB | Domain needs relational constraints bootstrap template does not model |
| Monorepo with portfolio parent | Product code stays in its own git root per portfolio `AGENTS.md` |

## Agent constraints

- Do not introduce a second frontend framework without updating this file and `.docs/frontend_stack.md`.
- Do not add secrets to this doc — env var **names** only; values in `.env` / Cursor secrets.
- Breaking stack changes require an ADR or slice called out in `.docs/slice_backlog.md`.

## Related product-repo files

```text
.docs/frontend_stack.md       # frontend projects only
.docs/development_playbook.md # local validation and agent pre-PR checks
.docs/deployment.md           # UAT and production ownership
.env.example                  # names/placeholders only
SECRETS.example.md            # cloud secret names only
AGENTS.md                     # repo-specific safety and branch policy
```

## Review triggers

Update this file when:

- frontend or backend stack profile changes;
- package manager, UAT host, or production target changes;
- a new external service requires secrets or env vars;
- shared-runtime extraction moves from local-only to shared package/service.
