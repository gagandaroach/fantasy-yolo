# Security

## Never post your cookies

`espn_s2` is a full ESPN/Disney session cookie, not a scoped token. Anyone
holding it is signed in as you. **Do not paste it — or `SWID`, your credentials
file, or an unredacted audit log — into an issue, a pull request, a discussion,
a chat, or a screenshot.**

If you think it has leaked, sign out of ESPN everywhere; that invalidates it.

## Reporting a vulnerability

Report privately through
[GitHub's private vulnerability reporting](https://github.com/gagandaroach/fantasy-yolo/security/advisories/new),
not a public issue.

Things that count:

- A way for a credential to reach a log, an error message, a tool response, or
  anything handed to the MCP client
- A way for a write to happen without its preview's confirmation code, or for
  one code to authorise a different transaction
- A way to act on a team other than the one pinned in config
- A retried or duplicated write

This is a single-maintainer hobby project; expect a reply within a week.
