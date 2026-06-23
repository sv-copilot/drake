# Branch Conventions

This document describes the branch model for agent-driven slice work in
`{{PROJECT_NAME}}`.

## Integration branches

| Branch | Role |
| --- | --- |
| `main` | Production-grade branch. |
| `dev` | Staging-grade branch. |
| `{{INTEGRATION_BRANCH}}` | Agent integration branch and default PR target. |

## Feature branch prefixes

| Prefix | Status |
| --- | --- |
| `{{FEATURE_BRANCH_PREFIX}}*` | Preferred prefix for new agent implementation branches. |
| {{LEGACY_FEATURE_BRANCH_PREFIXES}} | Legacy prefixes accepted during migration. |

Configure the preferred prefix in `.cursor/slice-pipeline-local.config.json`
using `featureBranchPrefix`. List accepted legacy prefixes under
`legacyFeatureBranchPrefixes`.

## Default workflow

1. Start from `{{INTEGRATION_BRANCH}}`.
2. Create a `{{FEATURE_BRANCH_PREFIX}}<slug>` branch for one scoped slice or
   change set.
3. Run validation, then open a PR targeting `{{INTEGRATION_BRANCH}}`.
4. After merge, sync back to the integration branch before starting the next
   slice.

## Backward compatibility

Existing open PRs and in-flight branches that use legacy prefixes remain valid
until a repo completes BRANCH-MIGRATE-2 rollout. New automation runs should
prefer `{{FEATURE_BRANCH_PREFIX}}*` unless an operator explicitly requests a
legacy prefix for compatibility testing.
