"""Player research and search (E-01..E-06, F-01, F-03, F-11, G-01).

Ranking is always on a basis the caller names, echoed back in the answer. There
is no default that encodes an opinion about who is better (X-01).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from fantasy_yolo.context import get_client
from fantasy_yolo.models import Page, PlayerView, Response
from fantasy_yolo.read.weeks import provenance, resolve_week
from fantasy_yolo.registry import Kind, tool
from fantasy_yolo.tools.team import to_player_view

SORT_BASES = ("projected", "percent_owned", "name")
DEFAULT_LIMIT = 25
FREE_AGENT_SCAN = 300


class Pool(StrEnum):
    FREE_AGENTS = "free_agents"
    ROSTERED = "rostered"
    ALL = "all"


class PlayerNotFound(LookupError):
    pass


class AmbiguousPlayer(LookupError):
    pass


class Ownership(Response):
    player: PlayerView
    owned_by: str | None
    """Team name, or None when nobody rosters them."""


class PlayerSearch(Page):
    pool: Pool
    sorted_by: str
    players: list[PlayerView]


def resolve_one(query: str, candidates: list[PlayerView]) -> PlayerView:
    """Resolve a typed name to exactly one player (E-05).

    Two matches are returned as a choice, never a guess: a misresolved drop is
    permanently unrecoverable.
    """
    wanted = query.strip().lower()
    exact = [p for p in candidates if p.name.lower() == wanted]
    if len(exact) == 1:
        return exact[0]
    pool = exact or [p for p in candidates if wanted in p.name.lower()]
    if not pool:
        raise PlayerNotFound(f"no player matching {query!r}")
    if len(pool) > 1:
        options = "; ".join(f"{p.name} ({p.position}, {p.pro_team})" for p in pool[:10])
        raise AmbiguousPlayer(f"{query!r} matches several players — say which: {options}")
    return pool[0]


def _sort_key(basis: str):
    if basis == "name":
        return lambda p: (p.name.lower(),)
    if basis == "projected":
        # None is absence, not zero: it sorts last without outranking a real 0.0.
        return lambda p: (p.projected is None, -(p.projected or 0.0))
    return lambda p: (getattr(p, basis, None) is None, -(getattr(p, basis, 0.0) or 0.0))


def sort_players(players: list[PlayerView], basis: str) -> list[PlayerView]:
    if basis not in SORT_BASES:
        raise ValueError(f"sort basis must be one of {', '.join(SORT_BASES)}, got {basis!r}")
    return sorted(players, key=_sort_key(basis))


def _rostered(client: Any, week: int) -> list[tuple[str, PlayerView]]:
    return [
        (team.team_name, to_player_view(p, week))
        for team in client.league.teams
        for p in team.roster
    ]


@tool(kind=Kind.READ)
def find_players(
    position: str | None = None,
    pool: Pool = Pool.FREE_AGENTS,
    sort_by: str = "projected",
    limit: int = DEFAULT_LIMIT,
    week: int | None = None,
    league: str | None = None,
) -> PlayerSearch:
    """Search the player pool, ranked on a basis you name.

    pool is free_agents, rostered, or all. sort_by is projected, percent_owned or
    name. Reaches past the fifty ESPN returns by default, and states how many
    were examined.
    """
    client = get_client(league)
    resolved = resolve_week(week, client.latest_scoring_period())

    found: list[PlayerView] = []
    if pool in (Pool.FREE_AGENTS, Pool.ALL):
        agents = client.league.free_agents(week=resolved, size=FREE_AGENT_SCAN, position=position)
        found.extend(to_player_view(p, resolved) for p in agents)
    if pool in (Pool.ROSTERED, Pool.ALL):
        found.extend(
            view for _, view in _rostered(client, resolved)
            if position is None or view.position == position
        )
    if position is not None:
        found = [p for p in found if p.position == position]

    ranked = sort_players(found, sort_by)
    window = ranked[:limit]
    return PlayerSearch(
        summary=f"{len(window)} of {len(ranked)} {pool.value} sorted by {sort_by}",
        provenance=provenance(client.cfg.year, resolved),
        total=len(ranked),
        returned=len(window),
        offset=0,
        pool=pool,
        sorted_by=sort_by,
        players=window,
    )


@tool(kind=Kind.READ)
def get_player(name: str, week: int | None = None, league: str | None = None) -> Ownership:
    """Look up one player and find out who rosters them.

    Returns the player with team, position and ESPN's injury designation, plus
    the fantasy team that owns them or nothing if they are unowned. A name
    matching several players is returned as a choice rather than a guess.
    """
    client = get_client(league)
    resolved = resolve_week(week, client.latest_scoring_period())

    owners = _rostered(client, resolved)
    try:
        match = resolve_one(name, [view for _, view in owners])
        owner = next(team for team, view in owners if view.player_id == match.player_id)
        return Ownership(
            summary=f"{match.name} ({match.position}, {match.pro_team}) is rostered by {owner}",
            provenance=provenance(client.cfg.year, resolved),
            player=match,
            owned_by=owner,
        )
    except PlayerNotFound:
        pass

    agents = client.league.free_agents(week=resolved, size=FREE_AGENT_SCAN)
    match = resolve_one(name, [to_player_view(p, resolved) for p in agents])
    return Ownership(
        summary=f"{match.name} ({match.position}, {match.pro_team}) is not rostered by anyone",
        provenance=provenance(client.cfg.year, resolved),
        player=match,
        owned_by=None,
    )
