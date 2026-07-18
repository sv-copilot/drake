# Harness Interface Boundaries Design Document

| Field         | Value                                                                 |
|---------------|-----------------------------------------------------------------------|
| Slice #       | 94                                                                    |
| Group         | technical                                                             |
| Repo          | drake                                                                 |
| State         | shaped                                                                |
| Tier          | P1                                                                    |
| Effort        | small                                                                 |
| Risk          | low                                                                   |
| PR            | null                                                                  |

## Overview

This document defines the interface seams for the `drake` orchestrator so that its core loop can eventually be extracted into a pure harness library (`drake-core`). It identifies **trait boundaries** validated against three concrete adapter surfaces:

1. **Headless runner** (VPS cron, filesystem, GitHub API)
2. **Cockpit API** (Hetzner-hosted, Postgres, UI)
3. **Cockpit Chat** (read‑only console, interactive)

The goal is *not* to extract anything today — we lack the necessary second adapter surface. Instead, we define the seams, validate them, and plan a strangler‑fig migration that begins with small, safe extractions (guardrail chain, git_ops) and culminates in a full `drake-core` extraction only after **two or more real adapter surfaces** exist.

---

## Current State Analysis

### Module Map & Dependencies

drake/
├── orchestrator.py           # Main loop: fetch slice → run → commit/push
├── dispatch/                 # How slices are fetched/cancelled/queued
│   ├── webhook_dispatch.py   # Webhook receiver, GitHub event parsing
│   └── cron_dispatch.py      # Periodic polling via GitHub API
├── persistence/              # Session & evidence storage
│   └── sqlite_store.py       # SQLite (cockpit DB now, but mixed concerns)
├── approval/                 # Gate evaluation
│   └── gates/
│       └── operator_gates.py # Approval logic coupled to webhook payloads
├── llm/                      # LLM invocation
│   └── deepseek_provider.py  # Direct DeepSeek API calls
├── guardrails/               # Slice‑level guardrail chain
├── git_ops/                  # Git operations (clone, branch, commit, push)
└── cockpit/                  # Web dashboard & API (emerging)

### Core Logic vs Adapter Surface

| Module              | Classification   | Reason                                                  |
|---------------------|------------------|---------------------------------------------------------|
| `orchestrator.py`   | **Core**         | Loop logic; schedule/run/approve cycle, policy neutral |
| `dispatch/`         | **Adapter**      | Webhook, cron, future cockpit queue – all dispatch     |
| `persistence/`      | **Adapter**      | Storage backend (SQLite, Postgres, filesystem)         |
| `approval/`         | **Adapter**      | Decision source (operator gates, UI, chat)             |
| `llm/`              | **Adapter**      | Which LLM backend and how to call it                   |
| `guardrails/`       | **Core**         | Pure validation logic, reusable across adapters        |
| `git_ops/`          | **Core**         | Pure library for git automation, no adapter coupling   |
| `cockpit/`          | **Adapter**      | User interface, future dispatch & approval source      |

### Current Coupling Points

1. **`orchestrator.py` directly imports from `webhook_dispatch.py`** for fetching the next slice.
2. **Approval gates read webhook‑specific payload fields** (e.g., `event_type`, `action`).
3. **Persistence uses SQLite** with cockpit‑specific schema assumptions.
4. **The orchestrator writes artifacts directly to hard‑coded filesystem paths** expected by the webhook responder.

These couplings must be dissolved into trait‑based interfaces before extraction is possible.

---

## Proposed Trait Boundaries

Each trait defines a **Rust‑style interface** — a set of method signatures with explicit error semantics. All adapters implement the same traits. The orchestrator core depends *only* on these traits, not on concrete implementations.

### 1. `DispatchTrait`

// DispatchTrait — how the orchestrator obtains work
trait DispatchTrait {
    /// Return the next slice to run, or None if the queue is empty.
    fn select_next_slice(&self) -> Result<Option<Slice>, DispatchError>;

    /// Place a slice into the run queue.
    fn enqueue_run(&self, slice: Slice) -> Result<(), DispatchError>;

    /// Cancel a previously queued or in‑flight slice.
    fn cancel_run(&self, slice_id: SliceId) -> Result<(), DispatchError>;
}

**Error semantics:** `DispatchError` covers transport failures, queue corruption, and authentication issues. It is opaque to the core; only adapters interpret it.

**Adapter mapping:**

- **Headless runner**: Implemented by scanning a `slices/` directory (filesystem) and using GitHub Issues as a queue.
- **Cockpit API**: Backed by a database `dispatch_queue` table; enqueue via REST.
- **Cockpit Chat**: Does *not* implement this trait (read‑only adapter).

### 2. `PersistenceTrait`

trait PersistenceTrait {
    fn save_session(&self, session: &Session) -> Result<(), PersistenceError>;
    fn load_session(&self, session_id: &SessionId) -> Result<Session, PersistenceError>;
    fn save_evidence(&self, evidence: &Evidence) -> Result<(), PersistenceError>;
    fn load_evidence(&self, slice_id: &SliceId) -> Result<Vec<Evidence>, PersistenceError>;
}

**Error semantics:** `PersistenceError` signals storage failures (disk full, DB down). The core does not retry; it propagates the error.

**Adapter mapping:**

- **Headless runner**: Filesystem + SQLite in `/data/drake`.
- **Cockpit API**: Full Postgres database.
- **Cockpit Chat**: SQLite or in‑memory storage for interactive sessions.

### 3. `ApprovalTrait`

trait ApprovalTrait {
    /// Ask the operator whether to proceed. Returns a gate decision.
    fn request_approval(&self, context: &ApprovalContext) -> Result<Gate, ApprovalError>;

    /// Synchronous check of a pre‑defined policy (e.g. “no PR on weekends”).
    fn check_gate(&self, gate_name: &str) -> Result<bool, ApprovalError>;
}

**Error semantics:** `ApprovalError` includes timeout, manual denial, or configuration errors.

**Adapter mapping:**

- **Headless runner**: Gate configuration stored as YAML files; `request_approval` returns the default policy when no human is present (e.g., auto‑approve for low‑risk slices).
- **Cockpit API**: Pushes a notification to the cockpit UI; returns once the user clicks Approve/Deny.
- **Cockpit Chat**: Interactive prompt in the chat terminal; waits for operator input.

### 4. `LLMProviderTrait`

trait LLMProviderTrait {
    fn complete(&self, prompt: &str) -> Result<String, LlmError>;
    fn complete_streaming(&self, prompt: &str) -> Result<Box<dyn Stream<Item = String>>, LlmError>;
}

**Error semantics:** `LlmError` captures API rate limits, authentication failures, or model unavailability.

**Adapter mapping:**

- All three surfaces use the same core provider (Direct DeepSeek API), so this trait is already adapter‑ready.

---

## Adapter Surface Validation

The table below validates that each adapter surface can (or cannot) implement each trait. A check mark (✓) means the adapter can provide a real backing; a cross (✗) indicates the trait is inapplicable.

| Adapter Surface               | DispatchTrait         | PersistenceTrait       | ApprovalTrait          | LLMProviderTrait      |
|-------------------------------|-----------------------|------------------------|------------------------|-----------------------|
| Headless runner (VPS cron)    | ✓ Filesystem + GitHub | ✓ SQLite + /data/artifacts | ✓ Operator gates in tree | ✓ Direct DeepSeek API |
| Cockpit API (Hetzner)         | ✓ Cockpit DB + dispatch queue | ✓ Postgres | ✓ UI-based approval flow | ✓ Direct DeepSeek API |
| Cockpit Chat (#93)            | ✗ (read‑only)        | ✓ Session storage      | ✓ Interactive approval | ✓ Direct DeepSeek API |

**Key observation:** The **Headless runner** and **Cockpit API** both implement all four traits. The **Cockpit Chat** drops `DispatchTrait` because it cannot *create* new work; it only reads existing sessions. This is acceptable because the core loop for a read‑only client is a distinct instantiation that omits the dispatch step.

---

## Strangler-Fig Migration Plan

A strangler‑fig approach gradually replaces tightly‑coupled code with trait‑based components while the system continues to run.

### Phase 1 – Extract guardrail chain (#135)
- **Goal:** Prove the extraction pattern on a core module that already has minimal adapter coupling.
- Extract `guardrails/` into a standalone Python package with its own tests.
- The orchestrator imports this package as a library (no trait required, just a clean dependency).
- **Status:** Slice #135 is ready for implementation.

### Phase 2 – Extract git_ops (#141)
- **Goal:** Extract the pure git automation logic into a reusable library.
- `git_ops` has no adapter dependencies; it can exist as a standalone module.
- **Status:** Slice #141 is defined.

### Phase 3 – Stabilize second adapter surface
- Wait until **two adapter surfaces** are production‑ready:
  - **Cockpit API** (slices #53, #65) – provides dispatch, persistence, and approval over REST.
  - **Cockpit Chat** (#93) – provides interactive approval and read‑only session inspection.
- Once both are stable, begin defining concrete adapter implementations that conform to the traits described above.

### Phase 4 – Run old and new in parallel
- Create a feature flag (`DRAKE_CORE_ENABLED`) that switches the orchestrator between the current monolithic implementation and the refactored version that uses trait objects.
- Deploy the refactored version to a staging environment alongside the production orchestration.
- Validate parity: identical slices, identical outputs, identical side‑effects.
- Once parity is proven, **cut over** by flipping the flag in production.

### Phase 5 – Extract `drake-core` library
- Move the pure orchestrator loop and the trait definitions into a standalone crate/library.
- All remaining adapter modules become optional dependencies behind the trait boundaries.
- The monorepo continues to provide concrete adapters, but external teams can now build their own.

---

## Anti-Patterns to Avoid

1. **Extraction before 2+ adapter surfaces exist.** A trait shaped by a single concrete implementation often reflects the quirks of that implementation rather than a genuine abstraction. Wait until we have a headless runner and the cockpit API running in production before finalizing traits.

2. **Traits designed for a single adapter.** If only the webhook dispatch exists, the `DispatchTrait` would inadvertently carry webhook‑specific concepts. Counteract this by keeping traits minimal and designing them against the planned headless and cockpit surfaces from the start.

3. **Mixing orchestration policy with adapter code.** The core must never know about GitHub webhooks, cron schedules, or cockpit REST endpoints. Policy decisions (e.g., retry logic, timeouts) belong in adapter implementations, not in the trait signatures.

4. **Avoiding the strangler‑fig by attempting a big‑bang rewrite.** The migration plan above is deliberately incremental. Even the trait definitions in this document are considered provisional until Phase 4 proves them correct in practice.

5. **Ignoring error semantics.** A common mistake is to make trait errors too generic (e.g., `Box<dyn Error>`). Define explicit error enums so that adapters can differentiate between transient and permanent failures without leaking adapter‑specific details.

6. **Premature extraction of the orchestrator loop as a library.** The current loop is small and still evolving. Extracting it before the adapter surfaces are stable would result in frequent breaking changes to the `drake-core` interface, defeating its purpose.

---

*This document is a living blueprint. It will be updated as adapter surfaces mature and extraction slices progress.*