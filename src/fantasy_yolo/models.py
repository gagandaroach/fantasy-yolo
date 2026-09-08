"""Response contract (M-13, M-14).

A small, explicitly listed set of flat fields plus a one-line human summary.
Never a serialized espn-api object: Player carries a nested per-week stats dict,
so a naive roster dump is tens of kilobytes.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Provenance(BaseModel):
    """So "this week" can never mean two different weeks to the tool and the user (M-13)."""

    season: int
    week_resolved: int
    fetched_at: datetime
    from_cache: bool = False


class Response(BaseModel):
    summary: str
    provenance: Provenance


class Page(Response):
    """Truncation is stated, never silent (M-14)."""

    total: int
    returned: int
    offset: int

    @property
    def truncated(self) -> bool:
        return self.offset + self.returned < self.total


class PlayerView(BaseModel):
    player_id: int
    name: str
    position: str
    slot: str
    pro_team: str
    opponent: str
    projected: float
    injury_status: str


class RosterView(Response):
    starters: list[PlayerView]
    bench: list[PlayerView]
    counts_by_position: dict[str, int]
    open_roster_spots: int
