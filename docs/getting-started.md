# Getting started

Adopt Drake in about 30 minutes: verify this repo, then wire the slice pipeline
into a product repository of your own.

## Prerequisites

- Python **3.12+**
- Node **22+**, npm **10+**
- `git`

## Step 1 — Verify this repository

```bash
git clone https://github.com/sv-copilot/drake.git
cd drake
bash scripts/ci_preflight.sh
```

Expected: the script prints each check and ends with `ci preflight passed`. Every
check is blocking — if it can't run, the gate fails rather than skipping. The
first run creates a repo-local `.venv` for Python test dependencies; it never
touches your system interpreter.

## Step 2 — Install the slice pipeline into your product repo

`sync_slice_pipeline_local.py` installs the reusable capability (agent
definitions, hooks, prompts, branch conventions, and the runner config) into a
target repository. It is conservative by design: `check` writes nothing.

```bash
# Report what is missing or stale in your repo.
# check compares the target against the flags you pass, so give it the same ones
# you installed with.
python3 scripts/sync_slice_pipeline_local.py --target /path/to/your-repo --mode check \
  --project-name "Your Product" --project-id your-product \
  --github-slug OWNER/REPO --validation-commands "bash scripts/ci_preflight.sh"

# Install (existing non-empty files are left alone unless you pass --overwrite-existing)
python3 scripts/sync_slice_pipeline_local.py \
  --target /path/to/your-repo \
  --mode install \
  --project-name "Your Product" \
  --project-id your-product \
  --github-slug OWNER/REPO \
  --integration-branch dev \
  --validation-commands "bash scripts/ci_preflight.sh"
```

Then copy the registry example to a real registry in your control-plane location
(one entry per repository):

```bash
cp .docs/examples/projects-registry.example.json /path/to/your-registry/projects-registry.json
```

## Step 3 — Describe your work as slices

Three artifacts per project, all in your repository:

| Artifact | Path | Purpose |
| --- | --- | --- |
| Slice backlog | `.docs/slice_backlog.md` | Ranked list of what to build |
| Dependency tree | `.docs/slice_dependency_tree.json` | What blocks what; machine-validated |
| Slice detail docs | `.docs/slices/<SLICE-ID>.md` | Acceptance criteria and validation commands |

Validate the tree before you rely on it — this is the same validator CI runs:

```bash
python3 scripts/validate_slice_dependency_tree.py --tree /path/to/your-repo/.docs/slice_dependency_tree.json
```

It fails on dependency cycles, dependencies missing from the tree, gate/state
mismatches, and invalid states. Acceptance criteria should be **runnable**: each
one names the command that proves it.

## Step 4 — Point a worker at the slices

Workers implement one slice at a time and return evidence. The contract is
[`adapters/CONTRACT.md`](../adapters/CONTRACT.md); the reference CLI is
`tools/slice-agent-runner`:

```bash
npm --prefix tools/slice-agent-runner ci
npm --prefix tools/slice-agent-runner run build

node tools/slice-agent-runner/dist/index.js check --repo /path/to/your-repo
node tools/slice-agent-runner/dist/index.js run-next --repo /path/to/your-repo --local --dry-run
```

`--dry-run` renders the task packet and prompt without calling a model — use it
to see exactly what a worker would be told. Drop `--dry-run` (and add `--cloud
--auto-pr` to run against the configured GitHub repo and open the pull request)
once the packet looks right.

## Step 5 — Evidence and promotion

- Every slice produces evidence JSON matching
  [`adapters/evidence-contract.schema.json`](../adapters/evidence-contract.schema.json):
  which test files changed, what the tests did before and after, and the
  validation output.
- Branches: feature/slice branches → `dev` → `rc` → `main`. CI runs on all three;
  nothing is promoted without a green run.
- `bash scripts/ci_preflight.sh` is the local equivalent of that gate — run it
  before opening a pull request.

## Step 6 — Optional: the hosted read model

```bash
bash scripts/dev-hosted.sh --check   # verify the scaffold
bash scripts/dev-hosted.sh           # start API + web shell
```

| Service | URL |
| --- | --- |
| API | `http://127.0.0.1:8000` |
| Web | `http://127.0.0.1:3000` |

It serves read-only views over the registry, slice trees, runs, and dispatches —
useful when you have more than one repository and want one screen across them.

## Decision documentation

Drake governs *how* work gets done (slice lifecycle, validation, dispatch).
Decisions about *what* to build and *why* should be captured as **Architecture
Decision Records (ADRs)** before decomposing into slices.

- **Template:** `templates/adr.md` — copy to `.docs/adr/YYYY-MM-DD-title.md` in your project repo
- **When to write an ADR:** any decision that affects architecture, product
  direction, technology choice, or operational practice across multiple slices
- **Status lifecycle:** `proposed` → `accepted` → `deprecated` → `superseded`
- **Traceability:** link slices back to ADRs with an `adr` field in the slice
  detail doc

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `error: externally-managed-environment` from pip | PEP 668 host. `ci_preflight.sh` already avoids this by using a repo-local `.venv`; do the same in your own scripts, or `python3 -m venv .venv` and install there. |
| `npm ci` fails | Run it from the repo root with `--prefix`, or `cd` into the package directory. Lockfiles are committed. |
| Playwright e2e fails with a missing browser | `npx --prefix apps/web playwright install chromium` once per machine. |
| `npm run test:e2e` points at the wrong app | Something else already owns port 3000. Re-run with `PLAYWRIGHT_PORT=3131 npm run test:e2e` — passing the port also forces a dedicated dev server instead of reusing whatever is on 3000. |
| `slice-agent-runner: command not found` | Build it first: `npm --prefix tools/slice-agent-runner ci && npm --prefix tools/slice-agent-runner run build`, then call `node tools/slice-agent-runner/dist/index.js …`. |

## What is not in this repository

The reference worker runtime — the orchestrator that schedules slices across
repositories, the dispatch queue, and the credentialed worker fleet — is operated
privately and is not part of this export. Adopters implement their own scheduler
and worker against [`adapters/CONTRACT.md`](../adapters/CONTRACT.md); the task
packet schema and the evidence contract are the stable interface.
