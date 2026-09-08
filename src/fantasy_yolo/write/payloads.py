"""ESPN transaction payloads.

Mirrored from ESPN's own client, not from any public repository — three of the
circulating shapes are provably wrong. This module imports nothing from the rest
of the package (M-08), so it can be extracted as a standalone write client.

Two platform facts govern everything here:
  * ESPN deserializes strictly. Any unknown or null key is a 400.
  * There is no dry run. Nothing built here can be rehearsed against ESPN.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

QB, RB, WR, TE = 0, 2, 4, 6
DST, K, FLEX = 16, 17, 23
BENCH, IR = 20, 21


class EnvelopeType(StrEnum):
    ROSTER = "ROSTER"
    FUTURE_ROSTER = "FUTURE_ROSTER"
    FREEAGENT = "FREEAGENT"
    WAIVER = "WAIVER"
    TRADE_PROPOSAL = "TRADE_PROPOSAL"
    TRADE_ACCEPT = "TRADE_ACCEPT"
    TRADE_DECLINE = "TRADE_DECLINE"


class ItemType(StrEnum):
    LINEUP = "LINEUP"
    ADD = "ADD"
    DROP = "DROP"
    TRADE = "TRADE"


class ExecutionType(StrEnum):
    EXECUTE = "EXECUTE"
    CANCEL = "CANCEL"


def build_item(
    player_id: int,
    type: ItemType | None = None,
    from_team_id: int | None = None,
    to_team_id: int | None = None,
    from_slot: int | None = None,
    to_slot: int | None = None,
) -> dict[str, Any]:
    """One transaction item, mirroring ESPN's own builder.

    Team ids are omitted when falsy, exactly as ESPN does. Slot ids are emitted
    whenever they are not None — QB is slot 0, so a falsy-but-real slot must
    survive.

    The wire names are fromLineupSlotId / toLineupSlotId. ESPN's client calls
    them fromSlotId / toSlotId internally and renames them on the way out;
    sending the internal names is a 400.
    """
    item: dict[str, Any] = {"playerId": player_id}
    if type is not None:
        item["type"] = str(type)
    if from_team_id:
        item["fromTeamId"] = from_team_id
    if to_team_id:
        item["toTeamId"] = to_team_id
    if from_slot is not None:
        item["fromLineupSlotId"] = from_slot
    if to_slot is not None:
        item["toLineupSlotId"] = to_slot
    return item


def build_envelope(
    type: EnvelopeType,
    team_id: int,
    member_id: str,
    items: list[dict[str, Any]],
    scoring_period: int | None = None,
    execution_type: ExecutionType = ExecutionType.EXECUTE,
    bid_amount: int | None = None,
    comment: str | None = None,
    related_transaction_id: str | None = None,
) -> dict[str, Any]:
    """The transaction envelope.

    isLeagueManager and isActingAsTeamOwner are hard-wired False and are not
    parameters (J-05). ESPN ships paired _LM variants of every roster-limit error
    constant, which is direct evidence it runs different server-side validation
    in that mode.
    """
    envelope: dict[str, Any] = {
        "type": str(type),
        "teamId": team_id,
        "memberId": member_id,
        "executionType": str(execution_type),
        "isLeagueManager": False,
        "isActingAsTeamOwner": False,
        "items": items,
    }
    if scoring_period is not None:
        envelope["scoringPeriodId"] = scoring_period
    if bid_amount is not None:
        envelope["bidAmount"] = bid_amount
    if comment is not None:
        envelope["comment"] = comment
    if related_transaction_id is not None:
        envelope["relatedTransactionId"] = related_transaction_id
    return envelope


def build_lineup_moves(
    team_id: int,
    member_id: str,
    moves: list[tuple[int, int, int]],
    scoring_period: int,
    latest_period: int,
) -> dict[str, Any]:
    """Lineup changes as one batched transaction.

    moves are (player_id, from_slot, to_slot). ESPN batches all moves into a
    single transaction and so do we — per-item posting makes partial-failure
    states more likely, not less, given there is no idempotency key.

    A future week uses FUTURE_ROSTER, not ROSTER. Every published implementation
    hardcodes ROSTER and sets the wrong week.
    """
    real = [m for m in moves if m[1] != m[2]]
    if not real:
        raise ValueError("no changes to make: every move is already in place")
    envelope_type = (
        EnvelopeType.FUTURE_ROSTER if scoring_period > latest_period else EnvelopeType.ROSTER
    )
    items = [
        build_item(player_id=pid, type=ItemType.LINEUP, from_slot=src, to_slot=dst)
        for pid, src, dst in real
    ]
    return build_envelope(
        envelope_type, team_id, member_id, items, scoring_period=scoring_period
    )


def _add_drop_items(
    team_id: int, add_player: int | None, drop_player: int | None
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if add_player is not None:
        items.append(build_item(player_id=add_player, type=ItemType.ADD, to_team_id=team_id))
    if drop_player is not None:
        items.append(build_item(player_id=drop_player, type=ItemType.DROP, from_team_id=team_id))
    return items


def build_add_drop(
    team_id: int,
    member_id: str,
    add_player: int | None,
    drop_player: int | None,
    scoring_period: int | None = None,
) -> dict[str, Any]:
    """Add a free agent, drop a player, or both as one transaction.

    An add uses FREEAGENT. A standalone drop uses ROSTER — not FREEAGENT, which
    is the second place every published repo is wrong.
    """
    if add_player is None and drop_player is None:
        raise ValueError("nothing to do: give a player to add, to drop, or both")
    envelope_type = EnvelopeType.FREEAGENT if add_player is not None else EnvelopeType.ROSTER
    return build_envelope(
        envelope_type,
        team_id,
        member_id,
        _add_drop_items(team_id, add_player, drop_player),
        scoring_period=scoring_period,
    )


def build_waiver_claim(
    team_id: int,
    member_id: str,
    add_player: int,
    drop_player: int | None,
    bid: int | None,
    scoring_period: int | None = None,
) -> dict[str, Any]:
    """A waiver claim, with a FAAB bid where the league uses one.

    bid is None in a rolling-priority league, where a bid field is a malformed
    transaction. Zero is a legal FAAB bid and is kept.
    """
    if bid is not None and bid < 0:
        raise ValueError(f"bid cannot be negative, got {bid}")
    return build_envelope(
        EnvelopeType.WAIVER,
        team_id,
        member_id,
        _add_drop_items(team_id, add_player, drop_player),
        scoring_period=scoring_period,
        bid_amount=bid,
    )
