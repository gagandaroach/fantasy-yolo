"""Preview-to-execute tokens (J-01).

Every write is split into two calls. The preview hands back a short-lived,
single-use code bound to a fingerprint of the exact transaction; execute refuses
to run without it.

What this guarantees: a write is never a side effect of a question, an approval
given for one transaction cannot be spent on another, and a retried execute is
refused rather than double-submitted.

What it does NOT guarantee: that a human read the preview. In an MCP server the
reader of a preview is a model, which can call preview and execute in the same
turn. The human-in-the-loop guarantee lives in the client's approval prompt on a
destructively-annotated tool (J-08). Do not oversell this.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from pathlib import Path
from typing import Any

TOKEN_BYTES = 4
DEFAULT_TTL = 600


class UnknownToken(LookupError):
    pass


class ExpiredToken(LookupError):
    pass


class TokenMismatch(ValueError):
    pass


def payload_fingerprint(payload: dict[str, Any]) -> str:
    """Stable across key order, sensitive to every value."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


class TokenStore:
    """File-backed, so the CLI can preview in one process and execute in another.

    Only fingerprints are persisted — never the payload, so this file is not a
    record of what you were about to do to your roster.
    """

    def __init__(self, path: Path, ttl_seconds: int = DEFAULT_TTL) -> None:
        self.path = path
        self.ttl = ttl_seconds

    def _read(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _write(self, data: dict[str, dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2))
        self.path.chmod(0o600)

    def issue(self, payload: dict[str, Any]) -> str:
        token = secrets.token_hex(TOKEN_BYTES)
        data = self._read()
        data[token] = {"fingerprint": payload_fingerprint(payload), "issued_at": time.time()}
        self._write(data)
        return token

    def consume(self, token: str, payload: dict[str, Any]) -> None:
        """Spend a token. Raises unless it matches this exact payload and is live."""
        data = self._read()
        entry = data.get(token)
        if entry is None:
            raise UnknownToken(
                f"confirmation code {token!r} is not recognised — run the preview again"
            )
        del data[token]
        self._write(data)

        if time.time() - entry["issued_at"] > self.ttl:
            raise ExpiredToken(
                f"confirmation code {token!r} has expired — run the preview again"
            )
        if entry["fingerprint"] != payload_fingerprint(payload):
            raise TokenMismatch(
                f"confirmation code {token!r} was issued for a different transaction — "
                "run the preview again for the change you actually want"
            )
