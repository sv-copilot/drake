# CLAUDE.md

This repository runs the Drake slice pipeline. `{{PROJECT_NAME}}` uses the
`{{HARNESS_ID}}` harness.

Claude Code reads this file automatically. Two things to know:

- **AGENTS.md is the contract.** Read it before any git operation. It is the same
  file every other harness reads, so the rules do not fork per tool.
- **Canonical agent prompts live in `.drake/agents/`.** `slice-preflight`,
  `slice-implementer` and `pr-babysitter` are installed as Claude Code subagents
  under `.claude/agents/`, and the same prompts are used by the other harnesses.
  If you edit one, edit the copy under `.drake/agents/` first: that is the source
  the installer refreshes everywhere else from.

Slice workflow: pick the next ready slice with
`python3 scripts/select_next_automation_slice.py --tree .docs/slice_dependency_tree.json`,
implement exactly that one slice, keep one slice to one PR, and never fan out.

Runtime handoff files belong under `.drake/runs/` and are never committed.
