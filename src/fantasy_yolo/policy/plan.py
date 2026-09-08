"""Turning "start these players" into a legal lineup arrangement (H-01).

This is the boundary against X-01, and it is easy to cross here by accident.
Assigning named players to eligible slots is constraint satisfaction over the
league's own rules. Deciding WHICH players are worth starting is the user's job,
and nothing in this module may consult a projection.

The tiebreak rule, which is what keeps this on the right side of the line:

    Where several legal arrangements exist, players are placed in the order the
    user named them, each into the LOWEST-numbered eligible starting slot with
    room. Never by projection, and never by any other measure of quality.
"""

from __future__ import annotations

from espn_api.football.constant import POSITION_MAP

from fantasy_yolo.models import PlayerView

# espn-api's POSITION_MAP is bidirectional but its label->id half is INCOMPLETE:
# it has no BE and no IR, and it maps 23 to "FLEX" while the id->label half emits
# "RB/WR/TE". Player.lineupSlot is produced from the id->label half, so looking a
# slot label back up in the reverse half silently returns None for bench, IR and
# flex — which would drop exactly the moves a lineup change is made of.
# Invert the id->label half, which is authoritative, and keep the extra aliases.
SLOT_IDS: dict[str, int] = {
    label: slot
    for slot, label in POSITION_MAP.items()
    if isinstance(slot, int) and isinstance(label, str) and label
}
SLOT_IDS.update(
    {label: slot for label, slot in POSITION_MAP.items() if isinstance(label, str)}
)

BENCH_SLOT = 20
IR_SLOT = 21
BENCH_LIKE = {BENCH_SLOT, IR_SLOT}

Move = tuple[int, int, int]
"""(player_id, from_slot_id, to_slot_id)"""


class CannotFit(ValueError):
    pass


def slot_id(label: str) -> int | None:
    return SLOT_IDS.get(label)


def _eligible_ids(player: PlayerView) -> set[int]:
    ids = {slot_id(label) for label in player.eligible_slots}
    return {i for i in ids if i is not None}


def _resolve(name: str, roster: list[PlayerView]) -> PlayerView:
    wanted = name.strip().lower()
    exact = [p for p in roster if p.name.lower() == wanted]
    if len(exact) == 1:
        return exact[0]
    pool = exact or [p for p in roster if wanted in p.name.lower()]
    if not pool:
        raise CannotFit(f"{name!r} is not on your roster")
    if len(pool) > 1:
        raise CannotFit(
            f"{name!r} matches several players — say which: "
            + ", ".join(p.name for p in pool[:10])
        )
    return pool[0]


def plan_lineup(
    roster: list[PlayerView],
    start: list[str],
    slot_counts: dict[int, int],
) -> tuple[list[Move], list[str]]:
    """Work out the moves that put exactly `start` in the starting lineup.

    Returns the moves to make and the names of anyone who could not be placed.
    Players not named are benched.
    """
    capacity = {s: n for s, n in slot_counts.items() if s not in BENCH_LIKE and n > 0}
    wanted = [_resolve(name, roster) for name in start]

    assigned: dict[int, int] = {}
    unplaced: list[str] = []
    remaining = dict(capacity)

    for player in wanted:
        eligible = sorted(_eligible_ids(player) & remaining.keys())
        placed = next((s for s in eligible if remaining[s] > 0), None)
        if placed is None:
            unplaced.append(player.name)
            continue
        remaining[placed] -= 1
        assigned[player.player_id] = placed

    moves: list[Move] = []
    for player in roster:
        current = slot_id(player.slot)
        if current is None:
            continue
        target = assigned.get(player.player_id, BENCH_SLOT)
        if current != target:
            moves.append((player.player_id, current, target))
    return moves, unplaced
