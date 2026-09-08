"""Resolves settings and credentials into a read client."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fantasy_yolo.config import DEFAULT_PATH, load_settings
from fantasy_yolo.creds import load_credentials
from fantasy_yolo.policy.audit import AuditLog
from fantasy_yolo.policy.tokens import TokenStore
from fantasy_yolo.read.client import ReadClient
from fantasy_yolo.write.client import WriteClient

STATE_DIR = DEFAULT_PATH.parent


class WritesDisabled(PermissionError):
    pass


@lru_cache(maxsize=8)
def get_client(league: str | None = None) -> ReadClient:
    """Session-scoped cache (design §10).

    Never to be used for live scoring or a post-write read-back — a cached score
    presented as live is a wrong answer.
    """
    settings = load_settings()
    if settings.credentials_file is None:
        raise FileNotFoundError("credentials_file is not set in config; see docs/setup.md")
    return ReadClient(settings.league(league), load_credentials(settings.credentials_file))


def _credentials(league: str | None = None):
    settings = load_settings()
    if settings.credentials_file is None:
        raise FileNotFoundError("credentials_file is not set in config; see docs/setup.md")
    return settings, load_credentials(settings.credentials_file)


def require_writes_enabled() -> None:
    """Defence in depth for J-02.

    Write tools are not registered at all when writes are off, so this should be
    unreachable through either frontend. It exists because "unreachable" is a
    claim about today's wiring, and this is the one place where being wrong costs
    a real transaction.
    """
    if not load_settings().write_enabled:
        raise WritesDisabled(
            "writes are disabled — set write_enabled: true in your config to turn them on"
        )


def get_write_client(league: str | None = None) -> WriteClient:
    require_writes_enabled()
    settings, creds = _credentials(league)
    cfg = settings.league(league)
    return WriteClient(year=cfg.year, league_id=cfg.league_id, cookies=creds.cookies())


def get_audit(league: str | None = None) -> AuditLog:
    try:
        _, creds = _credentials(league)
    except (FileNotFoundError, OSError):
        creds = None
    return AuditLog(Path(STATE_DIR) / "audit.jsonl", creds)


def get_tokens() -> TokenStore:
    return TokenStore(Path(STATE_DIR) / "pending-confirmations.json")
