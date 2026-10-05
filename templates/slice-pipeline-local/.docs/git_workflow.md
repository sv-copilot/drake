# Git workflow

- Branch: `{{FEATURE_BRANCH_PREFIX}}<slice-id>` (legacy prefixes still accepted: {{LEGACY_FEATURE_BRANCH_PREFIXES}})
- Integration branch: `{{INTEGRATION_BRANCH}}`
- One slice, one branch, one pull request. Direct pushes to `{{INTEGRATION_BRANCH}}` are not allowed.
- Slice selection: `{{SLICE_SELECTOR_COMMAND}}`
- Validation before merge: `{{VALIDATION_COMMANDS}}`
