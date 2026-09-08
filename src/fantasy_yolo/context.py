"""Resolves settings and credentials into a read client."""

from __future__ import annotations

from functools import lru_cache

from fantasy_yolo.config import load_settings
from fantasy_yolo.creds import load_credentials
from fantasy_yolo.read.client import ReadClient


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
