# User Stories

## A. Connection & Session

- **A-01** As a manager, I want to connect using my ESPN cookies, so the tool can see my private league.
- **A-02** As a manager, I want to know whether my session is still alive before I try anything, so an expired login reads as "your login expired" and not as an empty roster.
- **A-03** As a manager, I want to see which leagues and teams my account has, so I can pick the one to operate on.
- **A-04** As a manager, I want my league and team pinned in config, so nothing can act on a team that isn't mine.
- **A-05** As a manager, I want the tool to record the date I supplied my cookies and tell me how old they are, since ESPN publishes no expiry it can read, so I refresh on my own schedule instead of mid-transaction.
- **A-06** As a manager, I want every league I play in configured at once, and to name the league on any call or switch the active league mid-session, so I can manage all of my teams without editing config between them.

## B. My Team

- **B-01** As a manager, I want my full roster — name, position, lineup slot, NFL team, opponent, projection — in one response, with starters and bench shown separately.
- **B-02** As a manager, I want each player's injury designation exactly as ESPN reports it, with the response stating plainly that no timestamp and no news text exist behind it, so I get "ESPN lists him QUESTIONABLE, no detail, no date" rather than an invented hamstring, and I know when I still have to read the news myself.
- **B-03** As a manager, I want a week-by-week bye grid for my roster through the rest of the season, showing for each week which starters are out and whether my remaining players can still fill every starting slot, so I can plan a trade or a stash weeks ahead instead of scrambling on Sunday.
- **B-05** As a manager, I want to be warned about empty or invalid starting slots.
- **B-06** As a manager, I want to know when my lineup locks and which players are already locked.
- **B-07** As a manager, I want my remaining acquisitions and — depending on which system my league runs — my remaining FAAB budget or my current waiver priority, each with one plain line saying what that number limits.
- **B-08** As a manager, I want my rostered players counted by position against my league's starting requirements and roster limits, with open roster spots and open IR slots shown, so I can see for myself where I have no backup.
- **B-09** As a manager, I want one pre-kickoff check across the leagues I name, listing every empty or illegal starting slot, every starter on bye, every starter ESPN lists as out, every starter whose game has already kicked off, and every slot already locked, so before kickoff I ask one question instead of twelve.

## C. Matchup & Scoring

- **C-01** As a manager, I want to know who I'm playing this week.
- **C-02** As a manager, I want projected scores for both sides.
- **C-03** As a manager, I want live scoring for both sides, showing which players have finished, are in progress, and have yet to play, and how many starters each of us has left, so I know whether the game is actually close.
- **C-04** As a manager, I want a position-by-position comparison against my opponent.
- **C-06** As a manager, I want to see every matchup in the league this week.
- **C-07** As a manager, I want my score history across the season.

## D. League Context

- **D-01** As a manager, I want the league's roster and scoring settings, so answers reflect my league's rules.
- **D-02** As a manager, I want the key dates and rules — trade deadline, waiver day and hour, minimum bid, acquisition limits, trade review window, playoff start week, number of playoff teams, and seeding tiebreakers — with every time given as a real date and time in my own time zone, named, rather than as a settings field.
- **D-03** As a manager, I want the standings with records and points for and against.
- **D-04** As a manager, I want to see the other teams and who manages them.
- **D-06** As a manager, I want the power rankings, labeled as espn-api's own two-step-dominance calculation rather than an ESPN ranking or a fantasy-yolo one.

## E. Player Research

- **E-01** As a manager, I want to look up any player and get status, stats, projection, and ownership.
- **E-02** As a manager, I want to know who owns a given player — me, another team, or nobody.
- **E-03** As a manager, I want to compare two players side by side.
- **E-04** As a manager, I want a player's recent game log, so I can judge form rather than season averages.
- **E-05** As a manager, I want a name I type resolved to a real player with team and position echoed back — two or more matches returned as a choice rather than a guess, no match returned as no match — and every write taking the resolved id rather than the name I typed, so I never act on the wrong person.
- **E-06** As a manager, I want players at a position ranked on a basis I name — season points, points per game, last three weeks, or this week's projection — over rostered players or available players as I choose, with the basis, window, and pool echoed back in the answer.

## F. Free Agency & Waivers

- **F-01** As a manager, I want available players at a position ranked on a basis I name — last week's points, season points, or this week's projection — reaching past the fifty ESPN returns by default, with each player's NFL opponent for this week or a window of weeks I name, and the basis and how many players were looked at stated in the answer.
- **F-02** As a manager, I want free agents ranked by change in percent rostered over the past week, or the answer to say plainly that ESPN does not expose that number, so "trending" means one defined thing rather than a re-sort of popularity.
- **F-03** As a manager, I want free agents at a named starter's position, excluding those on bye in the week I name, so I can pick the replacement myself.
- **F-04** As a manager, I want to add a free agent and drop someone to make room, as a single transaction.
- **F-05** As a manager, I want to submit a waiver claim with a FAAB bid, or without one in a waiver-priority league, so the claim is valid under whichever system my league runs.
- **F-06** As a manager, I want to see my pending waiver claims.
- **F-07** As a manager, I want to cancel a pending waiver claim.
- **F-08** As a manager, I want to drop a player outright, with a hard confirmation.
- **F-09** As a manager, I want every team's remaining FAAB and waiver position, not just my own, so I know what it will actually take to win a claim.
- **F-10** As a manager, I want the fate of my own claims after a waiver run — which won, which lost, and to what bid — so I can calibrate my next bid.
- **F-11** As a manager, I want to know whether an unrostered player is on waivers or a true free agent, and the date and hour he clears, so I know whether to add him now or bid on him.

## G. Trades

- **G-01** As a manager, I want to find which teams roster a given position, so I know who to talk to.
- **G-02** As a manager, I want to see a specific team's roster.
- **G-03** As a manager, I want every team's rostered counts by position in one table next to my own, so I can find a trade partner myself.
- **G-04** As a manager, I want a proposed trade laid out side by side — what I give, what I get, and both rosters after.
- **G-05** As a manager, I want to propose a trade to another team, with an optional message.
- **G-06** As a manager, I want to see trades proposed to me and trades I have outstanding.
- **G-07** As a manager, I want to accept or decline a trade offer.
- **G-08** As a manager, I want to cancel a trade I proposed.
- **G-09** As a manager, I want a proposed trade's roster and position counts shown before and after for both teams, with a note that ESPN decides legality at acceptance, so I am not told a trade is fine when the tool cannot know that.
- **G-10** As a manager, I want the state of an accepted trade — whether it is in review, when it processes, and whether it can still be vetoed — so I know which week I actually have the player.

## H. Roster Moves

- **H-01** As a manager, I want to set my starting lineup by naming the players I want starting, with slots optional, and have the preview lay out a legal arrangement — naming anyone who cannot fit — so the tool submits exactly the arrangement I confirmed and never one it chose on merit.
- **H-02** As a manager, I want to swap two players between starting and bench.
- **H-03** As a manager, I want to set a future week's lineup in advance.
- **H-04** As a manager, I want to move an eligible player to IR to free a roster spot.
- **H-06** As a manager, I want to activate a player off IR, and to be told first whether I have an open roster spot and who I would have to drop, so I never leave a healthy player parked on IR.

## I. History

- **I-01** As a manager, I want the league transaction log filtered by team, by transaction type, and by week, defaulting to the most recent page, so I can find one move without pulling the season.
- **I-02** As a manager, I want draft results.
- **I-03** As a manager, I want my head-to-head history against a given opponent.

## J. Safety

- **J-01** As a manager, I want every write split into two calls — a preview that shows what will happen in player names rather than ids, with the exact before and after, and hands back a short-lived single-use code bound to that exact transaction, and an execute that refuses to run without it — so a write is never a side effect of a question, an approval I gave for one add cannot be spent on another, and a retried execute is refused rather than double-submitted.
- **J-02** As a manager, I want a read-only mode that does not register the write tools at all and says so in the server description, so a model cannot offer me a move I have disabled.
- **J-03** As a manager, I want an append-only audit log of every write — what was intended, written before the request leaves, and what came back, written after — with reads logged by name and arguments only, and my espn_s2 and SWID redacted from every log line, error message, and tool response, so a write interrupted halfway leaves me something to reconcile against ESPN and my log is never a copy of my session cookie.
- **J-04** As a manager, I want the tool to never retry a write on its own, and a write whose outcome is unknown — timeout, dropped connection, unparseable response — reported to me as unknown rather than as success or failure, with my roster and pending transactions read back fresh so I can see for myself whether it landed, since ESPN offers no idempotency key and a retry genuinely submits the move a second time.
- **J-05** As a manager, I want the tool to refuse to act on any team but mine, and to never present itself as league manager.
- **J-06** As a manager, I want errors in plain language — roster full, slot limit, roster locked — not raw error codes.
- **J-07** As a manager, I want warning when I'm churning free agents, since cycling players through waivers can get you expelled.
- **J-08** As a manager, I want every read tool marked read-only and every write tool marked destructive in the MCP tool schema, so my client can prompt me before a model drops a player.
- **J-09** As a manager, I want my roster and pending transactions re-read immediately before any write is submitted, and the write aborted naming what changed if the state no longer matches what I approved, so a move I made on my phone is never silently clobbered.

## K. Legal & Compliance

- **K-01** As a software engineer, I want the project to state plainly that it is unofficial and not affiliated with, endorsed by, or sponsored by ESPN or Disney, and that it uses a private, undocumented API that may change or break without notice.
- **K-02** As a software engineer, I want the README to state what the project factually is — software running on the user's own machine, with credentials the user supplies, reading and writing only that user's own account, operating no service and redistributing nothing — alongside its stated purpose of research, study, and personal use, and a link to the terms that govern this activity, so its posture rests on what it does and not only on what it declares.
- **K-05** As a software engineer, I want the program to work only with credentials the user supplies for their own account, and to ship none.
- **K-06** As a software engineer, I want the project to ship no telemetry and open no network connection other than to ESPN, and to state plainly that everything the server returns is handed to whatever MCP client and model the user has configured — which may be a hosted service — so nobody mistakes "runs locally" for "stays local".
- **K-09** As a software engineer, I want no scraped or redistributed ESPN data committed to the repo.
- **K-10** As a manager, I want a plain-language statement of what I am risking — that ESPN's terms restrict unofficial access and that ESPN can suspend or terminate my account and my league, and that neither this project nor its author can restore anything they take — so my consent rests on more than a link I did not open.

## L. Licensing

- **L-01** As a software engineer, I want a permissive license (MIT) covering this project's own code, stated to grant no rights to ESPN's data, marks, or API and no permission from ESPN, so anyone can use, modify and redistribute the code without friction and nobody reads "MIT" as licence to build a service on this.
- **L-02** As a software engineer, I want every dependency to be permissively licensed, so downstream users inherit no copyleft obligations.
- **L-04** As a software engineer, I want clear attribution for any code or API knowledge derived from other projects.

## M. Engineering & Operations

- **M-01** As a software engineer, I want to install and run the MCP server in one command.
- **M-02** As a software engineer, I want it to work with any MCP client over stdio, with minimal configuration.
- **M-03** As a software engineer, I want the full test suite to run without live credentials or network access.
- **M-04** As a software engineer, I want read shapes validated against live ESPN and write payloads validated only against recorded fixtures and a schema, with a documented manual write canary run before each release, and no flag, code path, or tool name that implies a dry run ESPN does not offer.
- **M-06** As a software engineer, I want CI running tests and lint on every push.
- **M-07** As a software engineer, I want pinned dependencies and a reproducible environment.
- **M-08** As a software engineer, I want the read layer and the write layer independent, so the write client can be reused on its own.
- **M-09** As a software engineer, I want credentials read from a file path or secret-store reference named in the MCP client config, never as a literal value inside it, so a user's session cookie is not sitting in the JSON file they will paste into a GitHub issue the first time the server won't start.
- **M-10** As a software engineer, I want clear errors when ESPN changes its API, rather than silent wrong answers.
- **M-11** As a software engineer, I want a changelog and semantic versioning.
- **M-12** As a software engineer, I want a contributing guide, so others can add to this.
- **M-13** As a software engineer, I want every week-sensitive tool to take an optional week, to default to ESPN's current scoring period, and to echo back the season, the week it actually resolved, and when the data was fetched, so "this week" can never quietly mean a different week to the tool than it does to me.
- **M-14** As a software engineer, I want every tool to return a short, explicitly listed set of flat fields plus a one-line human summary, with every list taking a limit and offset, defaulting small, and reporting how many exist alongside how many came back, so one roster costs a few hundred tokens rather than the whole ESPN player object.
- **M-15** As a software engineer, I want the server's own instructions to state what it does not know — no projections beyond ESPN's own number, no injury news, no timestamps, no news feed — so a model driving it is told once, up front, what it must not infer.
- **M-16** As a software engineer, I want a documented request ceiling in config, one write in flight at a time, and backoff-and-retry on 429 and 5xx for reads only, so the program is a good API citizen without ever retrying a transaction.
- **M-17** As a software engineer, I want CI to fail on any dependency whose license is not on an explicit allowlist, treating missing or ambiguous metadata as a failure clearable only by a recorded, dated manual exception, so a copyleft dependency can't slip in behind blank metadata.
- **M-18** As a software engineer, I want every tool exposed as both an MCP tool and a CLI command from one definition, so I can exercise the whole program from a terminal without an MCP client, and the two interfaces cannot drift apart.

## Out of Scope

- **X-01** Automated decision-making. No optimizer, no projections model. The human decides. Local record-keeping — cookie capture date, waiver outcomes, a write-ahead log — is not automation.
- **X-02** Autonomous scheduled operation.
- **X-03** Live draft.
- **X-04** League-manager operations — settings changes, editing other teams, forcing transactions.
- **X-05** Multi-account operation, and acting on any team that is not the authenticated user's own.
- **X-06** Credential acquisition. The tool never logs into ESPN, drives a browser, or refreshes cookies. The human supplies espn_s2 and SWID.
