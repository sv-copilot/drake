# Getting started

1. Clone `sv-copilot/drake` (public OSS export).
2. Copy `.docs/examples/projects-registry.example.json` to your operator layout.
3. Install slice-pipeline-local from `templates/slice-pipeline-local/`.
4. Run `bash scripts/ci_preflight.sh` before opening a PR.

## Decision documentation

Drake governs *how* work gets done (slice lifecycle, validation, dispatch).
Decisions about *what* to build and *why* should be captured as **Architecture
Decision Records (ADRs)** before decomposing into slices.

- **Template:** `templates/adr.md` — copy to `.docs/adr/YYYY-MM-DD-title.md` in your project repo
- **When to write an ADR:** Any decision that affects architecture, product
  direction, technology choice, or operational practice across multiple slices
- **Status lifecycle:** `proposed` → `accepted` → `deprecated` → `superseded`
- **Traceability:** Link slices back to ADRs by adding an `adr` field in the
  slice detail doc (`.docs/planning/projects/<repo>/slices/<SLICE-ID>.md`)

Full guides land in later documentation slices.
