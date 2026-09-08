# fantasy-yolo — Design

Implementation spec. The needs live in [user-stories.md](./user-stories.md);
this document says how they get built. Story IDs are cited throughout — if a
decision here has no story behind it, it is a decision this document is making
on its own, and it says so.

## 1. What this is

An MCP server, and an equivalent CLI, that give a human a programmatic
interface to their own ESPN Fantasy Football account. It answers questions
about a league accurately and executes roster instructions carefully.

**The human is the brain** (X-01). Nothing here ranks players on merit, picks a
lineup, or decides a trade. Where a story sounds like judgment, it has been
reduced to arithmetic over the league's own settings — see §4.3.

Reads come from [`espn-api`](https://github.com/cwendt94/espn-api). Writes go
through a client this project owns, because `espn-api` has none.

## 2. Platform constraints

These are ESPN's, not ours. Every subsequent decision is downstream of them.

| Constraint | Consequence |
|---|---|
| **No dry run.** `executionType` accepts `EXECUTE`, `CANCEL`, `PROCESS`. `VALIDATE` / `PREVIEW` / `DRY_RUN` all `400`. | Legality must be pre-checked client-side (§7.2). No flag or tool name may imply a dry run exists (M-04). |
| **No idempotency key.** `idempotencyKey` and `executionKey` both `400`. | A retried write double-submits. Never retry a mutation (J-04, M-16). |
| **Body is deserialized before auth.** A well-formed unauthenticated POST returns `401`; a malformed one returns `400`. | Free, side-effect-free schema oracle for CI (§11.2). |
| **Strict deserialization.** Any unknown envelope key `400`s. | Build payloads from an explicit allowlist, never by dumping a dict. |
| **The read host also accepts `POST /transactions/`** and returns `401`, not `405`. | Host choice is not a safety barrier. Read-only-ness is enforced in our code (J-02). |
| **`espn_s2` has no readable expiry.** The user pastes a value, not a cookie with attributes. | Track capture age (A-05). Detect a dead session from the **HTTP status** — `401`/`403` — not from `X-Fantasy-Role` (A-02); see below. |
| **`scoringPeriodId` and `matchupPeriodId` diverge** in the playoffs and roll over mid-week. | Every week-sensitive call resolves and echoes its week (M-13). |

### 2.1 The write endpoint

```
POST https://lm-api-writes.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{leagueId}/transactions/
Content-Type: application/json          # mandatory — 415 without it
Cookie: espn_s2=...; SWID={...}
```

> **`X-Fantasy-Role` is not a liveness canary.** Measured against the live
> league endpoint on 2026-09-08: an unauthenticated request returns `401` with
> `X-Fantasy-Role: NONE`, and an authenticated request returns `200` with
> `X-Fantasy-Role: NONE`. The header is present in both and identical in both,
> so it cannot distinguish them. Earlier research established only the
> unauthenticated half and inferred the rest; the inference was wrong. Use the
> status code. The header is kept in error messages as a diagnostic breadcrumb.

`x-fantasy-*` headers, `Origin`, `Referer` and `User-Agent` are optional and
inert. There is no CSRF token — the preflight allows only `content-type`,
`x-fantasy-source`, `x-fantasy-platform`, and the host reflects any `Origin`.

Envelope keys, from ESPN's own `createTransaction`:

```
analysis, bidAmount, comment, executionType, expirationDate,
isActingAsTeamOwner, isLeagueManager, memberId, relatedTransactionId,
scoringPeriodId, skipTransactionCounters, teamId, type, items
```

`memberId` is the **braced** SWID. `executionType` defaults to `EXECUTE`.
`scoringPeriodId` defaults to `league.status.latestScoringPeriod` — a field
`espn-api` does not parse, so it comes from a raw fetch (§4.1).

Item shape, mirroring ESPN's own builder: always `playerId`; `type` when set;
`fromTeamId` / `toTeamId` only when truthy; `fromLineupSlotId` /
`toLineupSlotId` only when defined.

> **The wire names are `fromLineupSlotId` / `toLineupSlotId`.** ESPN's client
> calls them `fromSlotId` / `toSlotId` internally and renames on the way out.
> Sending the internal names `400`s. At least one widely-copied public repo has
> this wrong.

### 2.2 Operations

| Operation | Envelope `type` | Items |
|---|---|---|
| Lineup change | `ROSTER` | `{playerId, type: LINEUP, fromLineupSlotId, toLineupSlotId}`, **batched into one transaction** |
| Future-week lineup | `FUTURE_ROSTER` | same — used when the draft is done and the requested period is past `latestScoringPeriod` |
| Add (optionally with drop) | `FREEAGENT` | `{playerId, type: ADD, toTeamId}` then `{playerId, type: DROP, fromTeamId}` |
| Standalone drop | `ROSTER` | `{playerId, type: DROP, fromTeamId}` |
| Waiver claim | `WAIVER` | as ADD; FAAB via envelope-level `bidAmount` |
| Cancel waiver | `WAIVER` | `executionType: CANCEL`, `relatedTransactionId` |
| Propose trade | `TRADE_PROPOSAL` | mirrored `{playerId, type: TRADE, fromTeamId, toTeamId}`, plus `expirationDate`, `comment` |
| Accept trade | `TRADE_ACCEPT` | `teamId`, `relatedTransactionId`, optional DROP items to make room |
| Decline trade | `TRADE_DECLINE` | `teamId`, `comment`, `relatedTransactionId` |

Three of these are wrong in every published implementation: standalone drop
uses `ROSTER` (not `FREEAGENT`), future weeks use `FUTURE_ROSTER`, and the
trade verbs exist at all — one popular repo declares them "never captured, do
not implement."

`TRADE_UPHOLD` and `TRADE_VETO` are league-manager operations and are out of
scope (X-04).

## 3. Architecture

```
fantasy_yolo/
  registry.py     the @tool decorator — single source of truth (M-18)
  config.py       league/team pinning, kill switch, limits
  creds.py        cookie loading, X-Fantasy-Role canary
  read/           espn-api wrappers + raw fetches it misses
  write/          payloads, client, errors — NO imports from policy/ or tools/
  policy/         legality, locks, audit, confirmation tokens
  tools/          one module per tool group; plain typed functions
  mcp/server.py   registry -> FastMCP tools
  cli.py          registry -> Typer commands
```

`write/` imports nothing from the rest of the package (M-08). It is the piece
worth extracting as a standalone `espn-write` library once the payloads are
proven, and keeping it dependency-free now makes that a `git mv` later.

### 3.1 One definition, two interfaces (M-18)

Tools are plain typed functions. A small internal decorator records them, and
both frontends read the registry. Neither frontend is the source of truth, so
they cannot drift.

```python
@tool(kind=Kind.READ)
def get_roster(week: int | None = None) -> RosterView:
    """Your roster with slots, opponents and projections."""
```

`kind` is load-bearing in three places at once:

- **MCP annotations** — `READ` sets `readOnlyHint`, `WRITE_EXECUTE` sets
  `destructiveHint` (J-08).
- **CLI behavior** — execute commands require an explicit `--yes` or an
  interactive confirm.
- **Read-only mode** — `J-02` requires that disabled write tools are *not
  registered at all*, so a model cannot see or offer them. That is a filter over
  the registry at startup, not an error return.

We depend on the decorator we own rather than FastMCP's, so `tools/` stays
framework-free and unit-testable without a server (M-03).

**Consequence worth naming:** because MCP annotations are per-tool, preview and
execute must be **two separate tools**, not one tool with a mode parameter.
A single tool cannot be both `readOnlyHint` and `destructiveHint`.

## 4. Reads

### 4.1 What `espn-api` doesn't give us

Fetched raw, or derived:

- `league.status.latestScoringPeriod` — never parsed by `espn-api`, and the
  correct default for a write's `scoringPeriodId`. Using `currentMatchupPeriod`
  instead is a real bug in a published MCP server.
- Raw `rosterSettings.lineupSlotCounts`, keyed by slot id. Prefer it over
  football's `Settings.position_slot_counts`, which zips
  `list(POSITION_MAP.values())[:n]` positionally against
  `lineupSlotCounts.values()`. **Measured 2026-09-08: that produces the correct
  answer**, because ESPN returns 25 contiguous keys `"0".."24"` in order and
  `POSITION_MAP`'s first 25 values are the labels for ids 0..24 in the same
  order. The alignment is a coincidence of two orderings, not a lookup, and it
  breaks silently if ESPN ever returns a sparse or reordered map. An earlier
  draft of this document called it broken; that was wrong. Reading the raw dict
  by key costs one line and does not depend on the coincidence.

- A complete slot label -> id map. `POSITION_MAP` is bidirectional but its
  label->id half is **incomplete**: `BE`, `IR` and `RB/WR/TE` are absent, so
  `POSITION_MAP[POSITION_MAP[20]]` raises. `Player.lineupSlot` is produced from
  the id->label half, so converting a slot label back to an id — which every
  lineup write must do — silently yields `None` for bench, IR and flex. Invert
  the id->label half instead. This one is a real defect, not a fragility.
- Lineup lock state. Football's `Player` exposes no lock flags (baseball's
  does). Derive kickoff from the pro schedule and apply the league's lock rule.
- Waiver-vs-free-agent status and clear time (F-11).

### 4.2 Tool surface

Read one-story-one-tool, the story list implies fifty-plus tools, several of
which answer the same question under different names. A model selecting among
those fails silently rather than erroring. Target is **~15 tools, with no two
that could plausibly answer the same question.**

| Tool | Stories |
|---|---|
| `get_roster` | B-01, B-02, B-08 |
| `check_lineup` | B-03, B-05, B-06, **B-09** |
| `get_matchup` | C-01, C-02, C-03, C-04, C-06 |
| `get_league` | D-01, D-02, D-03, D-04, D-06 |
| `find_players` | E-02, E-06, F-01, F-02, F-03, F-11, G-01 |
| `get_player` | E-01, E-03, E-04, E-05 |
| `get_team` | G-02, G-03 |
| `get_transactions` | I-01, F-10 |
| `get_pending` | F-06, G-06, G-10 |
| `get_history` | C-07, I-02, I-03 |
| `get_budgets` | B-07, F-09 |
| `preview_lineup` / `execute_lineup` | H-01, H-02, H-03, H-04, H-06 |
| `preview_transaction` / `execute_transaction` | F-04, F-05, F-08 |
| `preview_trade` / `execute_trade` | G-04, G-05, G-07, G-08, G-09 |
| `cancel_pending` | F-07, G-08 |

Seventeen. `find_players` is deliberately one search over a pool parameter
rather than five near-synonyms.

### 4.3 Judgment reduced to arithmetic

Four stories were rewritten during review because they required a strength
model — X-01 in disguise. The implementations must stay mechanical:

- **B-08** — count rostered players by position against the league's own slot
  counts and roster limits. Not "where am I thin."
- **G-03** — every team's positional counts in one table. Not "who is weak."
- **F-03** — free agents at a position, bye-week filtered. Not "plausible
  replacements."
- **F-01 / E-06** — rank on a basis the caller names, echoed back in the
  answer. Never a default that encodes an opinion.

## 5. Response contract (M-14)

Every tool returns a small set of explicitly listed flat fields plus a
one-line human summary. Never a serialized `espn-api` object — `Player`
carries a nested per-week stats dict, so a naive roster dump is tens of
kilobytes, and `get_matchup`, `get_transactions` and `get_history` are each a
context bomb without this.

Every response carries:

- `season`, `week_resolved`, `fetched_at` (M-13) — so "this week" can never mean
  two different weeks to the tool and the user.
- `total` alongside `returned` on any list, with `limit`/`offset`. Truncation
  is stated, never silent.
- Sample size on anything computed from completed games, and a plain statement
  when it is too small to mean anything. It is Week 1; several tools currently
  return empty lists, and a model will narrate `[]` as a finding.

The CLI renders the same objects as tables; the MCP server returns them
structured with the summary attached.

### 5.1 What the server says it doesn't know (M-15)

The server's own instructions state, once and up front: no projections beyond
ESPN's own number, no injury news, no timestamps, no news feed.

This is the compensating control for X-01. Removing the optimizer does not
remove decision-making from the product — it relocates it into a general chat
model with no current fantasy data. Handed the bare word `QUESTIONABLE` with no
provenance, that model will produce a confident recovery narrative, and the
user cannot see the seam. Telling it what it may not infer is the cheapest
high-value line in this design.

## 6. The write protocol

### 6.1 Two calls, one token (J-01)

```
preview_*  →  human-readable before/after, in player names, plus a
              single-use code bound to a hash of the exact payload
execute_*  →  refuses to run without that code
```

The token is bound to the serialized transaction, so an approval given for one
add cannot be spent on another, and a retried execute is refused rather than
double-submitted — the same mechanism that closes the retry hazard.

> **Be honest about what this guarantees.** In an MCP server the reader of a
> preview string is a model, which can call preview and execute in the same
> turn. The token forces the preview into the transcript and makes a write
> impossible as a side effect of a question. It does **not** guarantee a human
> saw it. That guarantee lives in the client's approval prompt on a
> destructively-annotated tool (J-08), and the README must say so plainly
> rather than implying the token does more than it does.

### 6.2 Desired state, not commands

Writes are declarative. `execute_lineup` takes a target arrangement, not a
sequence of swaps:

1. Read roster and pending transactions fresh.
2. Abort if state no longer matches what was approved, naming what changed
   (J-09) — this is what stops a lineup set on the phone being silently
   clobbered.
3. Compute the item diff; drop no-op items where `fromLineupSlotId ==
   toLineupSlotId` (an all-no-op transaction `409`s with "TransactionItems are
   missing").
4. Preserve vacate-then-promote ordering.
5. POST **once**, batched.
6. Re-read and diff to confirm the applied state.

A crashed run is safe to re-run because intent is recomputed from current
state rather than replayed.

### 6.3 Unknown outcomes (J-04)

On timeout, dropped connection, or unparseable response, the outcome is
**unknown** — not success, not failure. Report it as unknown, read back roster
and pending transactions, and let the human see whether it landed.

Never retry a write. This must be enforced at the transport layer too: every
Python HTTP stack retries by default, so backoff on `429`/`5xx` is configured
for **reads only** (M-16), and one write is in flight at a time.

### 6.4 The lineup tiebreak rule

`H-01` accepts player names with slots optional, and the preview lays out a
legal arrangement. This resolves a genuine conflict — a casual manager cannot
name slots, while an implementer given "work out the moves" will build a slot
solver and cross X-01 without noticing.

Assigning named players to eligible slots is constraint satisfaction over the
league's own rules, not a judgment about who is better. The boundary is one
rule, and it is not optional:

> **Where several legal arrangements exist, pick deterministically — lowest
> slot id — and state which rule was used. Never by projection.**

## 7. Safety

### 7.1 Invariants in code, not config

- `isLeagueManager` and `isActingAsTeamOwner` are hard-wired `False`, with no
  parameter anywhere exposing them (J-05). ESPN ships paired `_LM` variants of
  every roster-limit error constant, which is direct evidence it runs different
  server-side validation in that mode.
- `teamId` is pinned from config (A-04), with a post-read assertion that the
  roster being mutated belongs to it.
- The kill switch filters the registry at startup (J-02).
- Credentials are redacted from every log line, error message and tool
  response (J-03).

Multiple leagues on one account is explicitly supported (A-06). The
prohibition is on acting for someone else, not on managing several of your own
teams (X-05).

### 7.2 Client-side legality

With no dry run, everything checkable is checked before the POST: slot
eligibility via `player.eligibleSlots`, per-slot counts and roster size from
raw `lineupSlotCounts`, acquisition limits against `team.transactionCounter`,
IR eligibility, FAAB minimum bid, trade deadline.

`G-09` states what it cannot know: ESPN decides trade legality at acceptance.
A false clean bill of health is worse than no check, because the manager
proposes the trade *because* the tool said it was fine.

### 7.3 Audit log (J-03)

Writes only. Intent written **before** the request leaves, outcome written
**after** — a process killed mid-write must leave evidence of what was
attempted, which is what makes §6.3's read-back reconcilable. Reads are logged
by name and arguments only.

Never log full requests. Every ESPN request carries the session cookie in a
`Cookie` header; "log every request and response" mandates a permanent
plaintext copy of the user's credentials, in the exact file someone attaches
to a GitHub issue when the server won't start.

### 7.4 Churn (J-07)

Cycling players through waivers is expellable under ESPN's Fair Play rules.
Default threshold: warn on re-adding a player dropped within 7 days, or more
than 4 adds in a scoring period. Configurable, since leagues vary.

## 8. Credentials

`espn_s2` is a full ESPN/Disney session cookie, not a fantasy-scoped token.
Leaking it is account compromise.

Loaded from a file path or secret-store reference named in the client config,
**never as a literal value inside it** (M-09) — that JSON file is what users
paste into issues and screenshots. This pulls against M-02's "minimal
configuration"; M-02 yields.

The tool never logs into ESPN, drives a browser, or refreshes cookies (X-06).

## 9. Errors (J-06, M-10)

ESPN's own handler makes no distinction between `400` and `409` and reads the
rule out of `details[].type`. So **never treat a `400` as "malformed, nothing
happened."**

Match `TRAN_*` constants by **prefix** — the real ones include
`TRAN_ROSTER_LIMIT_EXCEEDED_ONE` / `_ONE_LM` / `_PLURAL` / `_PLURAL_LM`,
`TRAN_ROSTER_POSITION_LIMIT_EXCEEDED(_LM)`, `TRAN_ROSTER_SLOT_LIMIT_EXCEEDED(_LM)`.
Exact-string matching breaks on the plural and LM variants.

Distinguish `415` (content-type), `404` (path), `401` (auth — indistinguishable
between absent, malformed and expired, so use the `X-Fantasy-Role` canary
instead). `FAILED_ROSTERLOCK` is a real observed status. `401` on a read means an expired
cookie or ids that do not belong to this account — say both, since they are
indistinguishable from the response.

Parse defensively: the accepted enum sets are open, not closed.

## 10. Caching

Constructing an `espn-api` `League` pulls the league wholesale, and one
conversation asks ten to twenty questions — so twenty questions become twenty
full fetches. Session-scoped cache with a stated max age, an explicit
force-refresh, and cached answers reporting their age.

Two carve-outs, both correctness rather than preference:

- **Live scoring is never cached.** A cached score presented as live is a wrong
  answer.
- **The post-write read-back is never served from cache** (§6.2 step 6).

## 11. Testing

### 11.1 Offline (M-03)

The full suite runs with no credentials and no network. Fixtures recorded from
real responses; the write client tested at the payload-construction boundary.

### 11.2 The schema oracle (M-04)

ESPN validates body shape before authenticating, so an **unauthenticated** POST
returns `401` for a well-formed body and `400` for a malformed one. That is a
free, side-effect-free regression test for every payload the builder emits.

> **Never run it with cookies attached.** The identical request then executes.

### 11.3 Live verification

Read shapes validate against live ESPN. Write payloads validate only against
fixtures and the oracle — a write validated against ESPN *is* a real
transaction, and the natural way to make that pass is to build a fake dry run,
which is the worst outcome available (M-04 forbids any flag, code path or tool
name implying one).

The write path is proven by a documented **manual canary**, run before each
release and recorded in the release checklist:

1. Unauthenticated POST — confirm `405` / `401` / `400`. Zero risk.
2. Authenticated read — confirm a `200` and real roster data. Do **not** expect
   `X-Fantasy-Role` to change; it reads `NONE` either way.
3. **Toggle-and-revert**: move one bench player to a starting slot and back,
   capturing both responses.

Step 3 is the only thing that converts this design from well-corroborated to
verified. The CLI (M-18) exists partly so it can be done without an MCP client
in the loop.

## 12. Project deliverables

Not architecture, but the spec is incomplete without saying who owns them.

**README** (K-01, K-02, K-06, K-10, L-01). One page, and it carries four
statements that exist nowhere else:

- Unofficial, not affiliated with or endorsed by ESPN or Disney; uses a
  private, undocumented API that may change or break without notice (K-01).
- What the project factually is — runs on your machine, your credentials, your
  account only, operates no service, redistributes nothing — alongside its
  stated purpose of research, study and personal use, and a link to the
  governing terms (K-02).
- **"Runs locally" is not "stays local"** (K-06). Everything this server
  returns is handed to whatever MCP client and model the user configured, which
  for most users is a hosted service. A user who reads a no-telemetry claim and
  concludes "this is private" has been misled by our own honesty section.
- What the user is risking, in plain language (K-10): ESPN's terms restrict
  unofficial access, ESPN can suspend or terminate an account and a league, and
  neither this project nor its author can restore anything they take.

It also states that MIT covers this project's code only and grants no rights to
ESPN's data, marks, or API (L-01) — kept out of `LICENSE` so that file stays
unmodified MIT and machine-detectable. And it records a **last-verified stamp**:
the date and league settings the write path was last exercised against. For an
unversioned private endpoint on a seasonal product, that tells a stranger in
Week 12 next year something semantic versioning cannot.

**Setup docs** (A-01, A-03, M-01, M-09). Getting `espn_s2` and `SWID` out of a
browser is the hardest thing this project asks of a non-technical user and the
gate on every other story. Say what `espn_s2` actually is — a full session
cookie, not a scoped API key — because people paste it into Discord and GitHub
issues precisely because it looks like one.

**CI** (M-06, M-07, M-17). Tests and lint on every push; pinned dependencies;
and a dependency-license allowlist that treats missing or ambiguous metadata as
a failure, clearable only by a recorded, dated exception. PyPI license metadata
is routinely absent or contradicts the sdist, so a naive check either blocks
everything or passes everything — and the second is what ships.

**Release** (M-11, M-12). Changelog and semantic versioning; a contributing
guide, pointing at GitHub's private vulnerability reporting rather than
promising a disclosure response window this project cannot honor. No CLA.

**Attribution** (L-04, K-09). Credit `espn-api` for the read layer. Record that
the write payloads were derived from ESPN's own client bundle, with the hash
pinned (§14.7). No scraped or redistributed ESPN data in the repo.

## 13. Build order

Story IDs run A→M, which is the reverse of safe build order: an agent working
top-down ships every write path in F, G and H before the audit log and kill
switch in J.

**Nothing in F, G or H is implemented until A-04, J-01, J-02, J-03, J-04, J-08
and J-09 are done and tested.**

Suggested sequence: registry and dual interface (M-18) → creds and canary →
reads → response contract → policy and audit → write client against the oracle
→ live canary → write tools.

## 14. Open questions

Settled by doing, not by discussion:

1. **Does an authenticated write succeed, and what does a 200 body look like?**
   One captured `EXECUTED` response exists in public, in a commented-out block
   in one repo. Everything downstream depends on this. Toggle-and-revert
   settles it in five minutes.
2. **`FUTURE_ROSTER` end-to-end.** Accepted as an envelope type; no captured
   success anywhere. Set next week's lineup and read it back.
3. **Waiver + `bidAmount` end-to-end**, and whether the response comes back
   `PENDING` until the waiver run.
4. **Is there a body-borne anti-forgery field?** Cannot be ruled out from
   unauthenticated `401`s, since a body field would be validated after auth.
   The first authenticated write settles it.
5. **Cookie casing** — `SWID` vs `swid`. Repos disagree. Standardize on
   uppercase for the cookie and the braced value for `memberId`, and verify.
6. **`espn_s2` TTL.** Undocumented by anyone. Instrument the canary and learn
   it empirically.
7. **Durability.** ESPN tightened `leagueHistory` in Aug 2025 and split hosts in
   Apr 2024, both without notice. Pin the bundle hash the payloads were derived
   from and add a canary that re-fetches and diffs the item builder.

## 15. Deferred

- **Decision layer.** An optimizer, a projections model, an evaluation harness
  that replays prior weeks against the baseline of "start ESPN's own
  projected-best lineup." Explicitly not v1 (X-01).
- **Scheduled read-only reminders** (X-02). A 10pm-Tuesday nudge is not a decision —
  but it is an unattended process holding write-capable cookies, which is a
  different risk surface. Revisit after v1 as a reminder, never as an actor.
- **Stat-correction detection.** Snapshot a completed week's box score, diff it
  against ESPN later. Permitted by X-01 as record-keeping, and no human can do
  it by hand — but it needs a snapshot store and a staleness lifecycle.
- **Extracting `write/`** as a standalone `espn-write` package, and offering it
  upstream to `espn-api`, once the payloads are proven.
