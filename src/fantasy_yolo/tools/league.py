"""League context: settings, rules, dates, standings, teams (D-01..D-06).

Dates are returned as real timestamps in the user's own zone rather than as
ESPN settings fields (D-02) — misreading a lock time is the specific failure
this tool exists to prevent.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from fantasy_yolo.context import get_client
from fantasy_yolo.models import Response
from fantasy_yolo.read.weeks import provenance, resolve_week
from fantasy_yolo.registry import Kind, tool


class WaiverSystem(StrEnum):
    FAAB = "faab"
    PRIORITY = "priority"


class StandingsRow(BaseModel):
    rank: int
    name: str
    wins: int
    losses: int
    points_for: float
    points_against: float


class LeagueView(Response):
    league_name: str
    team_count: int
    waiver_system: WaiverSystem
    acquisition_budget: int | None
    trade_deadline: datetime | None
    playoff_team_count: int | None
    regular_season_weeks: int | None
    lineup_slots: dict[str, int]
    standings: list[StandingsRow]


def detect_waiver_system(settings: dict[str, Any]) -> WaiverSystem:
    """FAAB or rolling priority.

    The write path branches on this: a bid field in a priority league is a
    malformed transaction, and on a platform with no dry run that costs a real
    move (F-05, B-07).

    Do NOT read acquisitionBudget to decide. ESPN carries a non-zero budget in
    rolling-priority leagues too — observed live: budget 100 alongside
    isUsingAcquisitionBudget false and acquisitionType WAIVERS_TRADITIONAL. The
    explicit flag is the answer; acquisitionType is the fallback; the budget is
    a last resort for leagues that report neither.
    """
    using_budget = settings.get("isUsingAcquisitionBudget")
    if isinstance(using_budget, bool):
        return WaiverSystem.FAAB if using_budget else WaiverSystem.PRIORITY

    acquisition_type = str(settings.get("acquisitionType") or "")
    if acquisition_type:
        return WaiverSystem.FAAB if "BUDGET" in acquisition_type.upper() else WaiverSystem.PRIORITY

    return WaiverSystem.FAAB if int(settings.get("acquisitionBudget") or 0) > 0 else (
        WaiverSystem.PRIORITY
    )


def epoch_ms_to_local(value: int | None) -> datetime | None:
    """ESPN returns epoch milliseconds; the naive path prints UTC or the
    container's zone. Zero means unset."""
    if not value:
        return None
    return datetime.fromtimestamp(int(value) / 1000.0).astimezone()


def build_standings(teams: list[dict[str, Any]]) -> list[StandingsRow]:
    """Ordered by wins, then points for. ESPN's own tiebreaker may differ; this
    is a presentation order, not a claim about seeding."""
    ordered = sorted(teams, key=lambda t: (-t["wins"], -t["points_for"]))
    return [
        StandingsRow(
            rank=i,
            name=t["name"],
            wins=t["wins"],
            losses=t["losses"],
            points_for=round(t["points_for"], 2),
            points_against=round(t["points_against"], 2),
        )
        for i, t in enumerate(ordered, start=1)
    ]


@tool(kind=Kind.READ)
def get_league(week: int | None = None, league: str | None = None) -> LeagueView:
    """Your league's rules, key dates and standings.

    Roster and scoring settings, whether waivers run on FAAB or rolling
    priority, the trade deadline as a real local timestamp, and the current
    standings.
    """
    client = get_client(league)
    resolved = resolve_week(week, client.latest_scoring_period())
    raw, _ = client.raw(["mSettings"])
    settings = raw.get("settings", {})
    acquisition = settings.get("acquisitionSettings", {})
    schedule = settings.get("scheduleSettings", {})
    trade = settings.get("tradeSettings", {})

    system = detect_waiver_system(acquisition)
    budget = int(acquisition.get("acquisitionBudget") or 0)

    from fantasy_yolo.espn.football.constant import POSITION_MAP

    slots = {
        POSITION_MAP.get(slot_id, str(slot_id)): count
        for slot_id, count in sorted(client.lineup_slot_counts().items())
        if count
    }

    rows = build_standings(
        [
            {
                "name": t.team_name,
                "wins": t.wins,
                "losses": t.losses,
                "points_for": float(t.points_for or 0.0),
                "points_against": float(t.points_against or 0.0),
            }
            for t in client.league.teams
        ]
    )

    return LeagueView(
        summary=(
            f"{client.league.settings.name}: {len(client.league.teams)} teams, "
            f"{system.value} waivers"
        ),
        provenance=provenance(client.cfg.year, resolved),
        league_name=client.league.settings.name,
        team_count=len(client.league.teams),
        waiver_system=system,
        acquisition_budget=budget if system is WaiverSystem.FAAB else None,
        trade_deadline=epoch_ms_to_local(trade.get("deadlineDate")),
        playoff_team_count=schedule.get("playoffTeamCount"),
        regular_season_weeks=schedule.get("matchupPeriodCount"),
        lineup_slots=slots,
        standings=rows,
    )
