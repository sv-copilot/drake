# AGENTS.md

Operating contract for AI agents working in a **Drake** governance repository.

Drake provides repository-native governance for AI-assisted development: slice
planning, dependency graphs, adapter contracts, and validation tooling.

## Branch policy

- `main` — stable integration branch for adopters.
- `ai-dev` — agent integration branch when using Drake automations.
- `agent/*` or `slice/*` — feature branches for isolated slices.

## Slice Lifecycle

All slice planning and state tracking lives in the **canonical planning tree**
at `simon-projects/.docs/planning/projects/drake/slice_dependency_tree.json`.
This file is the single source of truth. Do not maintain a duplicate slice
inventory in this file.

Before implementing any new feature, ensure a slice entry and detail doc exist
in the planning tree. After merging a PR, update the planning tree with
`state`, `last_known_pr`, and `branch_posture` (see `tree-sync-after-merge`
skill in simon-projects).

The canonical local dev loop: PLAN (simon-projects) → IMPLEMENT (this repo) → SYNC (simon-projects).

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
