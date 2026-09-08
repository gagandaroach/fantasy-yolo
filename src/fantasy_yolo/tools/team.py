"""My-team reads.

Pure helpers are kept separate from the ESPN calls so they test without a
network (M-03).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from fantasy_yolo.context import get_client
from fantasy_yolo.models import PlayerView, Response, RosterView
from fantasy_yolo.read.weeks import provenance, resolve_week
from fantasy_yolo.registry import Kind, tool

BENCH_SLOTS = {"BE", "IR"}


class MatchupView(Response):
    opponent: str
    my_projected: float
    their_projected: float


def split_starters(players: list[PlayerView]) -> tuple[list[PlayerView], list[PlayerView]]:
    """B-01 shows starters and bench separately."""
    starters = [p for p in players if p.slot not in BENCH_SLOTS]
    bench = [p for p in players if p.slot in BENCH_SLOTS]
    return starters, bench


def build_roster_view(
    players: list[PlayerView],
    slot_counts: dict[int, int],
    season: int,
    week: int,
) -> RosterView:
    """B-01, B-08. Counts are arithmetic over the league's own settings, not judgment."""
    starters, bench = split_starters(players)
    counts = Counter(p.position for p in players)
    capacity = sum(slot_counts.values())
    return RosterView(
        summary=(
            f"{len(starters)} starters, {len(bench)} bench, "
            f"{capacity - len(players)} open of {capacity}"
        ),
        provenance=provenance(season, week),
        starters=starters,
        bench=bench,
        counts_by_position=dict(counts),
        open_roster_spots=capacity - len(players),
    )


def _stat(player: Any, week: int, key: str) -> float | None:
    """None when ESPN has no entry. A real 0.0 is kept — ESPN projects an unfit
    starter at zero, and that is data, not absence (M-15)."""
    stats = getattr(player, "stats", {}) or {}
    entry = stats.get(week)
    if entry is None:
        entry = stats.get(str(week))
    if not entry or key not in entry:
        return None
    value = entry[key]
    return None if value is None else float(value)


def _opponent(player: Any, week: int) -> str:
    """The NFL opponent, from whichever shape espn-api handed us.

    league.free_agents() returns BoxPlayer, which sets pro_opponent and leaves
    schedule empty; team rosters return Player, which is the other way round.
    Reading only schedule left every free agent with a blank opponent — exactly
    the field you need when streaming a kicker or defence.
    """
    if getattr(player, "on_bye_week", False):
        return ""

    opponent = getattr(player, "pro_opponent", None)
    if opponent and str(opponent).upper() not in ("BYE", "NONE"):
        return str(opponent)

    schedule = getattr(player, "schedule", {}) or {}
    entry = schedule.get(str(week)) or schedule.get(week) or {}
    return str(entry.get("team", "") or "")


def to_player_view(player: Any, week: int) -> PlayerView:
    return PlayerView(
        player_id=player.playerId,
        name=player.name,
        position=player.position,
        slot=player.lineupSlot,
        pro_team=player.proTeam,
        opponent=_opponent(player, week),
        projected=_stat(player, week, "projected_points"),
        eligible_slots=list(getattr(player, "eligibleSlots", []) or []),
        injury_status=getattr(player, "injuryStatus", None) or "UNKNOWN",
    )


@tool(kind=Kind.READ)
def get_roster(week: int | None = None, league: str | None = None) -> RosterView:
    """Your roster: lineup slots, NFL opponents, projections and injury designations.

    Injury designations are exactly what ESPN reports. There is no timestamp and
    no news text behind them, so do not describe how recent one is (B-02).
    """
    client = get_client(league)
    resolved = resolve_week(week, client.latest_scoring_period())
    team = client.my_team()
    players = [to_player_view(p, resolved) for p in team.roster]
    return build_roster_view(players, client.lineup_slot_counts(), client.cfg.year, resolved)


@tool(kind=Kind.READ)
def get_matchup(week: int | None = None, league: str | None = None) -> MatchupView:
    """Who you are playing this week, and the projected score for both sides."""
    client = get_client(league)
    resolved = resolve_week(week, client.latest_scoring_period())
    mine = client.cfg.team_id
    for box in client.league.box_scores(resolved):
        if box.home_team.team_id == mine:
            my_points, their_points = box.home_projected, box.away_projected
            opponent = box.away_team.team_name
            break
        if box.away_team.team_id == mine:
            my_points, their_points = box.away_projected, box.home_projected
            opponent = box.home_team.team_name
            break
    else:
        raise LookupError(f"no matchup for team {mine} in week {resolved}")
    return MatchupView(
        summary=f"vs {opponent}: {my_points:.1f} projected to {their_points:.1f}",
        provenance=provenance(client.cfg.year, resolved),
        opponent=opponent,
        my_projected=my_points,
        their_projected=their_points,
    )
