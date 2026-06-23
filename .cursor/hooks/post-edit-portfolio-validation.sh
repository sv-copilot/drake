#!/usr/bin/env bash
# Remind agents to run portfolio validation after relevant edits.
set -euo pipefail

input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name // empty')
path=$(echo "$input" | jq -r '.tool_input.path // .tool_input.file_path // empty')

if [[ "$tool_name" != "Write" && "$tool_name" != "StrReplace" ]]; then
  exit 0
fi

if [[ -z "$path" ]]; then
  exit 0
fi

norm="${path#./}"
norm="${norm#<workspace-root>/}"

context=""

case "$norm" in
  .docs/projects-registry.json|.docs/projects-registry.schema.json|.docs/bootstrap_spillover.json)
    context="Portfolio registry/schema changed. Before PR: python3 -m json.tool on touched JSON; run .github/workflows/ci.yml validation steps (registry schema + contract guards)."
    ;;
  .docs/*.json)
    context="Portfolio JSON under .docs/ changed. Run: python3 -m json.tool on the edited file."
    ;;
  *.md|.docs/*.md)
    context="Markdown changed. Run: git diff --check before commit."
    ;;
  drake.code-workspace)
    context="Workspace file changed. Run: python3 -c \"import json; json.load(open('drake.code-workspace'))\""
    ;;
esac

if [[ -n "$context" ]]; then
  jq -n --arg ctx "$context" '{additional_context: $ctx}'
fi

exit 0
