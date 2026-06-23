# AGENTS.md

Operating contract for AI agents working in a **Drake** governance repository.

Drake provides repository-native governance for AI-assisted development: slice
planning, dependency graphs, adapter contracts, and validation tooling.

## Branch policy

- `main` — stable integration branch for adopters.
- `ai-dev` — agent integration branch when using Drake automations.
- `agent/*` or `cursor/*` — feature branches for isolated slices.

## Validation before PR

From repo root:

```bash
bash scripts/ci_preflight.sh
```

## Scope

- Keep product runtime code in its own repositories.
- Use `.docs/examples/` for fictional registry and slice-tree samples.
- Do not commit secrets, live automation tokens, or operator registry data.

See `docs/getting-started.md` for a minimal adoption path.
