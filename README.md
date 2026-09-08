# fantasy-yolo

**A fantasy football agent server.** An [MCP](https://modelcontextprotocol.io)
server and a matching CLI that let you — or an agent you run — read and manage
your own ESPN Fantasy Football team.

[![CI](https://github.com/gagandaroach/fantasy-yolo/actions/workflows/ci.yml/badge.svg)](https://github.com/gagandaroach/fantasy-yolo/actions/workflows/ci.yml)
[![ESPN canary](https://github.com/gagandaroach/fantasy-yolo/actions/workflows/espn-canary.yml/badge.svg)](https://github.com/gagandaroach/fantasy-yolo/actions/workflows/espn-canary.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

```console
$ fy check-lineup
1 thing(s) to look at across 9 starters
  projected_zero: Josh Jacobs (RB/WR/TE) is projected 0.0 points by ESPN

$ fy player "Saquon Barkley"
Saquon Barkley (RB, PHI) is rostered by The white Bhatoyas
```

Ask an agent *"anything wrong with my lineup this week?"* or *"who has Saquon,
and what are they thin at?"* and get an answer from live league data.

---

## The one thing to understand first

**The human is the brain.** This server has no optimizer, no projections model,
and no opinion about which players are good. It answers questions accurately and
executes instructions carefully. It will tell you a starter is projected zero
points; it will never tell you to bench him.

That is a deliberate constraint, not a missing feature. See
[Why no optimizer](#why-no-optimizer).

## Install

Needs Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/gagandaroach/fantasy-yolo
cd fantasy-yolo
uv sync
uv run fy --help
```

Then follow **[docs/setup.md](docs/setup.md)** — two cookies out of your browser
and a small config file naming your league. Five minutes.

### As an MCP server

```json
{
  "mcpServers": {
    "fantasy-yolo": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/fantasy-yolo", "fantasy-yolo-mcp"]
    }
  }
}
```

No credentials in that stanza — deliberately. They live in a `chmod 0600` file
the config points at.

## Tools

Every tool is available identically over MCP and on the CLI, generated from one
definition, so the two cannot drift apart.

### Reading — always available

| Tool | CLI | What it answers |
|---|---|---|
| `get_roster` | `fy roster` | Your roster with slots, opponents, projections, injury designations |
| `check_lineup` | `fy check-lineup` | **One pre-kickoff check**: empty slots, byes, players out, already-locked, projected zero |
| `get_matchup` | `fy matchup` | Who you're playing, projected score both sides, who's yet to play |
| `get_league` | `fy league` | Rules, key dates, waiver system, standings |
| `get_budgets` | `fy budgets` | What *every* team can still spend, not just you |
| `find_players` | `fy find-players` | Search the pool, ranked on a basis **you** name |
| `get_player` | `fy player NAME` | One player, and which team rosters them |
| `get_team` | `fy team NAME` | Another team's roster |
| `get_position_counts` | `fy position-counts` | Every team's positional shape, for trade shopping |
| `get_transactions` | `fy transactions` | The league's transaction log, filterable |
| `get_pending` | `fy pending` | Your claims and trades ESPN hasn't processed yet |

### Writing — off by default

Set `write_enabled: true` in your config to turn these on. While it's false they
are **not registered at all**, so a model cannot see or offer them.

| Preview | Execute | Effect |
|---|---|---|
| `preview_lineup` | `execute_lineup` | Set your starting lineup |
| `preview_add_drop` | `execute_add_drop` | Add a free agent, drop a player, or both |
| `preview_waiver` | `execute_waiver` | Submit a waiver claim with a FAAB bid |
| `preview_cancel_waiver` | `cancel_waiver` | Cancel a pending claim |

Trades are designed but not yet built.

## How writes are made safe

ESPN's transaction API has **no dry run** and **no idempotency key**. A retried
write genuinely submits the move a second time. Everything below exists because
of those two facts.

**Two calls, one code.** Every write is split. `preview_*` shows the change in
player names and returns a short-lived, single-use code bound to that exact
transaction. `execute_*` refuses to run without it. An approval given for one
add cannot be spent on another, and a retried execute is refused rather than
double-submitted.

> **Being honest about what that guarantees.** It makes a write impossible as a
> side effect of a question, and forces the preview into the transcript. It does
> **not** guarantee a human read it — a model can call preview and execute in the
> same turn. The real human-in-the-loop guarantee is your MCP client's approval
> prompt on a tool marked `destructiveHint`. We set that annotation; your client
> decides what to do with it.

**Nothing is ever retried.** Retries are disabled at the HTTP adapter, because
`requests` and `urllib3` retry by default and this is the one platform where
that silently double-submits a waiver claim. A timeout is reported as
**unknown** — never as success, never as failure — with your roster re-read so
you can see for yourself.

**Your roster is re-read immediately before every write.** If anything moved
since the preview — you set a lineup on your phone — the write is refused rather
than silently clobbering it.

**Legality is checked client-side**, since ESPN won't tell you in advance:
roster space, slot eligibility, whether a player is actually free or actually
yours, your bid against your remaining budget and the league minimum, and
whether your league even uses FAAB.

**It can only ever touch your own team.** `isLeagueManager` and
`isActingAsTeamOwner` are hard-wired `false` with no parameter exposing them, and
your team id is pinned in config.

**Every write is logged** — intent before the request leaves, outcome after — so
an interrupted write still leaves something to reconcile against. Credentials
are redacted from every line.

## What this server does not know

Stated in the server's own instructions, so a model driving it is told up front
rather than left to invent:

- **No projections beyond ESPN's own number.** There is no model here.
- **No injury news, no news feed, no reporter text.**
- **No timestamps on injury designations.** ESPN reports a status word and
  nothing else. It will catch a player ruled out on Wednesday; it will **not**
  catch a Sunday-morning inactive.
- **No ranking of players on merit.**

A missing projection is returned as `null`, never as `0.0` — because ESPN really
does project some players at zero, and conflating the two invites a confident
wrong conclusion.

## Why no optimizer

Removing the optimizer doesn't remove decision-making from the product — it
moves it to you, where the context is. An automated optimizer on this platform
would also be operating with no dry run and no undo, which is a bad combination
for irreversible moves.

There's a second reason worth naming: if you drive this with an LLM, the
decision-making relocates into a general model with no current fantasy data. That
model will fill silence with confident, plausible, wrong detail. Hence the
section above — telling it loudly what it doesn't know is the compensating
control.

## Notes on ESPN's private API

Documented here because it is otherwise scattered across gists and half-wrong
repos. All verified against live ESPN.

| Fact | Detail |
|---|---|
| Read host | `lm-api-reads.fantasy.espn.com` |
| Write host | `lm-api-writes.fantasy.espn.com` — one `POST .../transactions/` endpoint for everything |
| Auth | `espn_s2` + `SWID` cookies. No OAuth, no API keys, no developer program |
| `X-Fantasy-Role` | **Not** an auth signal. Reads `NONE` on an authenticated `200` just as on an unauthenticated `401` |
| Dry run | Does not exist. `VALIDATE` / `PREVIEW` / `DRY_RUN` all `400` |
| Idempotency | Does not exist. `idempotencyKey` and `executionKey` both `400` |
| Body parsing | Strict, and happens **before** auth — so an unauthenticated POST returns `401` for a valid shape and `400` for an invalid one. A free, side-effect-free schema oracle |
| Wire slot names | `fromLineupSlotId` / `toLineupSlotId`. ESPN's client calls them `fromSlotId`/`toSlotId` internally and renames on the way out; sending the internal names `400`s |
| Errors | Match `TRAN_*` by **prefix** — the real constants ship in `_ONE` / `_PLURAL` / `_LM` variants |

Three shapes most public implementations get wrong, all confirmed correct here
by ESPN's own parser:

- A **future-week** lineup is `FUTURE_ROSTER`, not `ROSTER`.
- A **standalone drop** is `ROSTER`, not `FREEAGENT`.
- The **trade verbs** (`TRADE_ACCEPT`, `TRADE_DECLINE`, …) do exist.

A [daily canary](.github/workflows/espn-canary.yml) checks that ESPN still parses
the exact payloads we'd send. ESPN tightened `leagueHistory` in Aug 2025 and split
read/write hosts in Apr 2024, both without notice.

## Design

- **[docs/user-stories.md](docs/user-stories.md)** — 101 stories, the ground truth
- **[docs/design.md](docs/design.md)** — architecture, the write protocol, open questions
- **[docs/setup.md](docs/setup.md)** — getting your cookies

```
src/fantasy_yolo/
  espn/       vendored ESPN client (football), ours to fix
  read/       read wrappers + the raw fetches espn-api misses
  write/      payload builders, never-retry client, error interpretation
  policy/     lineup planner, legality, confirm tokens, audit log
  tools/      the 19 tools
  cli.py      Typer frontend      ─┐ both generated from one registry,
  mcp/        MCP frontend        ─┘ so they cannot drift
```

## Status

Reads are working and verified against a live league. Writes are built and their
payloads are validated by ESPN's own parser, but **no authenticated write has
been fired yet** — see `docs/design.md` §14. Trades are designed, not built.

## Before you use this

**Unofficial.** Not affiliated with, endorsed by, or sponsored by ESPN or
Disney. It drives a private, undocumented API that can change or break without
notice.

**It runs on your machine, with your credentials, on your own account.** It
operates no service and redistributes nothing.

**"Runs locally" is not "stays local."** Everything this server returns is handed
to whatever MCP client and model you configure — for most people, a hosted
service. There is no telemetry and no network connection other than to ESPN, but
that is not the same as your data staying on your machine.

**What you're risking.** ESPN's terms restrict unofficial automated access. ESPN
can suspend or terminate your account and your league, and neither this project
nor its author can restore anything they take. Read
[Disney's Terms of Use](https://disneytermsofuse.com/english/) and ESPN's
[Fair Play and Conduct](https://support.espn.com/hc/en-us/articles/115003845711-Fair-Play-and-Conduct)
rules and decide for yourself. Note ESPN ships its own "Auto Control" AI that
makes roster moves — automation is not itself against the spirit of the game —
but that is not permission to drive the private API from outside.

**`espn_s2` is a full ESPN/Disney session cookie, not a scoped token.** Leaking
it is account compromise. Never paste it into an issue, a chat, or a screenshot.

## Licence

[MIT](LICENSE). Permissive: use it, change it, ship it, sell it. The only thing
it asks is that the copyright notice travels with the code.

It covers this project's own code. It grants no rights to ESPN's data, marks, or
API, and it is not permission from ESPN.

### Vendored code

`src/fantasy_yolo/espn/` is a vendored copy of the football half of
[`espn-api`](https://github.com/cwendt94/espn-api) by Christian Wendt, also MIT.
Its licence is preserved verbatim at [LICENSE-espn-api](LICENSE-espn-api), as
MIT requires when redistributing.

It is vendored rather than depended on so defects in the read path can be fixed
directly. The first was a `POSITION_MAP` that could not convert a lineup slot
label back to its id for bench, IR or flex — which made lineup writes impossible.
Our changes are marked `fantasy-yolo:` in comments, and its own test suite runs
in our CI.
