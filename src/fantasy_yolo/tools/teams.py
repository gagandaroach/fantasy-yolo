"""Other teams: rosters, positional shape, and waiver spending power.

G-03 is a table of counts. It does not say who is weak or strong — that is the
judgment the user is here to make (X-01).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import BaseModel

from fantasy_yolo.context import get_client
from fantasy_yolo.models import Page, PlayerView, Response
from fantasy_yolo.read.weeks import provenance, resolve_week
from fantasy_yolo.registry import Kind, tool
from fantasy_yolo.tools.league import WaiverSystem, detect_waiver_system
from fantasy_yolo.tools.team import to_player_view


class BudgetRow(BaseModel):
    team: str
    faab_remaining: int | None
    waiver_rank: int | None
    acquisitions: int


class OwnedPlayer(BaseModel):
    team: str
    player: PlayerView


class AllRosters(Page):
    rows: list[OwnedPlayer]


class TeamRoster(Response):
    team: str
    players: list[PlayerView]
    counts_by_position: dict[str, int]


class PositionTable(Response):
    counts: dict[str, dict[str, int]]
    """team name -> position -> count"""


class Budgets(Response):
    system: WaiverSystem
    rows: list[BudgetRow]


def position_counts(players: list[PlayerView]) -> dict[str, int]:
    return dict(Counter(p.position for p in players))


def build_all_rosters(
    by_team: dict[str, list[PlayerView]],
    positions: list[str] | None = None,
) -> list[OwnedPlayer]:
    wanted = {p.upper() for p in positions} if positions else None
    return [
        OwnedPlayer(team=team, player=player)
        for team, players in by_team.items()
        for player in players
        if wanted is None or player.position.upper() in wanted
    ]


def resolve_team(query: str, teams: list[Any]) -> Any:
    wanted = query.strip().lower()
    exact = [t for t in teams if t.team_name.strip().lower() == wanted]
    if len(exact) == 1:
        return exact[0]
    pool = exact or [t for t in teams if wanted in t.team_name.lower()]
    if not pool:
        raise LookupError(f"no team matching {query!r}")
    if len(pool) > 1:
        raise LookupError(
            f"{query!r} matches several teams — say which: "
            + "; ".join(t.team_name for t in pool[:10])
        )
    return pool[0]


def build_budget_rows(teams: list[Any], total_budget: int, faab: bool) -> list[BudgetRow]:
    """F-09. My own balance decides nothing; the bid is decided by who can outbid me."""
    rows = [
        BudgetRow(
            team=t.team_name,
            faab_remaining=(total_budget - int(t.acquisition_budget_spent or 0)) if faab else None,
            waiver_rank=None if faab else t.waiver_rank,
            acquisitions=int(t.acquisitions or 0),
        )
        for t in teams
    ]
    if faab:
        return sorted(rows, key=lambda r: -(r.faab_remaining or 0))
    return sorted(rows, key=lambda r: (r.waiver_rank or 999))


@tool(kind=Kind.READ)
def get_team(team: str, week: int | None = None, league: str | None = None) -> TeamRoster:
    """Another team's roster, so you can look for a trade fit."""
    client = get_client(league)
    resolved = resolve_week(week, client.latest_scoring_period())
    found = resolve_team(team, client.league.teams)
    players = [to_player_view(p, resolved) for p in found.roster]
    return TeamRoster(
        summary=f"{found.team_name}: {len(players)} players",
        provenance=provenance(client.cfg.year, resolved),
        team=found.team_name,
        players=players,
        counts_by_position=position_counts(players),
    )


@tool(kind=Kind.READ)
def get_position_counts(week: int | None = None, league: str | None = None) -> PositionTable:
    """Every team's rostered players counted by position, in one table.

    Read it yourself to find a trade partner. It renders no opinion about which
    teams are weak or strong.
    """
    client = get_client(league)
    resolved = resolve_week(week, client.latest_scoring_period())
    counts = {
        t.team_name: position_counts([to_player_view(p, resolved) for p in t.roster])
        for t in client.league.teams
    }
    return PositionTable(
        summary=f"positional counts for {len(counts)} teams",
        provenance=provenance(client.cfg.year, resolved),
        counts=counts,
    )


@tool(kind=Kind.READ)
def get_budgets(week: int | None = None, league: str | None = None) -> Budgets:
    """What every team can still spend on waivers, not just you.

    FAAB remaining in a FAAB league, waiver priority in a rolling-priority
    league, plus acquisitions used.
    """
    client = get_client(league)
    resolved = resolve_week(week, client.latest_scoring_period())
    raw, _ = client.raw(["mSettings"])
    acquisition = raw.get("settings", {}).get("acquisitionSettings", {})
    system = detect_waiver_system(acquisition)
    total = int(acquisition.get("acquisitionBudget") or 0)
    rows = build_budget_rows(client.league.teams, total, system is WaiverSystem.FAAB)
    return Budgets(
        summary=f"{system.value} waivers across {len(rows)} teams",
        provenance=provenance(client.cfg.year, resolved),
        system=system,
        rows=rows,
    )


@tool(kind=Kind.READ)
def get_all_rosters(
    positions: list[str] | None = None,
    limit: int = 250,
    offset: int = 0,
    week: int | None = None,
    league: str | None = None,
) -> AllRosters:
    """Every team's roster in one call, for trade shopping.

    Filter by position to keep the answer small — a 14-team league is roughly
    240 players, which is a lot to read at once. Says how many exist alongside
    how many came back.
    """
    client = get_client(league)
    resolved = resolve_week(week, client.latest_scoring_period())
    by_team = {
        t.team_name: [to_player_view(p, resolved) for p in t.roster]
        for t in client.league.teams
    }
    rows = build_all_rosters(by_team, positions)
    window = rows[offset : offset + limit]
    return AllRosters(
        summary=(
            f"{len(window)} of {len(rows)} rostered players across "
            f"{len(by_team)} teams"
            + (f" ({', '.join(positions)})" if positions else "")
        ),
        provenance=provenance(client.cfg.year, resolved),
        total=len(rows),
        returned=len(window),
        offset=offset,
        rows=window,
    )
