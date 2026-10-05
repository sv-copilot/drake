# SLICE-2: Charge tax on the invoice total

| Field | Value |
| --- | --- |
| Slice # | 2 |
| State | ready |
| Depends on | SLICE-1 |
| Automation eligible | true |

## Goal

`invoice.total_with_tax(lines, rate_bps)` applies a basis-point tax rate to the line total.

## Acceptance

- [ ] tax is applied to the summed line totals, not per line
- [ ] a zero rate changes nothing

## Validation

- [ ] the repository gate passes
  CHECK: bash scripts/ci_preflight.sh
