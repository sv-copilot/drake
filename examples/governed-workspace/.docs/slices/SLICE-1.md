# SLICE-1: Add the invoice total helper

| Field | Value |
| --- | --- |
| Slice # | 1 |
| State | ready |
| Tier | P0 |
| Automation eligible | true |

## Goal

`invoice.line_total(quantity, unit_price_cents)` returns the total in cents.

## Acceptance

- [ ] a line total multiplies quantity by unit price
- [ ] a zero quantity is allowed and totals zero

## Validation

- [ ] the repository gate passes
  CHECK: bash scripts/ci_preflight.sh
