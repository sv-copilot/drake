# Where Drake sits next to agentic coding tools

Drake is **not** a coding agent, an IDE, or a CI product. It is the governance
layer that decides *what* an agent is allowed to work on, *what evidence* proves
the work is done, and *when* a change is promoted toward production.

That makes the comparison below a complement, not a bake-off. The useful
question is not "which tool writes code better" — it is "what stops the code an
agent writes from reaching production unproven".

## At a glance

| Dimension | Drake | Agentic coding tools (Cline, Cursor, OpenHands, Aider, …) |
| --- | --- | --- |
| Primary job | Governance: scope, gates, evidence, promotion | Authoring: propose and apply code edits |
| Unit of work | A **slice** with acceptance criteria and a dependency tree | A prompt, a chat turn, or a task |
| Where state lives | In your repo (`.docs/`): backlog, dependency tree, slice detail docs, evidence JSON | In the tool's session or the editor's history |
| Tests before implementation | Enforced — a guardrail rejects output with no test files, and the verification gate checks the test diff | Varies; most tools will write tests when asked |
| Proof a change works | A run directory plus `pipelineRunEvidence` JSON: test files changed, test results, validation output | The tool reports what it did; a human checks |
| Branch discipline | One branch per slice, no direct pushes to integration branches, promotion gated | Usually edits your working tree or a single branch |
| Human gates | Product vision, slicing, architecture, and promotion are human decisions; agents suggest | Human reviews the diff |
| Portability | Adapter contract: any worker that emits a task packet and returns evidence can implement slices | Tool-specific; swapping tools means re-learning the workflow |
| Model choice | Per-tier routing, so mechanical work and reasoning can run on different models | Usually one model per session |
| Failure mode it prevents | "The agent said it's done" merging unproven work | Writing code slower than you would like |

## What each one is actually good at

**Use an agentic coding tool when** you already know what you want changed and
want it changed now. They are excellent authoring surfaces: fast edits, good
diffs, wide tool access, and they keep getting better.

**Use Drake when** more than one agent (or more than one repository) is in play,
or when the cost of unproven changes reaching production is higher than the cost
of waiting. Drake answers: what is dispatchable right now, in what order, with
what acceptance criteria, proven by what evidence, promoted by which gate.

**Use both.** Drake's adapters are deliberately tool-agnostic — a slice is handed
to whatever worker satisfies the task-packet contract, so your authoring tool is
a swappable component rather than the architecture.

## Honest limits

- Drake does not write code. With no worker adapter configured, it validates
  trees and gates and does nothing else.
- It is young. The governance contracts, schemas, and validators in this
  repository are stable enough to adopt; the ecosystem around them is small.
- It adds ceremony. For a single-repository, single-developer, low-risk change
  the slice machinery is more process than the change deserves — start with the
  evidence contract and grow into the rest.

## This is not a benchmark

No performance, cost, or quality numbers are claimed here: nothing in this
document was measured against the tools named. It describes *structural*
differences only. For the tools themselves, their own documentation is the
source of truth.
