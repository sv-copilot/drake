# Drake: Repository-Native Governance for AI-Assisted Software Development

**Whitepaper · October 2026 · v3**

Drake is an open-source, repository-native governance layer for AI-assisted software development.
It is Apache-2.0 licensed, currently released as **v0.2.8**, and lives at
[github.com/sv-copilot/drake](https://github.com/sv-copilot/drake).

This paper describes what the system is, how it is put together, and — where it matters — what
has been verified and how. It is written from the system's current state rather than from its
intentions, so every claim below is backed by a test, by a run you can repeat, or is explicitly
labelled as unverified.

---

## How to read the claims in this paper

Documentation that asserts behaviour the code does not have is the recurring defect in this
domain, and this project has produced its share. Three examples from earlier revisions are worth
naming, because they show what the current revision is checked against:

- An earlier version described a `max_files_per_slice` field. **No such field exists**; work-size
  limits are the dependency tree's `default_fanout_limit` plus the selector's `--max`.
- An earlier version implied slices were executed in priority order. `priority` was declared in
  the tree schema and **ignored by the selector**. It now orders execution.
- An earlier version claimed the validator rejects dependency cycles. It did not, until the check
  was written and a test pinned it.

Where this paper states a number, it is the output of a command in this repository; where it
states a verification method, that method can be re-run. Anything unverified says so.

---

## 1. Generation is not the bottleneck

Modern AI coding agents — Claude Code, Codex, Cursor, Cline, Aider, OpenHands — produce code at
scale. Teams adopting them meet a consistent set of problems that have nothing to do with code
quality:

| Failure mode | Consequence |
|---|---|
| **Context loss** — each session starts fresh, with no memory of repository state or prior decisions | repeated work, inconsistent decisions |
| **Vague task prompts** | large, risky changes touching dozens of files |
| **Weak planning** — no explicit dependency graph | wrong execution order, merge conflicts |
| **Hidden assumptions** — the agent makes product and architecture decisions | design drift without human approval |
| **Incomplete validation** — work merges without proof it functions | defects found in production |
| **Environment drift** — local and remote agents see different filesystems and credentials | "worked on my machine" |
| **Tool lock-in** — governance encoded in one vendor's configuration | switching agents costs you your governance |
| **Green ≠ working** — a pipeline reports success while what it wraps is broken | false confidence, at the worst moment |

> *Agents generate code. Governance produces working software.*

Drake is that governance layer. It lives in the repository, treats Git as the canonical source of
truth, and works with whichever agent you already use.

---

## 2. Architecture

```
┌────────────────────────────────────────────────────────────┐
│  HUMANS — direction, gates, review, promotion approval     │
├────────────────────────────────────────────────────────────┤
│  OPTIONAL CONTROL PLANE — cross-repo scheduling, history   │
│  (not required; the framework runs without it)             │
├────────────────────────────────────────────────────────────┤
│  DRAKE (public, Apache-2.0)                                │
│  contracts · installer · selector · validators · runner    │
│  harness catalogue · gate · release + rehearsal scripts    │
├────────────────────────────────────────────────────────────┤
│  HARNESS RUNTIME — your CLI, and your credential           │
│  Claude Code · Codex · Cursor · Cline · Aider · your own    │
├────────────────────────────────────────────────────────────┤
│  VALIDATION — lint · typecheck · test · build · schemas    │
├────────────────────────────────────────────────────────────┤
│  REPOSITORY — registry · dependency tree · slice docs ·    │
│  canonical assets (.drake/), generated views, evidence      │
└────────────────────────────────────────────────────────────┘
```

The invariant: **the repository is the source of truth.** Any hosted or scheduled layer projects
state *from* Git and can disappear without stopping governance.

| Layer | Role | Must not |
|---|---|---|
| **Humans** | direction, priority, review gates, promotion approval | delegate accountability |
| **Control plane** | registry, dependency trees, scheduling, fan-out, run history | become the canonical store of slice state |
| **Drake** | contracts, selection, installation, validation, executing one slice, release and rehearsal | hold a model credential, embed a vendor SDK, or require a control plane to run |
| **Harness** | implement one slice from a task packet; produce evidence | choose its own slice, bypass validation, touch more than one repository |
| **Validation** | prove the change | be skipped when it cannot run — a check that cannot run is a failure |
| **Repository** | registry, tree, slice docs, canonical assets, evidence records | — |

---

## 3. The slice: the unit of work

A slice is a bounded, dependency-aware task with explicit state, gates, and validation
requirements. In the committed tree its fields are: `slice_id`, `slice_number`, `group`, `title`,
`state`, `status`, `dependencies`, `blocks`, `operator_gates`, `checkpoint`,
`automation_eligible`, `priority`, `last_known_pr`, `risk`, `effort`, `tier`.

Rules that hold in code, not only in prose:

- **One slice, one branch, one pull request, one evidence narrative.**
- **`priority` orders execution** — sorted ascending, then by `slice_number`, with a row's own
  number as the fallback.
- **Fan-out is capped at the tree** by `default_fanout_limit`, with `--max` as a further cap.
- **A managed asset is not an editable one.** Files Drake *executes* (selector, lifecycle
  helpers, hook scripts) are refreshed on install; your files (AGENTS.md, prompts, conventions)
  are never overwritten without an explicit flag, and `check` blocks on a stale managed file.
- **A slice with unresolved `operator_gates` is not automation-eligible**, and the selector skips
  it. Your decisions stay yours.

---

## 4. Lifecycle

```
proposed → shaped → ready → gated → running → review → validated → promoted → released
                ↓                ↓         ↓         ↓          ↓
            archived         running   blocked   running   archived
```

| State | Meaning | Who acts |
|---|---|---|
| **proposed** | captured, not yet refined | you |
| **shaped** | scoped: dependencies, gates, detail doc | you |
| **ready** | dependencies satisfied, eligible for dispatch | selector |
| **gated** | an operator gate is present and unresolved | you |
| **running** | dispatched to a harness | harness |
| **blocked** | an external blocker exists | you |
| **review** | pull request open, awaiting human review | reviewer |
| **validated** | merged, validation passed, tree synced | you |
| **promoted** | promoted along `dev → rc → main` | you |
| **released** | tagged and verified | you |
| **archived** | cancelled, superseded, or no longer relevant | — |

Humans hold four suspension points — **shaped**, **gated**, **review**, **promoted**. Automation
fills the gaps between them.

---

## 5. Harness-agnostic execution

Drake does not prescribe an agent and does not embed one. **A harness is a child process.** Drake
writes a prompt file and a task packet, spawns the configured command, and reads what the harness
left behind.

| Harness | Invocation | Prompt | Entry points it reads | How the invocation was verified |
|---|---|---|---|---|
| **Claude Code** | `claude -p <prompt> --output-format json --permission-mode acceptEdits [--model <m>]` | argv | `AGENTS.md`, `CLAUDE.md`, `.claude/agents/` | vendor docs |
| **Codex** | `codex exec --sandbox workspace-write [--model <m>] <prompt>` | argv | `AGENTS.md` | vendor docs |
| **Cursor** | `cursor-agent -p --force [--model <m>] <prompt>` | argv | `AGENTS.md`, `.cursor/agents/`, `.cursor/hooks/` | vendor docs |
| **Cline** | `cline --auto-approve true <prompt>` | argv | `AGENTS.md`, `.clinerules` | **`cline 3.0.68 --help`** |
| **Aider** | `aider --message-file <prompt-file> --yes-always --no-auto-commits [--model <m>]` | file | `AGENTS.md` | **`aider 0.86.2 --help`** |
| **Generic** | your command, with `{prompt_file}`, `{prompt}` or `{model}` | file | `AGENTS.md` | n/a — yours |

The catalogue is machine-readable (`adapters/harnesses.json`) and each entry records *how* it was
verified — by running the CLI, by reading vendor documentation, or as your own command. A test
asserts the runner and the catalogue agree, so "verified" can never quietly mean "someone read a
blog post".

Install lines pin versions deliberately: an unpinned global install is a supply-chain gamble, and
upstream has flagged old releases of at least one of these CLIs as malicious.

### Why a child process rather than an SDK

- **The credential stays yours.** Drake never holds a model key, so upgrading the framework cannot
  leak one and a cloned repository cannot spend on one.
- **The invocation is inspectable.** `run-next --dry-run` renders the exact command, so there is no
  hidden prompt assembly inside vendor code.
- **The whole path is testable without a model.** A stub harness that records what it received
  makes Drake's side of the contract executable in CI — no network, no credential, no cost. That
  is how the task packet and the evidence writer are kept honest (§7).
- **Swapping agents is a configuration change**, not a migration.

### What a harness must not do

Decide portfolio priority; bypass validation; touch more than one repository; mutate production
state; choose its own slice. The harness executes a bounded packet. Something else decides what
runs, and in what order.

---

## 6. The adoption path, and what it proves

**Prerequisites:** `git`, `curl`, `tar`, `xz`, Python 3.12+ (with `venv`), Node 22+ / npm 10+.
No C toolchain, no system Python packages, no root.

**The path:** clone → run the gate → install into your product repository → validate the
dependency tree → build the runner → run one slice (`--dry-run` first) → inspect the evidence →
schedule it.

**The gate** (`scripts/ci_preflight.sh`) runs **17 stages**, all blocking. There is no partial
pass: a check that cannot run is a failure, not a skip. An earlier version of this gate printed
`ci preflight passed` while the web build was broken — the precise failure mode this project
exists to prevent, and one of the reasons every check is now blocking.

**Scheduling is yours.** `scripts/slice-cron.sh` runs one slice per tick with a single-flight lock
(atomic `mkdir`, so it needs no `flock`), writes one log per run, and propagates the runner's exit
code unchanged. Those exit codes are the contract with your cron or systemd timer:

| Code | Meaning | Monitoring |
|---|---|---|
| `0` | a slice ran | nothing |
| `1` | configuration, harness or selector error — the run never started | **alert** |
| `2` | the harness ran and failed | **alert** |
| `3` | nothing runnable | nothing — this is a normal state |

A scheduler that cannot tell "no work" from "broken" gets muted within a week, so exit `3` exists,
and the systemd recipe in `docs/scheduling.md` carries `SuccessExitStatus=0 3`.

### What is verified, and how

- **From a machine with nothing installed** — base OS utilities plus Node and Python built from
  their own sources: the gate passes in about a minute, 17 stages, harness matrix **18/18**,
  adoption chain **27/27**. The scripts that build that room ship with the repository
  (`scripts/cleanroom-setup.sh`, `scripts/cleanroom-run.sh`), so the claim is reproducible rather
  than narrated.
- **Against the published release, from a cold clone**: **35 of 35 assertions** covering the gate,
  the install flow, one install per harness, the run chain (`0`/`2`/`3`), the upgrade path, and a
  pre-0.2 configuration still loading.
- **On every release**: the adoption chain runs in the gate, again before the tag, and once more
  after it — and a test asserts those three properties exist, because losing that discipline would
  otherwise be silent.

### What is not verified

No live vendor model call is executed anywhere in the test path. It requires a credential, and no
credential is installed in the verification environment. Everything up to the model call is
exercised; the invocation itself rests on the verification column in §5. If you want the last
mile, `run-next` against a configured CLI is a single command — but this paper will not claim it
has been run when it has not.

---

## 7. Evidence, and tests as an enforced property

Implementation work is expected to follow RED → GREEN → REFACTOR → PROVE, and the proof is a
machine-readable artifact rather than a paragraph. Every run writes a task packet, a prompt, the
harness's output, an evidence record, and the list of files that changed.

The evidence record is validated against a **published schema** in CI. That validation exists
because the record was once found to fail its own schema — a required field was missing and a field
typed as an object was emitted as an array — since nothing had ever applied the schema to the
output. Two rules generalise:

- **A contract nothing validates is decoration.** Publish the schema *and* the validator, run it
  in CI, and keep a captured real run checked in as a fixture.
- **"No files changed" and "the working tree could not be read" are different claims.** An empty
  list needs its reason attached, or the reader cannot tell them apart.

---

## 8. The repo-native principle

| Aspect | Repo-native implementation |
|---|---|
| **Dependency trees** | committed JSON under `.docs/` |
| **Slice definitions** | committed markdown, one file per slice |
| **Validation commands** | committed: `validationCommands` in `.drake/slice-pipeline.config.json`, plus CI workflow YAML |
| **Harness configuration** | committed catalogue plus the per-repository choice in the config |
| **Canonical assets** | committed under `.drake/`, with each harness's entry points generated from them |
| **State transitions** | git commits: tree-sync after merge, promotion pull requests |
| **Evidence** | run records under `.drake/runs/`, gitignored by default and retained when you want them |

Why it matters: no lock-in (your governance data is in your history), portability (clone the repo
and you have the whole state), auditability (every transition is a commit with an author and a
diff), branchability (experiment with governance on a branch), and an open core that is viable
*because* it is only files in a repository.

---

## 9. What is provided, and what is not

**Provided (Apache-2.0):** the slice specification and tree schema; the task packet, evidence and
validation-results contracts; the harness catalogue and the canonical asset set with its generated
views; the installer and validators; the slice selector and lifecycle helpers; the reference
runner; the gate, the adoption smoke, the harness matrix, the adoption-chain rehearsal and the
release scripts; the scheduler entry point; the example governed workspace; and the configuration
recommendations themselves (`docs/example-configuration.md`, `examples/governed-workspace/`).

**Not provided:** a cross-repository scheduler or dashboard. Drake executes one slice well and
leaves the portfolio-level loop to you — a shell script, a CI job, or a control plane you write.
Anything that speaks the schemas in `adapters/` can drive the same machinery. A hosted layer with
dashboards, run history and multi-repository views is an optional, non-required convenience, and
nothing in this paper depends on it existing.

---

## 10. Who this is for

- **Solo technical founders and single-operator product teams** — several repositories, limited
  time, AI leverage without losing control.
- **AI-native indie hackers** — many small products in parallel, wanting repeatable setup that
  enforces good defaults.
- **Small agencies** — client repositories delivered with consistent doctrine, without bespoke
  automation per client.
- **Small engineering teams** — experimenting with agents, wanting governance before trusting
  unattended execution, and a self-hostable path that does not depend on one vendor.

---

## 11. Current state

| Component | Status |
|---|---|
| Release | **v0.2.8**, Apache-2.0 |
| Gate | **17 stages, all blocking**; green from a from-scratch room and on every release |
| Harness catalogue | **6 presets**; two verified by running the CLI, three by vendor docs, one bring-your-own-command |
| Runner | Spawns a child process; holds no model credential |
| Selector and tree validator | Priority-aware ordering; cycle detection |
| Contracts | Task packet and evidence validated against published schemas in CI |
| Adoption rehearsal | **35/35** against the published release from a cold clone |
| Harness matrix | **18/18**, including four scheduling scenarios |
| Release management | The adoption chain runs in the gate, before the tag, and after it — asserted by a test |
| Unattended scheduling | `scripts/slice-cron.sh` with cron and systemd recipes |
| Clean room | `scripts/cleanroom-setup.sh` / `cleanroom-run.sh` |
| Unit tests | 84 |

**Reproduce the central claim:**

```bash
room=$(mktemp -d)
bash scripts/cleanroom-setup.sh "$room"
bash scripts/cleanroom-run.sh "$room" v0.2.8
```

---

## 12. Why this is different

Most tooling optimises for code generation — the part of the problem that is commoditising. Drake
optimises for what remains hard: coordination across repositories, trust in unattended execution,
validation that produces evidence rather than hope, and governance that survives a change of
tools.

Two choices define it. **Repo-native**: by anchoring governance in Git — the one tool every
developer already trusts — Drake avoids the adoption friction of a proprietary platform while
providing what such platforms cannot: portability, auditability, and no lock-in. **Harness-agnostic**:
a harness is a child process, so governance does not depend on the agent any more than on the
vendor, and swapping agents is configuration rather than migration.

As agents improve, the bottleneck moves further from generation and closer to governance — and to
a quieter problem worth naming: knowing whether the machinery you trust is actually working.
