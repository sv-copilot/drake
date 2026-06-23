#!/usr/bin/env bash
# Blocks Task tool usage for automation cost/scope policy, except approved
# slice-pipeline subagents.
# See .docs/agent_automation_execution_policy.md
set -euo pipefail

input=$(cat)

case "$input" in
  *slice-preflight*|*slice-implementer*|*pr-babysitter*)
    printf '%s\n' '{"permission":"allow"}'
    exit 0
    ;;
esac

printf '%s\n' '{"permission":"deny","user_message":"Task/explore agents are blocked by repo policy except for the approved slice-pipeline subagents: slice-preflight, slice-implementer, and pr-babysitter.","agent_message":"Do not use the Task tool unless invoking an approved slice-pipeline subagent."}'
exit 2
