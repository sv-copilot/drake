# Slice backlog

The human-readable surface. Keep it consistent with `.docs/slice_dependency_tree.json`,
which is what the selector and the validators actually read.

| Rank | Slice | State | Summary | Validation |
| --- | --- | --- | --- | --- |
| 1 | `SLICE-1` | ready | Add the invoice total helper | `bash scripts/ci_preflight.sh` |
| 2 | `SLICE-2` | ready | Charge tax on the invoice total (needs SLICE-1) | `bash scripts/ci_preflight.sh` |
| 3 | `SLICE-3` | gated | Decide the rounding policy for tax | operator decision |

`SLICE-3` is not automation-eligible: it carries an operator gate, so the selector skips it
and a person has to make the call before it becomes work.
