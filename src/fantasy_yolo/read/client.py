"""Reads via espn-api, plus the raw fetches it does not parse (design §4.1)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import requests

from fantasy_yolo.config import LeagueConfig
from fantasy_yolo.creds import Credentials
from fantasy_yolo.espn.football import League

READ_HOST = "https://lm-api-reads.fantasy.espn.com"
WRITE_HOST = "lm-api-writes"


AUTH_STATUSES = (401, 403)


def auth_error_for(status: int, headers: Mapping[str, str]) -> str | None:
    """Explain an auth failure, or return None if this is not one (A-02).

    The signal is the STATUS CODE, not X-Fantasy-Role. Measured against the live
    league endpoint on 2026-09-08, that header is "NONE" on an authenticated 200
    just as it is on an unauthenticated 401, so it cannot distinguish them. It is
    kept in the message only as a diagnostic breadcrumb.
    """
    if status not in AUTH_STATUSES:
        return None
    role = headers.get("X-Fantasy-Role", "absent")
    return (
        "ESPN rejected your credentials (HTTP "
        f"{status}, X-Fantasy-Role: {role}). Your espn_s2 cookie has most likely "
        "expired, or the league id and team id do not belong to this account. "
        "Refresh the cookie and check the ids — see docs/setup.md."
    )


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
        problem = auth_error_for(response.status_code, response.headers)
        if problem is not None:
            raise PermissionError(problem)
        response.raise_for_status()
        return response.json(), response.headers

    def my_team(self) -> Any:
        """The pinned team. Never any other (A-04, J-05)."""
        for team in self.league.teams:
            if team.team_id == self.cfg.team_id:
                return team
        raise LookupError(f"team {self.cfg.team_id} is not in league {self.cfg.league_id}")

    def latest_scoring_period(self) -> int:
        """espn-api never parses league.status.latestScoringPeriod."""
        data, _ = self.raw(["mStatus"])
        return int(data["status"]["latestScoringPeriod"])

    def lineup_slot_counts(self) -> dict[int, int]:
        data, _ = self.raw(["mSettings"])
        return slot_counts_from_settings(data)
