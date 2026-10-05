# SLICE-3: Decide the rounding policy for tax

| Field | Value |
| --- | --- |
| Slice # | 3 |
| State | gated |
| Operator gate | operator decision |
| Automation eligible | false |

## Goal

Decide whether tax rounds half-up per invoice or per line, and write it down.

## Why this waits

The answer changes customer-visible amounts and it is a business decision, not a
technical one. Slices with an operator gate are never dispatched by the selector;
this one sits in the backlog until a person resolves it.
