# Changelog

## Unreleased

### Fixed

- A preview no longer counts an empty IR slot as room for an add. ESPN places
  every add on the bench, so it rejected an add the preview had called legal.
- `fy roster` reports IR separately — `0 open of 16; IR 0 of 1 used` rather
  than `1 open of 17` — and gains `open_ir_spots`.
- `execute_add_drop` and `execute_waiver` work from the confirmation code
  alone, as `execute_lineup` already did.
- A circular import between `policy` and `tools` that broke importing a policy
  module first.

## 0.1.0 — 2026-09-08

First working version.

- 20 tools over MCP and CLI from one registry: roster, lineup check, matchup,
  league, budgets, player search, other teams, position counts, all rosters,
  transactions, pending moves.
- Writes, off by default: set lineup, add/drop, waiver claim, cancel claim —
  each split into preview and execute with a single-use confirmation code.
- Never-retry write client, re-read-before-write guard, client-side legality
  checks, and an audit log with credentials redacted.
- Vendored football half of `espn-api`, with the slot-map fix lineup writes
  need.
- Daily canary checking ESPN still parses the exact payloads sent.
