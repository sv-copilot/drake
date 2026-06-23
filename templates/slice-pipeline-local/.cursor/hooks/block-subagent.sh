#!/usr/bin/env bash
# Blocks subagentStart for automation cost/scope policy, except approved
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

printf '%s\n' '{"permission":"deny","user_message":"Subagents are blocked by repo policy except for the approved slice-pipeline subagents: slice-preflight, slice-implementer, and pr-babysitter.","agent_message":"Do not spawn subagents unless the task is one of the approved slice-pipeline subagents."}'
exit 2
