# Drake

[![CI](https://github.com/sv-copilot/drake/actions/workflows/ci.yml/badge.svg)](https://github.com/sv-copilot/drake/actions/workflows/ci.yml)

**Autonomous Development Governance** — repo-native governance for AI-assisted
software development. Coordinate agents, validate changes, and ship with
confidence.

> Agents generate code. Governance produces working software.

---

## What you can run in this repo today

Everything below is verified by CI on every push to `dev`, `rc`, and `main`.

| Command | What it does | Expected result |
| --- | --- | --- |
| `bash scripts/ci_preflight.sh` | The full gate: compiles and runs every validator, the Python test suites, the worker-runner build, and the hosted web tests + production build | ends with `ci preflight passed` |
| `bash scripts/dev-hosted.sh --check` | Verifies the hosted API + web shell scaffold | prints the local URLs |
| `bash scripts/dev-hosted.sh` | Starts the hosted read API and web shell locally | API on `http://127.0.0.1:8000`, web on `http://127.0.0.1:3000` |
| `python3 scripts/validate_slice_dependency_tree.py --tree .docs/examples/slice_dependency_tree.example.json` | Validates a slice dependency tree (cycles, missing deps, missing detail docs) | `dependency tree valid: …` |
| `python3 scripts/validate_drake_export.py --tree .` | Scans a tree for credential shapes and private control-plane markers | `drake export validation passed` |
| `npm --prefix apps/web test` | Hosted web shell unit tests (vitest) | all tests pass |
| `npm --prefix apps/web run test:e2e` | Playwright end-to-end smoke | passes with the dev server running |

Every check in `ci_preflight.sh` is **blocking**. There is deliberately no
"skip if it fails" path: a gate that hides a broken build is worse than no gate.

### Prerequisites

- Python **3.12+**
- Node **22+** and npm **10+**

`ci_preflight.sh` installs Python test dependencies into a repo-local `.venv`
(never into your system interpreter, which PEP 668 hosts refuse anyway).

### From scratch on a clean machine

Verified in a clean room: base OS utilities plus the toolchains installed below — no Node,
no Python toolchain, no npm cache, no site-packages. Every command here was run in that room,
in this order, on the release it ships with.

**Prerequisites — the whole list:** `git`, `curl`, `tar`, `xz`, **Python 3.12+** (with
`venv`), **Node 22+** and **npm 10+**. No C toolchain, no system Python packages: the gate
provisions a repo-local `.venv` for everything it needs.

Without root, both toolchains install from their own sources:

```bash
# Node, from the official tarball
curl -fsSL https://nodejs.org/dist/v22.20.0/node-v22.20.0-linux-x64.tar.xz | tar -xJ
export PATH="$PWD/node-v22.20.0-linux-x64/bin:$PATH"

# Python, from uv's standalone builds (no system packages, no root)
curl -fsSL https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz | tar -xz
./uv-x86_64-unknown-linux-gnu/uv python install 3.12
./uv-x86_64-unknown-linux-gnu/uv python find 3.12      # use this interpreter as python3
```

Then the documented path, which is what CI runs on every push:

```bash
# 1. get the framework
git clone --branch v0.2.6 --depth 1 https://github.com/sv-copilot/drake.git drake && cd drake

# 2. its own gate - compiles, validates, runs the suites, the smokes, the adoption chain,
#    the hosted API and the web build. Takes about a minute from an empty npm cache.
bash scripts/ci_preflight.sh                     # ends with: ci preflight passed

# 3. install the pipeline into your product repository
python3 scripts/sync_slice_pipeline_local.py --target ../my-product --mode install \
  --project-name "My Product" --project-id my-product --github-slug my-org/my-product \
  --validation-commands "bash scripts/ci_preflight.sh" --harnesses cline

# 4. start from the recommended configuration rather than a blank slate
cp -r examples/governed-workspace/.docs ../my-product/
python3 scripts/validate_slice_dependency_tree.py \
  --tree ../my-product/.docs/slice_dependency_tree.json     # dependency tree valid: …

# 5. build the runner
cd tools/slice-agent-runner && npm ci && npm run build && cd -

# 6. check the target: until your harness is installed this fails *by name*, which is the
#    point - a check that cannot run is a failure, not a skip
node tools/slice-agent-runner/dist/index.js check --repo ../my-product

# 7. prove the wiring with no model, no credentials, no cost
node tools/slice-agent-runner/dist/index.js run-next --repo ../my-product \
  --harness generic --harness-command "bash scripts/harness_stub.sh {prompt_file}"
python3 scripts/validate_run_artifacts.py --run "$(ls -dt ../my-product/.drake/runs/*/ | head -1)"

# 8. install your harness and run a slice
npm i -g cline && cline auth
node tools/slice-agent-runner/dist/index.js run-next --repo ../my-product
```

What you should see, from the clean-room run:

| Step | Result |
| --- | --- |
| 2 | `ci preflight passed` — 17 stages, harness matrix 14/14, adoption chain 27/27, ~55s |
| 3 | 27 files installed, including `.drake/slice-pipeline.config.json` and `AGENTS.md` |
| 4 | `dependency tree valid: …` |
| 6 | `[fail] harness binary not found on PATH: cline` — correct, and it names what is missing |
| 7 | run exits `0`; `evidence.json` validates and names the file the harness changed |
| 8 | a real slice, implemented by your harness, with evidence recorded under `.drake/runs/` |

Running a validator directly needs `jsonschema`; if your interpreter does not have it, use the
checkout's provisioned one (`./.venv/bin/python scripts/validate_run_artifacts.py …`) — the
validators say so rather than installing anything for you.

Reproduce it yourself — the scripts that built the room and walked this path are in the repo:

```bash
room=$(mktemp -d)
bash scripts/cleanroom-setup.sh "$room"          # base utilities + Node + Python, nothing else
bash scripts/cleanroom-run.sh "$room" v0.2.6     # the documented path, inside that room
```

**This section exists because a clean machine found two defects the host machine hid:** the gate
ran its validators with the system interpreter *before* provisioning `.venv`, and five
validators responded to a missing `jsonschema` by pip-installing it into whichever interpreter
was running them — refused on managed interpreters (PEP 668, uv, Homebrew) and wrong
everywhere else. Both are fixed; the clean-room run above is the regression test.

## What is Drake?

Drake is a governance framework that lives inside your repository. It coordinates
humans, AI coding agents, validation gates, and release promotion across one or
many software projects.

It is **not** an AI IDE, another coding agent, a CI/CD platform, a project
management tool, a GitHub replacement, or a fully autonomous engineering system.

Agents produce suggestions. Drake ensures those suggestions are scoped, validated,
reviewable, and merge-ready — with explicit human gates where they matter.

### What is in this repository, and what is not

This repo is the **adoptable framework**: contracts, schemas, templates,
validators, the slice-agent-runner CLI, and an optional hosted read-model API +
web shell.

The **reference worker runtime** — the orchestrator that schedules slices across
repositories, the dispatch queue, and the credentialed worker fleet — is operated
privately by the maintainer and is *not* part of this export. Adopters implement
or plug in their own worker against
[`adapters/CONTRACT.md`](adapters/CONTRACT.md); the contract and the evidence
schema are the stable interface.

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
    │                        Gate: No cycles. Every dependency declared and present.
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
                             Branches: slice/* → dev → rc → main
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

AI agents are implementers and suggesters — never deciders. Every decision that
affects product direction, architecture, or quality standards has a human gate.

### Automated Enforcement

These rules are enforced by tooling in **this** repository, not by convention:

| Rule | Enforcement | Artifact |
|------|-------------|----------|
| **TDD required** | The evidence gate requires test files in the diff and a recorded pre-implementation failure | `adapters/evidence-contract.schema.json` |
| **One slice, one PR** | One branch per slice; fan-out limited by the validated dependency tree | `adapters/task-packet.schema.json`, `tools/slice-agent-runner/` |
| **Branch policy** | Feature/slice branches → `dev` → `rc` → `main`; CI runs on every push to those three | `.github/workflows/ci.yml` |
| **Validation before merge** | `ci_preflight.sh` must pass, with every check blocking | `scripts/ci_preflight.sh` |
| **Dependency integrity** | Trees validated for cycles, dependencies missing from the tree, gate/state mismatches, and invalid states | `scripts/validate_slice_dependency_tree.py` |
| **No credential or private-data leak** | Public exports are scanned for credential shapes, home paths, and private control-plane markers | `scripts/validate_drake_export.py` |
| **Agent scope isolation** | Templated agent profiles scope which tools a worker may reach | `templates/slice-pipeline-local/.drake/`, `.docs/mcp_environment_profile.json` |

---

## Quick Start

```bash
git clone https://github.com/sv-copilot/drake.git
cd drake
bash scripts/ci_preflight.sh
```

That installs what it needs, validates the tree, runs every test suite, and
builds the hosted web shell. It ends with `ci preflight passed` or a failing exit
code — there is no partial pass.

Then:

1. [`docs/getting-started.md`](docs/getting-started.md) — the minimal adoption
   path: copy the example registry, install `slice-pipeline-local`, validate.
2. [`docs/cascade-walkthrough.md`](docs/cascade-walkthrough.md) — the whole
   methodology end to end, from strategy to production, on a worked example.
3. [`adapters/CONTRACT.md`](adapters/CONTRACT.md) — what a worker must implement
   to receive slices from Drake.

## Hosted local development

The hosted operations API and web shell are optional runtime surfaces. To verify
the local scaffold:

```bash
bash scripts/dev-hosted.sh --check
```

To start both services locally:

```bash
bash scripts/dev-hosted.sh
```

Defaults:

| Service | URL |
| --- | --- |
| API | `http://127.0.0.1:8000` |
| Web | `http://127.0.0.1:3000` |

`NEXT_PUBLIC_API_URL` points the web shell at the API. GitHub read sync may use
`GH_TOKEN` or `GITHUB_TOKEN` from the environment; committed docs and examples
must contain env var names only, never token values.

For a temporary no-DNS staging smoke on `http://<ip>:<port>` with a production
web build/start flow, see
[Temporary hosted IP staging](.docs/hosted-ip-staging.md):

```bash
STAGING_HOST=<server-ip> bash scripts/hosted-ip-staging.sh --check
```

## Repo Layout

| Directory | Purpose |
| --- | --- |
| `adapters/` | Worker adapter contract — task packet schema, evidence contract, reference adapter notes |
| `apps/web/` | Hosted operations web shell (Next.js) with its own unit and e2e tests |
| `services/api/` | Hosted read-model API (FastAPI) — read-only routes over the registry and trees |
| `docs/` | Getting started, cascade walkthrough, positioning, MCP hosting |
| `scripts/` | Validation, export, slice-lifecycle, and dev tooling |
| `templates/` | Reusable templates: ADR format, `slice-pipeline-local` install bundle |
| `tests/` | Validator and export-gate tests |
| `tools/` | CLI utilities (`slice-agent-runner`: selects the next slice, drives any coding harness, records evidence) |
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

## Status

Version **v0.1.0**. The governance contracts, schemas, validators, and the hosted
read-model shell in this repository are release-grade: every one of them is
exercised by the blocking gate above. The reference worker runtime (orchestrator,
dispatch, credentialed fleet) is operated privately and is intentionally not part
of this export.

Adoption is incremental: start with the evidence contract and the validators, add
the slice lifecycle when you have more than one agent working, and add the hosted
read-model when you want a view across repositories.

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
| **Full cascade walkthrough** | **[`docs/cascade-walkthrough.md`](docs/cascade-walkthrough.md)** — from strategy to production, using a worked example |
| Positioning next to coding agents | [`docs/comparison.md`](docs/comparison.md) |
| **Harnesses (Claude Code, Codex, Cursor, Cline, Aider, your own)** | [`docs/harnesses.md`](docs/harnesses.md) |
| **Example configuration to copy** | [`docs/example-configuration.md`](docs/example-configuration.md) + [`examples/governed-workspace/`](examples/governed-workspace/README.md) |
| Adapter contract (workers) | [`adapters/CONTRACT.md`](adapters/CONTRACT.md) |
| Task packet schema | [`adapters/task-packet.schema.json`](adapters/task-packet.schema.json) |
| Evidence contract | [`adapters/evidence-contract.schema.json`](adapters/evidence-contract.schema.json) |
| Agent operating contract | [`AGENTS.md`](AGENTS.md) |
| Project intake template | [`.docs/examples/project_intake.example.json`](.docs/examples/project_intake.example.json) |
| Slice dependency tree example | [`.docs/examples/slice_dependency_tree.example.json`](.docs/examples/slice_dependency_tree.example.json) |
| Stack decisions example | [`.docs/examples/stack_decisions.example.md`](.docs/examples/stack_decisions.example.md) |
| MCP hosting | [`docs/mcp_hosting.md`](docs/mcp_hosting.md) |
| Retest the adoption chain against a release | `scripts/adoption_chain_retest.sh` |
| Reproduce the from-scratch run | `scripts/cleanroom-setup.sh` + `scripts/cleanroom-run.sh` |
| Cut a verified release | `scripts/cut_release.sh <version>` (chain before the tag, cold-clone gate after it) |
