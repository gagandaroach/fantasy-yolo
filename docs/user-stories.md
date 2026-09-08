# User Stories

## A. Connection & Session

- **A-01** As a manager, I want to connect using my ESPN cookies, so the tool can see my private league.
- **A-02** As a manager, I want to know whether my session is still alive before I try anything, so an expired login reads as "your login expired" and not as an empty roster.
- **A-03** As a manager, I want to see which leagues and teams my account has, so I can pick the one to operate on.
- **A-04** As a manager, I want my league and team pinned in config, so nothing can act on a team that isn't mine.
- **A-05** As a manager, I want warning when my session is nearing expiry, so I can refresh it before it fails.

## B. My Team

- **B-01** As a manager, I want my full roster — name, position, lineup slot, NFL team, opponent, projection — in one response.
- **B-02** As a manager, I want to know who on my roster is injured and how serious.
- **B-03** As a manager, I want to know who is on bye this week and in coming weeks.
- **B-04** As a manager, I want my starters and bench shown separately.
- **B-05** As a manager, I want to be warned about empty or invalid starting slots.
- **B-06** As a manager, I want to know when my lineup locks and which players are already locked.
- **B-07** As a manager, I want my remaining acquisitions and FAAB budget.
- **B-08** As a manager, I want a read on my roster construction, so I know where I'm thin.

## C. Matchup & Scoring

- **C-01** As a manager, I want to know who I'm playing this week.
- **C-02** As a manager, I want projected scores for both sides.
- **C-03** As a manager, I want live scoring, including which of my players have finished and which have yet to play.
- **C-04** As a manager, I want a position-by-position comparison against my opponent.
- **C-05** As a manager, I want my record and standings position.
- **C-06** As a manager, I want to see every matchup in the league this week.
- **C-07** As a manager, I want my score history across the season.

## D. League Context

- **D-01** As a manager, I want the league's roster and scoring settings, so answers reflect my league's rules.
- **D-02** As a manager, I want the key dates and rules — trade deadline, waiver day and hour, minimum bid, acquisition limits.
- **D-03** As a manager, I want the standings with records and points for and against.
- **D-04** As a manager, I want to see the other teams and who manages them.
- **D-05** As a manager, I want recent league activity.
- **D-06** As a manager, I want power rankings.

## E. Player Research

- **E-01** As a manager, I want to look up any player and get status, stats, projection, and ownership.
- **E-02** As a manager, I want to know who owns a given player — me, another team, or nobody.
- **E-03** As a manager, I want to compare two players side by side.
- **E-04** As a manager, I want a player's recent game log, so I can judge form rather than season averages.
- **E-05** As a manager, I want a name I type resolved to a real player with team and position echoed back, so I never act on the wrong person.
- **E-06** As a manager, I want positional rankings across the league.

## F. Free Agency & Waivers

- **F-01** As a manager, I want to see who's available at a position, sorted by something useful rather than by popularity.
- **F-02** As a manager, I want trending adds and drops.
- **F-03** As a manager, I want plausible replacements for a specific injured or bye-week starter.
- **F-04** As a manager, I want to add a free agent and drop someone to make room, seeing exactly who's coming and going first.
- **F-05** As a manager, I want to submit a waiver claim with a FAAB bid.
- **F-06** As a manager, I want to see my pending waiver claims.
- **F-07** As a manager, I want to cancel a pending waiver claim.
- **F-08** As a manager, I want to drop a player outright, with a hard confirmation.

## G. Trades

- **G-01** As a manager, I want to find which teams roster a given position, so I know who to talk to.
- **G-02** As a manager, I want to see a specific team's roster.
- **G-03** As a manager, I want to know which teams are weak where I'm strong and strong where I'm weak.
- **G-04** As a manager, I want a proposed trade laid out side by side — what I give, what I get, and both rosters after.
- **G-05** As a manager, I want to propose a trade to another team, with an optional message.
- **G-06** As a manager, I want to see trades proposed to me and trades I have outstanding.
- **G-07** As a manager, I want to accept or decline a trade offer.
- **G-08** As a manager, I want to cancel a trade I proposed.
- **G-09** As a manager, I want to be told if a trade would leave a roster illegal, before I propose it.

## H. Roster Moves

- **H-01** As a manager, I want to set my starting lineup by naming players and slots, and have the tool work out the moves.
- **H-02** As a manager, I want to swap two players between starting and bench.
- **H-03** As a manager, I want to set a future week's lineup in advance.
- **H-04** As a manager, I want to move an eligible player to IR to free a roster spot.
- **H-05** As a manager, I want to preview any roster move — the exact before and after — before committing to it.

## I. History

- **I-01** As a manager, I want the league transaction log, filterable.
- **I-02** As a manager, I want draft results.
- **I-03** As a manager, I want my head-to-head history against a given opponent.

## J. Safety

- **J-01** As a manager, I want every write to show me what it will do, in player names rather than ids, before it happens.
- **J-02** As a manager, I want a kill switch that disables all writes, so I can run read-only.
- **J-03** As a manager, I want an append-only audit log of every request and response.
- **J-04** As a manager, I want a failed or interrupted write to leave a recoverable state.
- **J-05** As a manager, I want the tool to refuse to act on any team but mine, and to never present itself as league manager.
- **J-06** As a manager, I want errors in plain language — roster full, slot limit, roster locked — not raw error codes.
- **J-07** As a manager, I want warning when I'm churning free agents, since cycling players through waivers can get you expelled.

## K. Legal & Compliance

- **K-01** As a software engineer, I want the project to state plainly that it is unofficial and not affiliated with, endorsed by, or sponsored by ESPN or Disney.
- **K-02** As a software engineer, I want the project published for research, study, and personal use, so its purpose is unambiguous.
- **K-03** As a software engineer, I want the terms that govern this activity linked from the repo, so users can make their own informed decision.
- **K-04** As a software engineer, I want the project to document that it uses a private, undocumented API that may change or break without notice.
- **K-05** As a software engineer, I want the program to work only with credentials the user supplies for their own account, and to ship none.
- **K-06** As a software engineer, I want no telemetry and no data leaving the user's machine except requests to ESPN.
- **K-07** As a software engineer, I want the program to operate only on the authenticated user's own team.
- **K-08** As a software engineer, I want polite rate limiting, so the program is a good API citizen.
- **K-09** As a software engineer, I want no scraped or redistributed ESPN data committed to the repo.

## L. Licensing

- **L-01** As a software engineer, I want a permissive license (MIT), so anyone can use, modify, embed, and redistribute this without friction.
- **L-02** As a software engineer, I want every dependency to be permissively licensed, so downstream users inherit no copyleft obligations.
- **L-03** As a software engineer, I want dependency licenses checked automatically, so a copyleft dependency can't slip in.
- **L-04** As a software engineer, I want clear attribution for any code or API knowledge derived from other projects.
- **L-05** As a software engineer, I want contributions accepted without a CLA, so contributing is easy.

## M. Engineering & Operations

- **M-01** As a software engineer, I want to install and run the MCP server in one command.
- **M-02** As a software engineer, I want it to work with any MCP client over stdio, with minimal configuration.
- **M-03** As a software engineer, I want the full test suite to run without live credentials or network access.
- **M-04** As a software engineer, I want request and response shapes validated against ESPN without side effects, so I catch breakage before it costs a transaction.
- **M-05** As a software engineer, I want typed interfaces throughout.
- **M-06** As a software engineer, I want CI running tests and lint on every push.
- **M-07** As a software engineer, I want pinned dependencies and a reproducible environment.
- **M-08** As a software engineer, I want the read layer and the write layer independent, so the write client can be reused on its own.
- **M-09** As a software engineer, I want secrets loaded from the environment or a secret store, never from the repo.
- **M-10** As a software engineer, I want clear errors when ESPN changes its API, rather than silent wrong answers.
- **M-11** As a software engineer, I want a changelog and semantic versioning.
- **M-12** As a software engineer, I want a contributing guide, so others can add to this.

## Out of Scope

- **X-01** Automated decision-making. No optimizer, no projections model. The human decides.
- **X-02** Autonomous scheduled operation.
- **X-03** Live draft.
- **X-04** League-manager operations — settings changes, editing other teams, forcing transactions.
- **X-05** Multi-team or multi-account operation.
