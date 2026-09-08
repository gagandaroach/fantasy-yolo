"""Append-only audit log (J-03).

Writes are logged in two parts: intent BEFORE the request leaves, outcome AFTER
it returns. A process killed mid-write therefore leaves evidence of what was
attempted, which is what makes J-04's read-back reconcilable at all.

Reads are logged by name and arguments only. Logging read responses would store
full rosters and free-agent pools, burying the handful of entries that matter.

Credentials are redacted from every line. Every ESPN request carries the session
cookie in a Cookie header, so a naive "log the request" would write a permanent
plaintext copy of the user's credentials — the exact file someone attaches to a
GitHub issue when the server will not start.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fantasy_yolo.creds import Credentials, redact


class AuditLog:
    def __init__(self, path: Path, creds: Credentials | None = None) -> None:
        self.path = path
        self.creds = creds

    def _append(self, entry: dict[str, Any]) -> None:
        entry["at"] = datetime.now().astimezone().isoformat()
        line = redact(json.dumps(entry, default=str), self.creds)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as fh:
            fh.write(line + "\n")
        self.path.chmod(0o600)

    def read(self, tool: str, args: dict[str, Any]) -> None:
        self._append({"event": "read", "tool": tool, "args": args})

    def intent(self, tool: str, payload: dict[str, Any]) -> None:
        """Called before the request leaves. If the process dies here, this is
        the only record that anything was attempted."""
        self._append({"event": "intent", "tool": tool, "payload": payload})

    def outcome(self, tool: str, status: int, body: dict[str, Any]) -> None:
        self._append({"event": "outcome", "tool": tool, "status": status, "body": body})

    def unknown(self, tool: str, reason: str) -> None:
        """A write whose result we genuinely do not know (J-04)."""
        self._append({"event": "unknown", "tool": tool, "reason": reason})
