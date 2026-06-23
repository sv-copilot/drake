# Cursor Adapter Reference Implementation

This document describes the **Cursor adapter** — a reference implementation of
the [Worker Adapter Contract](../CONTRACT.md) that bridges the existing Cursor
Cloud-based automation pipeline with the generic Task Packet and Evidence
Contract schemas.

Existing Cursor automations (slice-pipeline, hourly-improvement, babysit, etc.)
continue to work unchanged. The adapter layer is additive: it documents how the
existing Cursor workflow maps onto the generic contract without requiring any
automation prompt changes.

---

## 1. How the Cursor Adapter Fits In

```
+------------------+     Task Packet      +------------------+
|                  |  ------------------> |                  |
|  Orchestrator    |                      |  Cursor Adapter  |
|  (human, hook,   |  <------------------ |  (Cursor Cloud   |
|   CI, or SDK)    |    Evidence Contract |   Agent, CLI)    |
+------------------+                      +------------------+
```

The Cursor adapter is the **first concrete adapter** implementing the generic
contract. It translates between:

- **Task Packets** (defined in `adapters/task-packet.schema.json`) and the
  Cursor Agent's native prompt/context format.
- **Evidence Contracts** (defined in `adapters/evidence-contract.schema.json`)
  and the Cursor Agent's natural output (file changes, logs, PR links).

### Adapter vs. Automation

| Concept | Cursor Automation | Adapter |
| --- | --- | --- |
| What it is | A saved Cursor Cloud Agent configuration with prompt, model, trigger | A **mapping layer** that documents how automation inputs/outputs correspond to the generic contract |
| Example | `slice-pipeline` automation in `drake` | `adapters/cursor/CURSOR-ADAPTER.md` + example schemas |
| Change needed | None — existing automations keep their prompts | Additive — new docs and examples sit alongside existing config |

The adapter is not a new runtime. It is a **documented convention** so that
non-Cursor tools (orchestrators, CI pipelines, other adapters) can understand
what a Cursor Cloud Agent run produces and expects.

---

## 2. Dispatching Work Through the Cursor Adapter

### 2.1 From an Orchestrator (human or automated)

A human or CI orchestrator builds a Task Packet and hands it to the Cursor
adapter. The adapter runs it as a Cursor Agent session:

1. **Build a Task Packet** — valid against `adapters/task-packet.schema.json`,
   with `adapter_type: "cursor"`.
2. **Choose a runner** — see [section 6](#6-integration-with-the-slice-agent-runner).
3. **Execute** — the runner translates the Task Packet into a Cursor Agent
   prompt and context.
4. **Collect evidence** — the runner reads the agent's output and produces an
   Evidence Contract.

### 2.2 Inside a Cursor Cloud Automation

Existing Cursor Cloud automations (slice-pipeline, hourly-improvement, babysit)
do **not** change their prompts. The adapter layer documents the correspondence:

1. The automation's prompt receives instructions (equivalent to the Task
   Packet's `payload.instructions`).
2. The Cursor Agent executes the work (implement slice, review PR, etc.).
3. The agent opens a PR and/or produces output files.
4. A validation script or hook reads the results and can produce an Evidence
   Contract (for auditability or cross-adapter consumption).

---

## 3. Task Type Mapping

The Cursor adapter supports all `task_type` values from the Task Packet schema.
The table below shows how each type maps to the existing Cursor workflow.

| `task_type` | Cursor Automation Equiv. | How the adapter handles it |
| --- | --- | --- |
| `implement_slice` | slice-pipeline | Runs the slice prompt from `.docs/slices/` against the repo. Opens a PR. Collects evidence from git diff and validation output. |
| `review_pr` | PR review (manual or automated) | Checks out the PR branch, analyses changes, runs relevant validation, and provides structured review comments. |
| `babysit_pr` | pr-babysitter automation | Watches an open PR for new comments, resolves merge conflicts, re-runs CI checks, and pushes fixup commits. Loops until merge or timeout. |
| `audit_repo` | portfolio-audit skill | Scans repo policy docs, automation config, and validation output. Produces a structured audit report as Evidence Contract. |
| `course_correct` | course-correct-project skill | Applies bootstrap standards to a sibling repo. Reports divergence and fix results. |
| `bootstrap_project` | kickoff-project skill | Creates a new repo from project-bootstrap template, initializes git, and runs intake setup. |
| `dry_run` | CI preflight / smoke test | Runs validation commands against the repo without making changes. Produces an Evidence Contract with `status: "success"` or `status: "failure"`. |
| `custom` | User-defined automation | The `payload.instructions` field is treated as the full agent prompt. The adapter executes it as-is. |

### Task-type-specific payload fields

Beyond the required `payload.instructions`, the Cursor adapter recognizes:

| Field | Applies to | Description |
| --- | --- | --- |
| `working_directory` | All | Override the default repo root. Default `.`. |
| `branch_prefix` | `implement_slice`, `review_pr` | Branch prefix for new work. Default `agent/`. Legacy `cursor/` accepted. |
| `target_branch` | `implement_slice` | Base branch for PR. Default `ai-dev`. |

---

## 4. Evidence Contract Production

After executing a task, the Cursor adapter produces an Evidence Contract valid
against `adapters/evidence-contract.schema.json`.

### Automated field mapping

| Evidence Contract Field | Source in Cursor workflow |
| --- | --- |
| `task_id` | Copied from the Task Packet `id`. |
| `status` | Derived from exit code and validation outcomes. |
| `summary` | Last-line summary from the agent or manual inspection of changes. |
| `evidence_items` | File changes detected by `git diff --name-status` against the base branch. |
| `validation_results` | Output of validation commands run after the agent finishes. Conforms to `adapters/validation-results.schema.json`. |
| `adapter_info.adapter_type` | Always `"cursor"`. |
| `adapter_info.adapter_version` | Git hash of the `adapters/cursor/` directory or a semver tag. |
| `adapter_info.runtime` | `"cursor-cloud"` for Cursor Cloud Agents, `"local-cli"` for local IDE sessions, `"slice-agent-runner"` when using the SDK runner. |
| `pr_info` | Populated when a PR was opened: URL, number, branch name, state. |
| `logs` | Captured from stdout/stderr during execution. |
| `timestamps` | Tracked by the runner or automation framework. |

### Backward-compatible output

Existing Cursor automations that do **not** produce an Evidence Contract
continue to work. The Evidence Contract is a **progressive enhancement**:

- Automations that produce it enable cross-adapter auditability and
  orchestrator handoff.
- Automations that skip it continue to rely on their current output
  (PR comment, git push, console log).

---

## 5. Backward Compatibility

The Cursor adapter is designed to be **fully backward compatible** with
existing Cursor Cloud automations and local workflows.

### What does NOT change

- Existing automation prompts (slice-pipeline, hourly-improvement, babysit, etc.)
- Existing branch naming conventions (`cursor/*` still accepted; `agent/*` preferred)
- Existing validation and CI scripts
- Existing PR workflow (opening, reviewing, merging)
- Existing credential and secret handling
- Existing Cursor Cloud Agent model settings (`composer-2.5`)

### What IS new (additive)

- `adapters/cursor/CURSOR-ADAPTER.md` — this document
- `adapters/cursor/task-packet-example.json` — example Task Packet
- `adapters/cursor/evidence-contract-example.json` — example Evidence Contract
- Adapter conformance validation scripts (see [section 7](#7-validation))

### Migration path for existing automations

Existing automations can adopt the adapter contract incrementally:

1. **Phase 0** (current) — No change. Automations use native Cursor prompts.
2. **Phase 1** — Automation produces an Evidence Contract file alongside the PR.
   No prompt change needed; a post-run hook writes the evidence.
3. **Phase 2** — Automation receives a Task Packet as input. The existing
   prompt wraps around the packet's `payload.instructions`.
4. **Phase 3** — Full adapter conformance: Task Packet in, Evidence Contract
   out, validated against schemas.

Each phase is optional. An automation can stay at any phase indefinitely.

---

## 6. Integration with the Slice-Agent-Runner

The [Cursor SDK](https://github.com/sv-copilot/cursor-sdk) provides a
`slice-agent-runner` that automates the Task-Packet-to-agent-execution-to-Evidence-Contract
pipeline. The Cursor adapter works with this runner in two modes:

### Mode 1: Runner dispatches automatically

The `slice-agent-runner` accepts a Task Packet file and:
1. Validates it against the Task Packet schema.
2. Routes to the Cursor adapter when `adapter_type: "cursor"`.
3. Creates a Cursor Agent session with instructions from the packet.
4. Collects output and produces an Evidence Contract.
5. Writes the evidence to a well-known path or returns it inline.

### Mode 2: Manual handoff

A human operator reads the Task Packet, runs the Cursor agent manually in the
IDE or Cloud Agent, and writes an Evidence Contract to document the outcome.
This is the default for local development and ad-hoc tasks.

### Prerequisites for SDK runner

- Python 3.10+ or Node.js 18+
- `cursor-sdk` package installed (`pip install cursor-sdk` or `npm install @cursor/sdk`)
- `GH_TOKEN` or equivalent credential for repository access
- A Task Packet file (JSON) to execute

---

## 7. Validation

Adapter conformance can be verified locally with:

```bash
# 1. JSON syntax
python3 -m json.tool adapters/cursor/task-packet-example.json
python3 -m json.tool adapters/cursor/evidence-contract-example.json

# 2. Schema validation (requires jsonschema)
python3 -c "
import json, jsonschema
s = json.load(open('adapters/task-packet.schema.json'))
d = json.load(open('adapters/cursor/task-packet-example.json'))
jsonschema.validate(d, s)
print('task-packet-example.json: valid')
"
python3 -c "
import json, jsonschema
s = json.load(open('adapters/evidence-contract.schema.json'))
d = json.load(open('adapters/cursor/evidence-contract-example.json'))
jsonschema.validate(d, s)
print('evidence-contract-example.json: valid')
"

# 3. Markdown lint (optional)
# npm install -g markdownlint-cli && markdownlint adapters/cursor/CURSOR-ADAPTER.md
```

---

## 8. Configuration

### Environment variables

| Variable | Required | Description |
| --- | --- | --- |
| `GH_TOKEN` | Yes | GitHub token with repo scope for PR operations and cloning. |
| `CURSOR_ADAPTER_VERSION` | No | Override adapter version in Evidence Contract. Default: inspect git hash of `adapters/cursor/`. |
| `CURSOR_ADAPTER_RUNTIME` | No | Override runtime label. Default: auto-detected (`cursor-cloud`, `local-cli`, or `slice-agent-runner`). |

### Scripts

| Script | Purpose |
| --- | --- |
| `adapters/cursor/task-packet-example.json` | Reference Task Packet for conformance testing |
| `adapters/cursor/evidence-contract-example.json` | Reference Evidence Contract for conformance testing |
| Portfolio validation commands (see section 7) | Adapter conformance checks |

No new scripts or binaries are required. Validation uses standard Python tools
available in any Cursor Cloud Agent or CI environment.

---

## 9. References

- `adapters/CONTRACT.md` — Worker Adapter Contract (specification)
- `adapters/task-packet.schema.json` — Task Packet JSON Schema
- `adapters/evidence-contract.schema.json` — Evidence Contract JSON Schema
- `adapters/validation-results.schema.json` — Validation Results JSON Schema
- `.docs/slice_backlog.md` — Human-readable slice backlog
- `.docs/slice_dependency_tree.json` — Machine-readable dependency graph
- `.docs/slices/ADAPTER-CURSOR-1.md` — This slice's detail document
- [Cursor SDK](https://github.com/sv-copilot/cursor-sdk) — SDK for
  programmatic agent execution
- `AGENTS.md` — Portfolio operating contract
