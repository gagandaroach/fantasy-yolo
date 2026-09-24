# Contributing

Issues and pull requests are welcome.

## Before you start

- **Read [docs/design.md](docs/design.md).** Most "why doesn't it just…"
  questions are answered there, especially around writes.
- **No optimizer, no recommendations.** The tool answers questions and executes
  instructions; the human decides. A PR that ranks players on merit or picks a
  lineup will be declined — see [Why no optimizer](README.md#why-no-optimizer).
- **Never include real credentials** in code, tests, fixtures, issues or logs.
  See [SECURITY.md](SECURITY.md).

## Development

```bash
uv sync
uv run pytest            # offline; no credentials, no network
uv run ruff check .
uv run ruff format src tests
```

Tests that talk to ESPN are opt-in with `-m network`, and are unauthenticated
and side-effect free.

`src/fantasy_yolo/espn/` is vendored from
[espn-api](https://github.com/cwendt94/espn-api) and kept close to upstream.
Mark any change to it with a `fantasy-yolo:` comment.

## Writes

ESPN has no dry run and no idempotency key, so a bug in a write path is a real
move on someone's real team. Changes to `write/`, `policy/` or the
`preview_*`/`execute_*` tools need a test that fails without the change, and a
note in the PR on how you verified it — a payload checked against ESPN's parser
(see the canary) at minimum.
