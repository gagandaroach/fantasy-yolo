# fantasy-yolo — User Stories

Ground truth for what this program is for. Every tool in the MCP server should
trace back to a story here. If a tool doesn't serve a story, it shouldn't exist;
if a story has no tool, the program isn't done.

## Premise

The ESPN Fantasy Football app is bad. It buries information you need, surfaces
information you don't, and makes routine questions take five taps. This project
is a **programmatic interface to the same data and actions**, so a human — via
whatever agent or chat client they already use — can ask plain questions and get
straight answers, then act on them.

**The human is the brain.** v1 makes no roster decisions. It answers questions
accurately and executes what it's told, carefully. An optimizer may come later;
it is explicitly not part of this MVP.

## Legend

| Tag | Meaning |
|---|---|
| `[R]` | Read-only. Cannot change anything. |
| `[W]` | Write. Mutates the account. Requires confirmation and audit. |
| `[MVP]` | In the first working version. |
| `[LATER]` | Wanted, deliberately deferred. |

Story IDs are stable. Reference them in commits, tests, and tool docstrings.

---

## A. Connection & Session

Getting authenticated and staying that way. Boring, but every other category
fails confusingly if this is wrong.

- **A-01** `[R]` `[MVP]` As a manager, I want to connect using my ESPN cookies so the tool can see my private league.
- **A-02** `[R]` `[MVP]` As a manager, I want to know whether my session is still alive *before* I try anything, so a dead cookie shows as "your login expired" and not as a confusing empty roster.
  *Use the `X-Fantasy-Role` response header as a zero-side-effect canary — it reads `NONE` when unauthenticated. A 401 on the write host cannot distinguish absent / malformed / expired.*
- **A-03** `[R]` `[MVP]` As a manager, I want to see which leagues and teams my account has, so I can pick the one to operate on.
- **A-04** `[R]` `[MVP]` As a manager, I want my league and team pinned in config, so no query or command can ever act on a team that isn't mine.
- **A-05** `[R]` `[LATER]` As a manager, I want to be told when my cookie is *nearing* expiry, so I can refresh it before a Sunday morning failure.
  *TTL is undocumented by anyone. Learn it empirically by logging canary results over weeks.*

## B. My Team

The questions asked most often, that the app answers worst.

- **B-01** `[R]` `[MVP]` As a manager, I want to see my full roster — name, position, lineup slot, NFL team, this week's opponent, and projection — in one response.
- **B-02** `[R]` `[MVP]` As a manager, I want to know **who on my roster is injured** and how serious, so I know what needs attention.
  *espn-api exposes only `injuryStatus` and `injured` — no timestamp, no news text. Sunday-morning inactives are invisible. State this limitation in the tool output rather than implying freshness.*
- **B-03** `[R]` `[MVP]` As a manager, I want to know who on my roster is **on bye** this week and in the coming weeks, so I can plan ahead instead of discovering it at kickoff.
- **B-04** `[R]` `[MVP]` As a manager, I want to see my starters and bench separately, so I can eyeball the lineup without decoding slot ids.
- **B-05** `[R]` `[MVP]` As a manager, I want to be warned about **empty or invalid starting slots**, because the single worst outcome in fantasy is starting nobody at a position.
- **B-06** `[R]` `[MVP]` As a manager, I want to know **when my lineup locks** and which of my players are already locked, so I know how much time I have.
  *Football's `Player` class does not expose lock flags (baseball's does). Derive from the pro schedule and the league's lock rule.*
- **B-07** `[R]` `[MVP]` As a manager, I want to know my remaining acquisitions and FAAB budget, so I know what moves I can still afford.
- **B-08** `[R]` `[LATER]` As a manager, I want a read on my roster construction — where I'm thin, where I'm stacked — so I know what to shop for.

## C. Matchup & Scoring

- **C-01** `[R]` `[MVP]` As a manager, I want to know **who I'm playing this week** and what their team looks like.
- **C-02** `[R]` `[MVP]` As a manager, I want projected scores for both sides, so I know if I'm favored.
- **C-03** `[R]` `[MVP]` As a manager, I want live scoring during games, including which of my players have finished and which haven't yet played.
  *"Yet to play" is the number that actually tells you whether you're winning. The app makes this hard to see.*
- **C-04** `[R]` `[MVP]` As a manager, I want a position-by-position comparison against my opponent, so I can see where the matchup is won or lost.
- **C-05** `[R]` `[MVP]` As a manager, I want my record and standings position.
- **C-06** `[R]` `[LATER]` As a manager, I want to see every matchup in the league this week, so I can follow races that affect my seeding.
- **C-07** `[R]` `[LATER]` As a manager, I want my score history across the season, so I can see whether I'm actually good or just lucky.

## D. League Context

The rules and shape of the league — needed to answer almost everything else correctly.

- **D-01** `[R]` `[MVP]` As a manager, I want the league's roster and scoring settings, so answers reflect *my* league's rules and not generic assumptions.
  *Read raw `rosterSettings.lineupSlotCounts` keyed by slot id. Do NOT use football's `Settings.position_slot_counts` — it positionally zips labels against counts and silently misaligns them.*
- **D-02** `[R]` `[MVP]` As a manager, I want the key dates and rules — trade deadline, waiver process day and hour, minimum bid, acquisition limits.
- **D-03** `[R]` `[MVP]` As a manager, I want the current standings with records and points for/against.
- **D-04** `[R]` `[MVP]` As a manager, I want to see the other teams and who manages them.
- **D-05** `[R]` `[MVP]` As a manager, I want recent league activity, so I know what everyone else has been doing.
- **D-06** `[R]` `[LATER]` As a manager, I want power rankings, as a sanity check on the standings.

## E. Player Research

- **E-01** `[R]` `[MVP]` As a manager, I want to look up any player and get status, stats, projection, and ownership.
- **E-02** `[R]` `[MVP]` As a manager, I want to know **who owns a given player** — me, another team, or nobody — because that determines whether I'm adding him or trading for him.
- **E-03** `[R]` `[MVP]` As a manager, I want to compare two players side by side, so I can settle a start/sit or a trade question myself.
- **E-04** `[R]` `[MVP]` As a manager, I want a player's recent game log, so I can judge form rather than season averages.
- **E-05** `[R]` `[MVP]` As a manager, I want to resolve a name I typed to an actual rostered player, with team and position echoed back, so I never act on the wrong person.
  *Name collisions, Jr./Sr. suffixes, D/ST as team entities, and kickers are all real hazards. A misresolved DROP is permanently unrecoverable.*
- **E-06** `[R]` `[LATER]` As a manager, I want positional rankings across the league, so I know what "good" looks like at each spot.

## F. Free Agency & Waivers

- **F-01** `[R]` `[MVP]` As a manager, I want to see who's available at a position, **sorted by something useful** rather than by popularity.
  *`free_agents()` defaults to 50 sorted by `percentOwned` behind a hand-rolled filter header. Widen the pool and re-sort; the default view is popularity-biased and shallow.*
- **F-02** `[R]` `[MVP]` As a manager, I want trending adds and drops, so I can see what the market is doing.
- **F-03** `[R]` `[MVP]` As a manager, I want to find plausible replacements for a specific injured or bye-week starter.
- **F-04** `[W]` `[MVP]` As a manager, I want to add a free agent, dropping someone specific to make room, and see exactly who's coming and going before it happens.
- **F-05** `[W]` `[MVP]` As a manager, I want to submit a waiver claim with a FAAB bid.
- **F-06** `[R]` `[MVP]` As a manager, I want to see my pending waiver claims.
- **F-07** `[W]` `[MVP]` As a manager, I want to cancel a pending waiver claim I've changed my mind about.
- **F-08** `[W]` `[MVP]` As a manager, I want to drop a player outright, with a hard confirmation, because this is the least reversible thing in the entire product.

## G. Trades

The user's own headline case: *"who can I trade for this person?"*

- **G-01** `[R]` `[MVP]` As a manager, I want to find which teams roster a given position, so I know who to talk to.
- **G-02** `[R]` `[MVP]` As a manager, I want to see a specific team's roster, so I can look for a fit.
- **G-03** `[R]` `[MVP]` As a manager, I want to know which teams are **weak where I'm strong and strong where I'm weak**, so trade targets suggest themselves.
- **G-04** `[R]` `[MVP]` As a manager, I want to lay a proposed trade side by side — what I give, what I get, and what each roster looks like after — so I can judge it myself.
- **G-05** `[W]` `[MVP]` As a manager, I want to propose a trade to another team, with an optional message.
- **G-06** `[R]` `[MVP]` As a manager, I want to see trades proposed *to* me and trades I have outstanding.
- **G-07** `[W]` `[MVP]` As a manager, I want to accept or decline a trade offer.
- **G-08** `[W]` `[MVP]` As a manager, I want to cancel a trade I proposed.
- **G-09** `[R]` `[MVP]` As a manager, I want to be told if a trade would leave a roster illegal, before I propose it — since ESPN offers no dry run.

## H. Roster Moves

- **H-01** `[W]` `[MVP]` As a manager, I want to set my starting lineup by naming players and slots, and have the tool work out the moves.
  *Declarative desired state, not imperative swaps. Read roster → diff → one batched transaction → re-read and verify.*
- **H-02** `[W]` `[MVP]` As a manager, I want to swap two players between starting and bench, as a shorthand for the common case.
- **H-03** `[W]` `[MVP]` As a manager, I want to set a **future week's** lineup in advance, so a bye week or an early kickoff doesn't catch me out.
  *Requires envelope type `FUTURE_ROSTER`, not `ROSTER`. Every published repo gets this wrong.*
- **H-04** `[W]` `[MVP]` As a manager, I want to move an eligible player to IR to free a roster spot.
- **H-05** `[R]` `[MVP]` As a manager, I want to preview any roster move — the exact before and after — before committing to it.

## I. History

- **I-01** `[R]` `[MVP]` As a manager, I want the league transaction log, filterable, so I can see who added or dropped whom and when.
- **I-02** `[R]` `[LATER]` As a manager, I want draft results, to see how the season started.
- **I-03** `[R]` `[LATER]` As a manager, I want my head-to-head history against a given opponent, for trash-talk purposes.

## J. Safety & Operations

Not user-facing features, but the stories that keep the rest trustworthy. These
exist because ESPN provides **no dry run and no idempotency key** — a retried
write genuinely double-submits.

- **J-01** `[R]` `[MVP]` As a manager, I want every write to show me exactly what it will do, in player names rather than ids, before it happens.
- **J-02** `[W]` `[MVP]` As a manager, I want a kill switch that disables all writes, so I can run in read-only mode whenever I want.
- **J-03** `[R]` `[MVP]` As a manager, I want an append-only audit log of every request and response, so I can reconstruct what happened.
- **J-04** `[R]` `[MVP]` As a manager, I want a failed or interrupted write to leave a *recoverable* state — re-reading and recomputing rather than blindly retrying.
- **J-05** `[R]` `[MVP]` As a manager, I want the tool to refuse to act on any team but mine, and to never present itself as league manager.
  *`isLeagueManager` and `isActingAsTeamOwner` hard-wired false, with no parameter exposing them. ESPN runs different server-side validation in LM mode; controlling a second team is the fastest expulsion in ESPN's Fair Play rules.*
- **J-06** `[R]` `[MVP]` As a manager, I want errors explained in plain language — roster full, slot limit, roster locked — rather than raw ESPN error codes.
  *Match `TRAN_*` error constants by prefix; there are `_ONE` / `_PLURAL` / `_LM` variants. Never treat a 400 as "nothing happened."*
- **J-07** `[R]` `[LATER]` As a manager, I want to be warned when I'm churning free agents, since cycling players through waivers is explicitly expellable under ESPN's Fair Play rules.

---

## Explicitly Not In Scope (v1)

- **Any automated decision-making.** No optimizer, no projections model, no "the bot picks." The human decides; the tool fetches and executes.
- **Autonomous scheduled operation.** No cron setting lineups unattended.
- **Live draft.** That is a real-time socket protocol, not this endpoint.
- **League-manager operations.** Settings changes, editing other teams, forcing transactions.
- **Multi-team or multi-account operation.**
