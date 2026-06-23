# Agent Automation Execution Policy

Canonical cost and scope guardrails for automated slice runs in `{{PROJECT_NAME}}`.
Operator in-thread overrides win for that run only.

## Rules

1. **Model:** Use the repo-approved automation model. If this repo has no
   stricter documented choice, use the portfolio default model for automated
   slice workers and do not escalate without explicit operator instruction.
2. **Subagents:** Do not launch subagents, Task tool runs, or explore agents
   unless the operator explicitly asks in the current thread or the run is using
   the approved slice-pipeline exception below.
3. **Scope:** One slice, one PR, no fan-out.
   - Run the configured selector:
     `{{SLICE_SELECTOR_COMMAND}}`
   - Implement only the first `selected[]` row.
   - Do not open a second implementation PR for another rank in the same run.

## Enforcement Layers

| Layer | Location |
| --- | --- |
| Prompts | `.docs/agent_prompts/slice-pipeline-automation.md` and repo-local TDD prompts |
| Hooks | `.cursor/hooks.json` plus `.cursor/hooks/block-task-tool.sh` and `.cursor/hooks/block-subagent.sh` |
| Selection | `{{SLICE_SELECTOR_COMMAND}}` |
| Workflow | `AGENTS.md`, `.docs/git_workflow.md`, `.docs/agent_automations.md` |

## When To Stop Instead Of Escalating

- The target slice is not ready, is not automation eligible, has incomplete
  dependencies, or has an unresolved operator gate.
- The selector exits non-zero or returns no selected rows.
- The target slice already has an open PR that should be babysat instead of
  opening a second implementation PR.
- The requested action conflicts with repo-local privacy, truthfulness, data, or
  branch policy.

## Approved Slice-Pipeline Exception

The `slice-pipeline` automation prompt is an operator-approved subagent
orchestration path. It may invoke only:

- `/slice-preflight`
- `/slice-implementer`
- `/pr-babysitter`

This exception does not permit general explore, shell, browser, or unrelated
Task agents, and it does not relax the one-slice/one-PR rule.
