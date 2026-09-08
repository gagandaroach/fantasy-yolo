"""The pre-kickoff check (B-09).

One question instead of twelve, five minutes before lock. Every element is a
read of state or the schedule — nothing here ranks players or recommends a move
(X-01). It tells you what is true; you decide what to do.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from fantasy_yolo.context import get_client
from fantasy_yolo.espn.football.constant import POSITION_MAP
from fantasy_yolo.models import PlayerView, Response
from fantasy_yolo.read.weeks import provenance, resolve_week
from fantasy_yolo.registry import Kind, tool
from fantasy_yolo.tools.team import BENCH_SLOTS, to_player_view

BENCH_SLOT_IDS = {20, 21}
OUT_STATUSES = {"OUT", "INJURY_RESERVE", "SUSPENSION", "DOUBTFUL"}


class Alert(BaseModel, frozen=True):
    kind: str
    detail: str


class LineupCheck(Response):
    alerts: list[Alert]
    starters_checked: int


def empty_starting_slots(
    players: list[PlayerView], slot_counts: dict[int, int]
) -> dict[str, int]:
    """Starting slots the league requires that nobody is filling (B-05).

    Counted against the league's own lineupSlotCounts, keyed by slot id.
    """
    filled = Counter(p.slot for p in players if p.slot not in BENCH_SLOTS)
    missing: dict[str, int] = {}
    for slot_id, required in slot_counts.items():
        if slot_id in BENCH_SLOT_IDS:
            continue
        label = POSITION_MAP.get(slot_id, str(slot_id))
        short = required - filled.get(label, 0)
        if short > 0:
            missing[label] = short
    return missing


def build_lineup_check(
    players: list[PlayerView],
    slot_counts: dict[int, int],
    kickoffs: dict[str, datetime],
    now: datetime,
) -> list[Alert]:
    """Every alert states a fact. None of them offer advice."""
    alerts: list[Alert] = []
    starters = [p for p in players if p.slot not in BENCH_SLOTS]

    for label, short in sorted(empty_starting_slots(players, slot_counts).items()):
        alerts.append(Alert(kind="empty_slot", detail=f"{short} empty {label} slot(s)"))

    for p in starters:
        if not p.opponent:
            alerts.append(
                Alert(kind="starter_on_bye", detail=f"{p.name} ({p.slot}) has no game this week")
            )
        if p.injury_status in OUT_STATUSES:
            alerts.append(
                Alert(
                    kind="starter_out",
                    detail=f"{p.name} ({p.slot}) is listed {p.injury_status} by ESPN",
                )
            )
        if p.projected == 0.0:
            alerts.append(
                Alert(
                    kind="projected_zero",
                    detail=f"{p.name} ({p.slot}) is projected 0.0 points by ESPN",
                )
            )
        kickoff = kickoffs.get(p.name)
        if kickoff is not None and kickoff <= now:
            alerts.append(
                Alert(kind="already_locked", detail=f"{p.name} ({p.slot}) has already kicked off")
            )
    return alerts


def _kickoffs(roster: list[Any], week: int) -> dict[str, datetime]:
    """Kickoff times from the pro schedule. Football's Player exposes no lock
    flags, so lock time is derived rather than read (design §4.1)."""
    times: dict[str, datetime] = {}
    for player in roster:
        schedule = getattr(player, "schedule", {}) or {}
        entry = schedule.get(str(week)) or schedule.get(week) or {}
        when = entry.get("date")
        if isinstance(when, datetime):
            times[player.name] = when.astimezone()
    return times


@tool(kind=Kind.READ)
def check_lineup(week: int | None = None, league: str | None = None) -> LineupCheck:
    """Everything blocking or time-critical about your lineup, in one call.

    Empty or illegal starting slots, starters on bye, starters ESPN lists as out,
    starters ESPN projects at zero, and starters whose game has already kicked
    off. It reports facts and recommends nothing.
    """
    client = get_client(league)
    resolved = resolve_week(week, client.latest_scoring_period())
    roster = client.my_team().roster
    players = [to_player_view(p, resolved) for p in roster]
    alerts = build_lineup_check(
        players,
        client.lineup_slot_counts(),
        _kickoffs(roster, resolved),
        datetime.now().astimezone(),
    )
    starters = [p for p in players if p.slot not in BENCH_SLOTS]
    return LineupCheck(
        summary=(
            f"{len(alerts)} thing(s) to look at across {len(starters)} starters"
            if alerts
            else f"nothing flagged across {len(starters)} starters"
        ),
        provenance=provenance(client.cfg.year, resolved),
        alerts=alerts,
        starters_checked=len(starters),
    )
