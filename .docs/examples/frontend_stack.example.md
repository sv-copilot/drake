# Frontend stack (example)

Copy to `.docs/frontend_stack.md` in frontend product repos. Cross-cutting stack
and deployment decisions belong in `.docs/stack_decisions.md`.

Canonical references:

- [frontend_scaffold_practices.md](../frontend_scaffold_practices.md)
- [stack_decisions.example.md](stack_decisions.example.md) (product-repo sibling)

## Profile

| Field | Value |
| --- | --- |
| Selected profile | Product app default |
| Why | App-like UI, API-backed screens, local browser state |
| Last reviewed | `YYYY-MM-DD` |

## Tooling

| Area | Choice | Notes |
| --- | --- | --- |
| Framework | Vite + React + TypeScript | Default product-app profile |
| Router | TanStack Router | File-based routes under `src/routes/` |
| Styling | Tailwind CSS | Utility-first; design tokens via config |
| Components | shadcn/ui | Generated into `src/components/ui/` |
| Package manager | `npm` | Use `pnpm` only when documented in stack decisions |
| Data access | REST via `fetch` + typed client | No GraphQL in v1 |
| CMS | None | Add Sanity only if non-developers need editing |

## App layout (agent navigation)

```text
src/
  main.tsx
  app/
    App.tsx
    router.tsx
  routes/
  components/ui/
  features/<feature-name>/
```

## Validation commands

Align script names with [testing_quality_practices.md](../testing_quality_practices.md) and `.docs/development_playbook.md`:

| Gate | Command |
| --- | --- |
| Lint | `npm run lint` |
| Typecheck | `npm run typecheck` |
| Unit/component tests | `npm test` |
| Build | `npm run build` |
| Smoke/e2e | `npm run test:e2e` |

Marketing/content profiles should add metadata/SEO smoke checks before production launch.

## Deviations from portfolio defaults

| Default | Deviation | Rationale |
| --- | --- | --- |
| None | — | — |

## Rejected alternatives (short)

| Alternative | Reason not chosen |
| --- | --- |
| Astro | App-like UI and client routing dominate; not a content-marketing site |
| Next.js | SSR not required for v1 |

## Agent constraints

- Do not add a second UI framework without updating this file and `.docs/stack_decisions.md`.
- Env var names only in docs; values live in `.env` / Cursor secrets.
