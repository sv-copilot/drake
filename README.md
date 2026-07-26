# Drake

**Autonomous Development Governance** — Repo-native governance for AI-assisted
software development. Coordinate agents, validate changes, and ship with
confidence.

> Agents generate code. Governance produces working software.

---

## Product Development Philosophy

Drake codifies a complete product development methodology — from top-level
product vision down to individual test-driven slices. Each layer has explicit
ownership, gates, and automation. Nothing ships without evidence.

### The Full Cascade

```
PRODUCT STRATEGY        →  What are we building and why?
    │                        Owner: Product Owner. Artifact: product_strategy.md
    │                        Gate: Strategy review. No automation.
    ▼
PROJECT INTAKE          →  How do we scope this product?
    │                        Owner: Product Owner. Artifact: project_intake.json
    │                        Gate: Success criteria defined. UX directive set.
    ▼
ARCHITECTURE DECISIONS  →  Why did we choose this approach?
    │                        Owner: Architect. Artifact: .docs/adr/*.md
    │                        Gate: Alternatives considered. Consequences documented.
    ▼
SLICE BACKLOG           →  What do we build and in what order?
    │                        Owner: Product Owner + Engineering Lead.
    │                        Artifact: .docs/slice_backlog.md
    │                        Gate: Ranked by value/risk/dependency.
    ▼
DEPENDENCY TREE         →  What blocks what?
    │                        Owner: Engineering Lead.
    │                        Artifact: slice_dependency_tree.json
    │                        Gate: No cycles. All deps declared. Detail docs present.
    ▼
TDD SLICES              →  RED → GREEN → REFACTOR → PROVE
    │                        Owner: AI Agent (dispatched) or Human Engineer.
    │                        Artifact: PR with test files, implementation, evidence
    │                        Gate: Tests fail before implementation. Tests pass after.
    ▼
EVIDENCE CONTRACT       →  Prove the work was done correctly.
    │                        Owner: Pipeline (automated verification).
    │                        Artifact: pipelineRunEvidence JSON
    │                        Gate: Test files in diff. Validation commands passed.
    ▼
PROMOTION PIPELINE      →  Ship with confidence.
                             Owner: Release Manager.
                             Branches: slice/* → ai-dev → dev → main
                             Gates: Local validation → CI → Staging deploy → CI → Production
```

### Who Decides What

Drake draws a clear line between human judgment and AI execution:

| Decision | Human | AI Agent |
|----------|-------|----------|
| Product vision and strategy | ✅ Decides | ❌ |
| What to build next (prioritization) | ✅ Decides | Suggests |
| Architecture and technology choices | ✅ Decides | Researches, proposes |
| Scoping a slice (acceptance criteria) | ✅ Approves | Drafts |
| Implementing a slice | ✅ Reviews PR | ✅ Implements |
| Writing tests | ✅ Reviews | ✅ Writes (TDD enforced) |
| Validation and CI | ✅ Defines commands | ✅ Runs, reports |
| Merging and promotion | ✅ Approves PR | ✅ Creates PR, syncs tree |

AI agents are implementers and suggester — never deciders. Every decision that
affects product direction, architecture, or quality standards has a human gate.

### Automated Enforcement

These rules are enforced by tooling, not convention:

| Rule | Enforcement | Where |
|------|-------------|-------|
| **TDD required** | Guardrail rejects output with zero test files. Verification gate checks test diff. | `guardrail.py`, `orchestrator.py` |
| **One slice, one PR** | Runner creates one branch per slice. Fan-out controlled by dependency tree. | `cockpit-runner-cron` |
| **Branch policy** | `slice/*` → `ai-dev` (local validation) → `dev` (CI) → `main` (CI). No direct pushes to dev/main. | Branch protection + AGENTS.md contract |
| **Validation before merge** | `ci_preflight.sh` must pass. Exact commands documented in PR body. | Pre-commit hooks + CI |
| **Evidence required** | Every completed slice produces `pipelineRunEvidence` JSON: test files changed, test results, validation output. | `evidence-contract.schema.json` |
| **Dependency integrity** | Tree validated for cycles, missing deps, missing detail docs. Invalid trees block fan-out. | `validate_slice_dependency_tree.py` |
| **Agent scope isolation** | BUILD agents get cockpit tools only. USE agents get platform tools only. Never both. | MCP access control + agent instructions |

---

## What is Drake?

Drake is a governance framework that lives inside your repository. It coordinates
humans, AI coding agents, validation gates, and release promotion across one or
many software projects.

It is **not** an AI IDE, another coding agent, a CI/CD platform, a project
management tool, a GitHub replacement, or a fully autonomous engineering system.

Agents produce suggestions. Drake ensures those suggestions are scoped, validated,
reviewable, and merge-ready — with explicit human gates where they matter.

### The Problem Drake Solves

AI coding has moved beyond autocomplete. Today's agents can read repos, edit
files, run commands, and open pull requests. The bottleneck is no longer code
generation — it is governance: knowing what to work on next, keeping changes
small and reviewable, proving they work before merging, and maintaining
portability across tools and environments.

Drake addresses the failure modes that frustrate AI-assisted development:

- **Context loss** — agents start fresh each time with no memory of repo state
- **Vague tasks** — poorly scoped instructions produce large, risky changes
- **Weak planning** — no dependency graph, no decomposition into reviewable units
- **Incomplete validation** — PRs merge without proof the change works
- **Broken environment parity** — local and headless agents see different
  filesystems and credentials
- **Tool lock-in** — deep coupling to one IDE or agent framework
- **Lack of trust** — no confidence that unattended execution produces safe,
  mergeable work

## Architecture at a Glance

Drake is organized into five layers. You adopt the layers you need.

| Layer | Where it Lives | What it Does |
| --- | --- | --- |
| **Repo-Native Contract** | Your product repo (`.docs/`) | Roadmap, slice backlog, dependency tree, validation commands, branch policy, MCP profiles |
| **Portfolio Governance** | Your control-plane repo | Project registry, cross-repo scheduling, dependency resolution, reusable templates |
| **State Engine** | Schema conventions (JSON) | Slice lifecycle tracking: proposed → shaped → ready → running → review → validated → promoted |
| **Worker Runtime** | Adapter layer | Interchangeable agents that receive task packets and produce PR evidence |
| **MCP / Tooling** | Environment profiles | Tool servers scoped to dev, staging, or production; agents move between environments but credentials do not |

## Quick Start

```bash
git clone https://github.com/sv-copilot/drake.git
cd drake
bash scripts/ci_preflight.sh
```

Then read [`docs/getting-started.md`](docs/getting-started.md) for the minimal
adoption path: clone, copy example registry, install slice-pipeline-local,
validate. For MCP hosting guidance, see [`docs/mcp_hosting.md`](docs/mcp_hosting.md).

## Repo Layout

| Directory | Purpose |
| --- | --- |
| `adapters/` | Worker adapter contract — task packet schema, evidence contract, and reference adapter implementations |
| `docs/` | Getting started, decision documentation (ADRs), MCP hosting |
| `scripts/` | Validation, export, and slice management tooling |
| `templates/` | Reusable templates: ADR format, slice-pipeline-local install bundle |
| `tests/` | Test fixtures and export validation tests |
| `tools/` | CLI utilities (slice-agent-runner for local/cloud execution) |
| `.docs/examples/` | Fictional registry and slice-tree samples for adopters |

## Who is Drake For?

- **Solo technical founders** managing multiple repos with limited time
- **AI-native teams** who want governance before trusting automation at scale
- **Small agencies** running consistent delivery doctrine across client repos
- **Engineers who want to show employers** a complete product development
  methodology — from strategy through TDD to production

If you're asking "what should I work on next?", "did that change actually pass
validation?", or "how do I make my agent workflows portable?" — Drake is for
you.

## License and Community

Drake is open source under the [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)
license (see `LICENSE`).

- [**CONTRIBUTING.md**](CONTRIBUTING.md) — how to contribute, DCO, and PR conventions
- [**CODE_OF_CONDUCT.md**](CODE_OF_CONDUCT.md) — community standards

## Links

| Topic | Document |
|-------|----------|
| Getting started | [`docs/getting-started.md`](docs/getting-started.md) |
| Decision documentation (ADRs) | [`templates/adr.md`](templates/adr.md) |
| Adapter contract (workers) | [`adapters/CONTRACT.md`](adapters/CONTRACT.md) |
| Task packet schema | [`adapters/task-packet.schema.json`](adapters/task-packet.schema.json) |
| Evidence contract | [`adapters/evidence-contract.schema.json`](adapters/evidence-contract.schema.json) |
| Agent operating contract | [`AGENTS.md`](AGENTS.md) |
| Project intake template | [`.docs/examples/project_intake.example.json`](.docs/examples/project_intake.example.json) |
| Slice dependency tree example | [`.docs/examples/slice_dependency_tree.example.json`](.docs/examples/slice_dependency_tree.example.json) |
| Stack decisions example | [`.docs/examples/stack_decisions.example.md`](.docs/examples/stack_decisions.example.md) |
| MCP hosting | [`docs/mcp_hosting.md`](docs/mcp_hosting.md) |

### Project Bootstrap

Drake's opinionated project-start template lives in
[project-bootstrap](https://github.com/sv-copilot/project-bootstrap).
Use it to create new repos with Drake governance pre-configured.

## Status

Drake is a working internal reference architecture managing multiple product
repositories. It is evolving from operator-private tooling into a public
open-source framework. Current focus: documentation, adapter contracts, and
public launch readiness.
