# Drake

**Autonomous Development Governance** — Repo-native governance for AI-assisted
software development. Coordinate agents, validate changes, and ship with
confidence.

> Agents generate code. Governance produces working software.

## What is Drake?

Drake is a governance framework that lives inside your repository. It coordinates
humans, AI coding agents, validation gates, and release promotion across one or
many software projects.

It is **not** an AI IDE, another coding agent, a CI/CD platform, a project
management tool, a GitHub replacement, or a fully autonomous engineering system.

Agents produce suggestions. Drake ensures those suggestions are scoped, validated,
reviewable, and merge-ready — with explicit human gates where they matter.

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
| **Worker Runtime** | Adapter layer | Interchangeable agents (Cursor, Cline, OpenCode, Aider, OpenHands) that receive task packets and produce PR evidence |
| **MCP / Tooling** | Environment profiles | Tool servers scoped to dev, staging, or production; agents move between environments but credentials do not |

## Quick Start

```bash
git clone https://github.com/sv-copilot/drake.git
cd drake
bash scripts/ci_preflight.sh
```

Then read [`docs/getting-started.md`](docs/getting-started.md) for the minimal
adoption path: clone, copy example registry, install slice-pipeline-local,
validate.

## Repo Layout

| Directory | Purpose |
| --- | --- |
| `adapters/` | Worker adapter contract — task packet schema, evidence contract, and reference adapter implementations |
| `docs/` | Getting started and documentation index |
| `scripts/` | Validation, export, and slice management tooling |
| `templates/` | Reusable templates (slice-pipeline-local install bundle) |
| `tests/` | Test fixtures and export validation tests |
| `tools/` | CLI utilities (slice-agent-runner for local/cloud execution) |
| `.docs/examples/` | Fictional registry and slice-tree samples for adopters |
| `.cursor/` | Agent operating contracts for IDE-native workflows |

## Who is Drake For?

- **Solo technical founders** managing multiple repos with limited time
- **AI-native indie hackers** shipping many small products in parallel
- **Small agencies** running consistent delivery doctrine across client repos
- **Small engineering teams** experimenting with AI agents who need governance
  before trusting automation

If you're asking "what should I work on next?", "did that change actually pass
validation?", or "how do I make my agent workflows portable?" — Drake is for
you.

For the full strategy and user personas, see the [product strategy
overview](https://github.com/sv-copilot/drake).

## License and Community

Drake is open source under the [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)
license (see `LICENSE`).

- [**CONTRIBUTING.md**](CONTRIBUTING.md) — how to contribute, DCO, and PR conventions
- [**GOVERNANCE.md**](GOVERNANCE.md) — project governance model _(coming soon)_
- [**CODE_OF_CONDUCT.md**](CODE_OF_CONDUCT.md) — community standards

## Links

- [Getting Started](docs/getting-started.md) — minimal adoption walkthrough
- [Adapter Contract](adapters/CONTRACT.md) — how workers are wired in
- [Task Packet Schema](adapters/task-packet.schema.json) — what a worker receives
- [Evidence Contract](adapters/evidence-contract.schema.json) — what a worker produces
- [Agent Operating Contract](AGENTS.md) — rules for AI agents in Drake-governed repos
- [Product Strategy](https://github.com/sv-copilot/drake) — vision, positioning, architecture direction

### Project Bootstrap

Drake's opinionated project-start template lives in
[project-bootstrap](https://github.com/sv-copilot/project-bootstrap).
Use it to create new repos with Drake governance pre-configured.

## Status

Drake is a working internal reference architecture managing multiple product
repositories. It is evolving from operator-private tooling into a public
open-source framework. Current focus: documentation, adapter contracts, and
public launch readiness.
