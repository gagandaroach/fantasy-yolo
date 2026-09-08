# fantasy-yolo

A programmatic interface to your own ESPN Fantasy Football team — an MCP server
and a CLI, sharing one set of tools.

**The human is the brain.** This makes no roster decisions. It answers questions
about your league accurately and executes what you tell it, carefully. There is
no optimizer and no projections model.

```console
$ fy roster
$ fy matchup
```

The same tools are exposed over MCP, so an agent you already use can answer
"who am I playing this week" or "any injuries on my roster" against live data.

## Status

Early. Reads work; the write path is designed but not built. See
[docs/design.md](docs/design.md) and [docs/user-stories.md](docs/user-stories.md).

## Setup

See **[docs/setup.md](docs/setup.md)**. In short: copy two cookies out of your
browser, put them in a `chmod 0600` file, write a small config naming your
league and team.

## What you should know before using this

**This is unofficial.** It is not affiliated with, endorsed by, or sponsored by
ESPN or Disney. It drives a private, undocumented API that can change or break
without notice.

**It runs on your machine, with your credentials, on your own account.** It
operates no service and redistributes nothing.

**"Runs locally" is not "stays local."** Everything this server returns is
handed to whatever MCP client and model you have configured — which for most
people is a hosted service. The project ships no telemetry and opens no network
connection other than to ESPN, but that is not the same as your roster staying
on your machine.

**What you are risking.** ESPN's terms restrict unofficial automated access.
ESPN can suspend or terminate your account and your league, and neither this
project nor its author can restore anything they take. Read
[Disney's Terms of Use](https://disneytermsofuse.com/english/) and ESPN's
[Fair Play and Conduct](https://support.espn.com/hc/en-us/articles/115003845711-Fair-Play-and-Conduct)
rules and decide for yourself.

**`espn_s2` is a full session cookie, not a scoped token.** Leaking it is
account compromise. Never paste it into an issue or a chat.

## Licence

[MIT](LICENSE). Permissive: use it, change it, ship it, sell it. The only thing
it asks is that the copyright notice travels with the code.

It covers this project's own code. It grants no rights to ESPN's data, marks, or
API, and it is not permission from ESPN.

### Vendored code

`src/fantasy_yolo/espn/` is a vendored copy of the football half of
[`espn-api`](https://github.com/cwendt94/espn-api) by Christian Wendt, also MIT.
Upstream covers five sports; this copy keeps football and the shared client, and
`FANTASY_SPORTS` is trimmed to match so nothing can request a sport that has no
client behind it.
Its licence is preserved verbatim at [LICENSE-espn-api](LICENSE-espn-api), as
MIT requires when redistributing.

It is vendored rather than depended on so this project can fix defects in the
read path directly — the first being a `POSITION_MAP` that could not convert a
lineup slot label back to its id for bench, IR or flex, which made lineup writes
impossible. Our changes to it are marked `fantasy-yolo:` in comments, and its own
test suite runs in our CI.
