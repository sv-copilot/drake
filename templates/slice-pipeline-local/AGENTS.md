# {{PROJECT_NAME}} — agent operating contract

This repository runs the slice pipeline. Agents implement one slice at a time and
report evidence. They never decide what to build.

## Rules

- Work only on the slice you were given. `{{DEPENDENCY_TREE_PATH}}` is the source of truth
  for what is ready, blocked, and gated.
- One slice, one branch (`{{FEATURE_BRANCH_PREFIX}}<slice-id>`), one pull request. Direct pushes
  to `{{INTEGRATION_BRANCH}}` are not allowed.
- Tests first. A slice is not done until its acceptance checks have run and passed.
- Report the outcome as an evidence record. Do not edit files that belong to another slice.
- No secrets in commits, prompts, or evidence. Credentials are referenced by name only.
- Runtime handoff artifacts belong under `.drake/runs/` and are never committed.
- This repository's slice pipeline is harness agnostic: `docs/harnesses.md`.

## Validation

`{{VALIDATION_COMMANDS}}` must pass before a pull request is opened.
