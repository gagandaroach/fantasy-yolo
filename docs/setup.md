# Setup

## 1. Get your ESPN cookies

ESPN has no API keys, no OAuth, and no developer program for fantasy. The only
way in is the two cookies your browser already has.

1. Sign in at [fantasy.espn.com](https://fantasy.espn.com) in a normal browser.
2. Open devtools (F12) → **Application** (Chrome) or **Storage** (Firefox) →
   **Cookies** → `https://fantasy.espn.com`.
3. Copy the values of **`espn_s2`** and **`SWID`**. `SWID` includes its curly
   braces — keep them.

> ### What you just copied
>
> **`espn_s2` is a full ESPN/Disney session cookie, not a scoped API key.**
> Anyone holding it is signed in as you — not just to fantasy. It is not
> restricted to this league, this sport, or reading.
>
> Never paste it into a chat, a GitHub issue, a screenshot, or a pastebin. If
> you think it has leaked, sign out of ESPN everywhere to invalidate it.

ESPN publishes no expiry that software can read, so this tool records *when you
supplied* the cookies and tells you how old they are (A-05). When they stop
working you will get a clear "your login expired" rather than an empty roster
(A-02).

## 2. Store them in a file

Credentials go in a file, never inline in your MCP client config — that JSON is
what people paste into bug reports (M-09).

```bash
mkdir -p ~/.config/fantasy-yolo
cat > ~/.config/fantasy-yolo/credentials.json <<'JSON'
{
  "espn_s2": "PASTE_YOURS_HERE",
  "swid": "{PASTE-YOURS-HERE}"
}
JSON
chmod 0600 ~/.config/fantasy-yolo/credentials.json
```

The tool refuses to load a group- or world-readable credentials file.

## 3. Find your league and team ids

Open your team in a browser. The URL looks like:

```
https://fantasy.espn.com/football/team?leagueId=123456&teamId=7
```

`leagueId` and `teamId` are what you need. Your team id is pinned in config so
nothing can act on anyone else's team (A-04, J-05).

## 4. Write the config

```bash
cat > ~/.config/fantasy-yolo/config.json <<'JSON'
{
  "leagues": [
    {"name": "office", "league_id": 123456, "team_id": 7, "year": 2026}
  ],
  "active": "office",
  "write_enabled": false,
  "credentials_file": "/home/YOU/.config/fantasy-yolo/credentials.json"
}
JSON
```

List every league you play in and switch with `--league` (A-06). `write_enabled`
stays `false` until you want write tools to exist at all — when it is false they
are not registered, so a model cannot see or offer them (J-02).

## 5. Check it works

```bash
uv run fy roster
uv run fy matchup
```

## 6. Point an MCP client at it

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

Note there are no credentials in this stanza. That is deliberate.
