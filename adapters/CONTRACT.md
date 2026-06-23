# Worker Adapter Contract

This document defines the interface contract between an **Orchestrator** and a
**Worker Adapter** in the Autonomous Development Governance system. The
contract is tool-agnostic: any orchestration framework, CI pipeline, or AI agent
that respects these schemas can participate in the slice pipeline.

---

## 1. Purpose

The adapter contract standardizes how work units (slices) are dispatched and how
results are reported back. This enables:

- **Interchangeable workers** — Cursor, Cline, OpenHands, or custom agents all
  speak the same wire format.
- **Auditability** — every task produces a structured evidence record that can
  be replayed, verified, or archived.
- **Orchestrator portability** — the orchestrator does not need to know which
  tool runs a task; it only needs to produce a valid Task Packet and consume a
  valid Evidence Contract.

---

## 2. Architecture Overview

```
+----------------+       Task Packet        +----------------+
|                |  ---------------------->  |                |
| Orchestrator   |                          | Worker Adapter |
|                |  <---------------------- |                |
+----------------+       Evidence Contract  +----------------+

        ^                                        ^
        |                                        |
   (human or CI)                          (Cursor, Cline, etc.)
```

The Orchestrator:
1. Selects a slice from the backlog/dependency tree.
2. Builds a Task Packet describing what to do.
3. Dispatches it to the appropriate Worker Adapter (based on `adapter_type`).
4. Receives back an Evidence Contract with results.
5. Feeds evidence into PR babysitting, auditing, or archival.

The Worker Adapter:
1. Receives a Task Packet.
2. Validates its schema and determines if it can handle the task.
3. Executes the work (implement slice, review PR, babysit, audit, etc.).
4. Produces an Evidence Contract with results, validation outcomes, and PR info.
5. Returns the evidence to the orchestrator.

---

## 3. Task Packet (Orchestrator -> Worker)

**Schema file:** `task-packet.schema.json`

The Task Packet is a JSON object with the following structure:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | yes | Globally unique task identifier. |
| `task_type` | enum | yes | Kind of work: `implement_slice`, `review_pr`, `babysit_pr`, `audit_repo`, `course_correct`, `bootstrap_project`, `dry_run`, `custom`. |
| `slice_ref` | object | yes | Reference to the backlog slice this task implements. |
| `orchestrator_ref` | object | yes | Identifies the orchestrator run that dispatched this task. |
| `adapter_type` | string | yes | Target adapter routing hint (e.g. `cursor`, `cline`, `openhands`). |
| `payload` | object | yes | The actual task content. At minimum contains `instructions`. |
| `context` | object | no | Non-secret runtime context, credential references, repo URL, environment hints. |
| `created_at` | string (date-time) | yes | ISO 8601 timestamp. |
| `ttl_seconds` | integer | no | Optional expiry. Default 3600. |
| `priority` | integer | no | 0-10 priority scale. Lower = higher. Default 5. |

### Required fields per role

| Role | Minimum required fields |
| --- | --- |
| **Dispatcher** (orchestrator) | Must set `id`, `task_type`, `slice_ref`, `orchestrator_ref`, `adapter_type`, `payload.instructions`, `created_at`. |
| **Consumer** (worker) | Must validate `id`, `task_type`, `payload.instructions` before processing. |
| **Router** (intermediate) | Must read `adapter_type` for routing; may inspect `task_type` for queue assignment. May ignore `payload`. |

### Example

```json
{
  "id": "run-20260617-abc123/1-a4f8",
  "task_type": "implement_slice",
  "slice_ref": {
    "slice_id": "ADAPTER-SPEC-1",
    "slice_number": 1,
    "slice_title": "Worker adapter specification"
  },
  "orchestrator_ref": {
    "run_id": "hourly-20260617-abc123",
    "orchestrator_type": "hourly",
    "dispatched_at": "2026-06-17T14:30:00Z"
  },
  "adapter_type": "cursor",
  "payload": {
    "instructions": "Implement the adapter specification...",
    "working_directory": "<workspace-root>",
    "branch_prefix": "agent/",
    "target_branch": "ai-dev"
  },
  "context": {
    "credential_refs": ["GH_TOKEN"],
    "github_slug": "sv-copilot/drake",
    "integration_branch": "ai-dev",
    "environment": "local"
  },
  "created_at": "2026-06-17T14:30:00Z",
  "ttl_seconds": 3600,
  "priority": 1
}
```

### Validation rules

1. `id` must be globally unique across all runs (use orchestrator_run_id + slice_number + short UUID).
2. `task_type` must be one of the defined enum values.
3. `payload.instructions` must be present and non-empty.
4. `created_at` must be a valid ISO 8601 date-time string.
5. `ttl_seconds`, if present, must be >= 60.
6. `payload.branch_prefix`, when present, should use `agent/` for new work. Legacy
   `cursor/` prefixes remain valid during migration (see `.docs/branch_conventions.md`
   in repos that install the slice-pipeline-local bundle).

---

## 4. Evidence Contract (Worker -> Orchestrator)

**Schema file:** `evidence-contract.schema.json`

The Evidence Contract is a JSON object with the following structure:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `task_id` | string | yes | Must match the original Task Packet `id`. |
| `status` | enum | yes | Outcome: `success`, `failure`, `partial`, `blocked`, `skipped`, `cancelled`. |
| `summary` | string | yes | Human-readable summary of results. |
| `evidence_items` | array | yes | List of file changes or artifacts produced. |
| `validation_results` | object | no | Validation outcomes. Schema: `adapters/validation-results.schema.json`. |
| `adapter_info` | object | yes | Adapter metadata (type, version, runtime). |
| `pr_info` | object | no | PR details if one was opened. |
| `logs` | array | no | Captured log entries. |
| `timestamps` | object | no | `started_at`, `completed_at`, `duration_ms`. `completed_at` is required. |

### Status semantics

| Status | Meaning |
| --- | --- |
| `success` | All work completed as instructed. |
| `failure` | Work attempted but could not complete; evidence may contain partial results. |
| `partial` | Some work done; the slice is too large or hit a resource limit. Sub-slicing may be needed. |
| `blocked` | Could not start or make progress due to an external blocker (missing credential, dependency not met, policy violation). |
| `skipped` | Task was valid but intentionally not executed (e.g. duplicate, out of scope). |
| `cancelled` | Task was aborted before completion. |

### Example

```json
{
  "task_id": "run-20260617-abc123/1-a4f8",
  "status": "success",
  "summary": "Created adapter specification: task-packet.schema.json, evidence-contract.schema.json, CONTRACT.md",
  "evidence_items": [
    {
      "path": "adapters/task-packet.schema.json",
      "change_type": "added",
      "description": "JSON Schema for the orchestrator-to-worker task packet."
    },
    {
      "path": "adapters/evidence-contract.schema.json",
      "change_type": "added",
      "description": "JSON Schema for the worker-to-orchestrator evidence contract."
    },
    {
      "path": "adapters/CONTRACT.md",
      "change_type": "added",
      "description": "Human-readable adapter interface specification."
    }
  ],
  "validation_results": {
    "overall": "passed",
    "checks": [
      {
        "check_name": "JSON syntax (task-packet)",
        "status": "passed",
        "command": "python3 -m json.tool adapters/task-packet.schema.json",
        "exit_code": 0
      },
      {
        "check_name": "JSON syntax (evidence-contract)",
        "status": "passed",
        "command": "python3 -m json.tool adapters/evidence-contract.schema.json",
        "exit_code": 0
      }
    ]
  },
  "adapter_info": {
    "adapter_type": "cursor",
    "adapter_version": "1.0.0",
    "runtime": "local"
  },
  "pr_info": {
    "pr_url": "https://github.com/sv-copilot/drake/pull/42",
    "pr_number": 42,
    "branch": "cursor/adapter-spec-1",
    "base_branch": "ai-dev",
    "state": "open"
  },
  "logs": [
    {
      "timestamp": "2026-06-17T14:30:05Z",
      "level": "info",
      "message": "Started implementation of ADAPTER-SPEC-1"
    }
  ],
  "timestamps": {
    "started_at": "2026-06-17T14:30:05Z",
    "completed_at": "2026-06-17T14:35:42Z",
    "duration_ms": 337000
  }
}
```

### Validation rules

1. `task_id` must exactly match the `id` from a dispatched Task Packet.
2. `status` must be one of the defined enum values.
3. At least one `evidence_items` entry is expected when `status` is `success` or `partial`.
4. `adapter_info.adapter_type` should match the `adapter_type` from the Task Packet.
5. If `pr_info` is present, `pr_url` must be a valid URL.

---

## 5. Delivery Protocol

The contract does not mandate a specific transport. Supported delivery methods:

| Method | When to use |
| --- | --- |
| **Inline return** | Worker runs in the same process as the orchestrator (local CLI, hook script). |
| **File output** | Evidence is written to a well-known path (e.g. `.evidence/<task_id>.json`). |
| **Webhook callback** | Orchestrator provides a callback URL in `context`, and the worker POSTs the evidence. |
| **Shared store** | Both parties read/write from a shared filesystem, S3 bucket, or database. |

For the Cursor adapter, the preferred delivery is **inline return** via
`orchestrator_ref.run_id` matching — the orchestrator and worker share a session.

---

## 6. Versioning and Evolution

| Component | Version source |
| --- | --- |
| Task Packet schema | `$id` field in `task-packet.schema.json` — change the version segment on breaking changes. |
| Evidence Contract schema | `$id` field in `evidence-contract.schema.json` — change the version segment on breaking changes. |
| Adapter implementations | `adapter_info.adapter_version` in evidence — the worker self-declares its version. |

### Schema evolution rules

1. **Adding fields** is always backward-compatible (non-breaking). Old workers
   ignore unknown fields; old orchestrators fill defaults.
2. **Removing or renaming fields** is a major version bump. Update the `$id`
   version segment and update all adapters that produce or consume the field.
3. **Enum additions** to existing fields (e.g. new `task_type` values) are
   backward-compatible. Consumers must tolerate unknown enum values — treat
   them as `custom`.
4. **Marking optional fields as required** is a breaking change. Prefer adding
   new optional fields over making existing optional fields required.

---

## 7. Error Handling

| Scenario | Worker behavior |
| --- | --- |
| Invalid Task Packet | Reject with evidence: `status: "failure"`, `summary` describing the schema violation. |
| Unknown `adapter_type` | Reject with evidence: `status: "skipped"`, log `warn` level. |
| Execution timeout | Abort, return evidence: `status: "partial"`, include whatever was completed. |
| Credential missing | Return evidence: `status: "blocked"`, describe which credential is missing. |
| Unexpected exception | Return evidence: `status: "failure"`, include exception info in `logs`. |

---

## 8. Security Considerations

1. **No secrets in Task Packets.** Credential names may appear in
   `context.credential_refs`, but actual tokens, keys, and passwords must never
   be embedded in the packet. The worker adapter resolves credentials from its
   own secure store (env vars, secret manager, MCP server).
2. **Evidence validation.** Orchestrators should validate the Evidence
   Contract against its schema before trusting any field. Signed evidence
   (using adapter-specific signing keys) is a future enhancement.
3. **Task ID uniqueness.** Task IDs must be globally unique to prevent replay
   attacks and evidence confusion. Use a combination of run ID, slice number,
   and a UUID.
4. **Transport security.** When using webhook callbacks, require HTTPS and
   optionally validate a webhook signature.

---

## 9. References

- `adapters/task-packet.schema.json` — Task Packet JSON Schema
- `adapters/evidence-contract.schema.json` — Evidence Contract JSON Schema
- `adapters/validation-results.schema.json` — Validation Results JSON Schema
- `.docs/validation_results_parity.md` — Cross-runtime validation result contract
- `.docs/slice_backlog.md` — Human-readable slice backlog
- `.docs/slice_dependency_tree.json` — Machine-readable dependency graph
- `AGENTS.md` — Portfolio operating contract
