"""Reads via espn-api, plus the raw fetches it does not parse (design §4.1)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import requests
from espn_api.football import League

from fantasy_yolo.config import LeagueConfig
from fantasy_yolo.creds import Credentials

READ_HOST = "https://lm-api-reads.fantasy.espn.com"
WRITE_HOST = "lm-api-writes"


def slot_counts_from_settings(raw: Mapping[str, Any]) -> dict[int, int]:
    """Raw lineupSlotCounts, keyed by slot id.

    Never use football's Settings.position_slot_counts: it positionally zips
    list(POSITION_MAP.values())[:n] against lineupSlotCounts.values(), so labels
    and counts silently misalign.
    """
    try:
        counts = raw["settings"]["rosterSettings"]["lineupSlotCounts"]
    except (KeyError, TypeError) as exc:
        raise KeyError(
            "no lineupSlotCounts in the mSettings response; ESPN may have changed shape"
        ) from exc
    return {int(slot): int(n) for slot, n in counts.items()}


class ReadClient:
    def __init__(self, cfg: LeagueConfig, creds: Credentials) -> None:
        self.cfg = cfg
        self.creds = creds
        self.league = League(
            league_id=cfg.league_id,
            year=cfg.year,
            espn_s2=creds.espn_s2,
            swid=creds.swid,
        )

    @staticmethod
    def assert_read_host(url: str) -> None:
        """Host choice is not a safety barrier, but this catches an obvious mistake."""
        if WRITE_HOST in url:
            raise ValueError(f"read client refuses the write host: {url}")

    @staticmethod
    def role_is_authenticated(headers: Mapping[str, str]) -> bool:
        """X-Fantasy-Role reads NONE when unauthenticated — a free liveness canary (A-02)."""
        return headers.get("X-Fantasy-Role", "NONE") != "NONE"

    def _endpoint(self) -> str:
        return (
            f"{READ_HOST}/apis/v3/games/ffl/seasons/{self.cfg.year}"
            f"/segments/0/leagues/{self.cfg.league_id}"
        )

    def raw(self, views: list[str]) -> tuple[dict[str, Any], Mapping[str, str]]:
        url = self._endpoint()
        self.assert_read_host(url)
        response = requests.get(
            url,
            params=[("view", v) for v in views],
            cookies=self.creds.cookies(),
            timeout=30,
        )
        if not self.role_is_authenticated(response.headers):
            raise PermissionError(
                "ESPN did not recognise your login (X-Fantasy-Role: NONE). "
                "Your espn_s2 cookie has expired — refresh it. See docs/setup.md."
            )
        response.raise_for_status()
        return response.json(), response.headers

    def latest_scoring_period(self) -> int:
        """espn-api never parses league.status.latestScoringPeriod."""
        data, _ = self.raw(["mStatus"])
        return int(data["status"]["latestScoringPeriod"])

    def lineup_slot_counts(self) -> dict[int, int]:
        data, _ = self.raw(["mSettings"])
        return slot_counts_from_settings(data)
