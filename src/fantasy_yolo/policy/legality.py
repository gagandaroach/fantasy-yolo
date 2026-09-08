"""Client-side legality checks (design §7.2).

ESPN provides no dry run and validates at execution, so every constraint that
can be known from the league's own settings is checked before the POST.

What cannot be known is stated rather than guessed. ESPN decides some things at
execution time that we cannot see, and a false clean bill of health is worse
than no check at all — the user submits the transaction *because* the tool said
it was fine.
"""

from __future__ import annotations

from fantasy_yolo.models import PlayerView
from fantasy_yolo.tools.league import WaiverSystem

BENCH_LIKE = {20, 21}


def roster_capacity(slot_counts: dict[int, int]) -> int:
    return sum(slot_counts.values())


def check_add_drop(
    roster: list[PlayerView],
    slot_counts: dict[int, int],
    adding: PlayerView | None,
    dropping: PlayerView | None,
) -> list[str]:
    """Problems with an add, a drop, or both. Empty means nothing we can see."""
    problems: list[str] = []
    if adding is None and dropping is None:
        return ["nothing to do: name a player to add, a player to drop, or both"]

    rostered = {p.player_id for p in roster}

    if adding is not None and adding.player_id in rostered:
        problems.append(f"{adding.name} is already on your roster")

    if dropping is not None and dropping.player_id not in rostered:
        problems.append(f"{dropping.name} is not on your roster")

    if adding is not None:
        after = len(roster) + 1 - (1 if dropping is not None else 0)
        capacity = roster_capacity(slot_counts)
        if after > capacity:
            problems.append(
                f"your roster is full ({len(roster)} of {capacity}) — "
                "drop someone in the same transaction"
            )
    return problems


def check_bid(
    system: WaiverSystem,
    bid: int | None,
    remaining: int,
    minimum: int,
) -> list[str]:
    """Whether a bid is coherent for this league's waiver system.

    A bid in a rolling-priority league is a malformed transaction, and on a
    platform with no dry run and no undo that costs a real move.
    """
    problems: list[str] = []
    if system is WaiverSystem.PRIORITY:
        if bid is not None:
            problems.append(
                "this league runs rolling waiver priority, not FAAB — a bid is not valid here"
            )
        return problems

    if bid is None:
        problems.append("this league uses FAAB — give a bid amount")
        return problems
    if bid < 0:
        problems.append(f"a bid cannot be negative (got {bid})")
        return problems
    if bid > remaining:
        problems.append(f"bid of {bid} is more than your remaining budget of {remaining}")
    if bid < minimum:
        problems.append(f"bid of {bid} is below your league's minimum of {minimum}")
    return problems
