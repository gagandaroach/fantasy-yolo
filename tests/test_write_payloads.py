"""Payload construction. ESPN deserializes strictly — an unknown key 400s — and
there is no dry run, so these are the tests that stand between a typo and a real
transaction."""

import pytest

from fantasy_yolo.write.payloads import (
    BENCH,
    EnvelopeType,
    ItemType,
    build_add_drop,
    build_envelope,
    build_item,
    build_lineup_moves,
    build_waiver_claim,
)

MEMBER = "{ABC-123}"


def test_item_always_carries_the_player_id():
    assert build_item(player_id=7) == {"playerId": 7}


def test_item_uses_the_wire_slot_names_not_the_internal_ones():
    """ESPN's own client calls these fromSlotId/toSlotId internally and renames
    them on the way out. Sending the internal names 400s."""
    item = build_item(player_id=7, from_slot=BENCH, to_slot=2)
    assert "fromLineupSlotId" in item and "toLineupSlotId" in item
    assert "fromSlotId" not in item and "toSlotId" not in item


def test_slot_zero_is_emitted_because_qb_is_slot_zero():
    """A falsy-but-real slot id must survive. QB is 0."""
    assert build_item(player_id=7, from_slot=BENCH, to_slot=0)["toLineupSlotId"] == 0


def test_falsy_team_ids_are_omitted_like_espns_own_builder():
    assert "fromTeamId" not in build_item(player_id=7, from_team_id=0)


def test_real_team_ids_are_kept():
    assert build_item(player_id=7, to_team_id=13)["toTeamId"] == 13


def test_envelope_never_claims_league_manager():
    """J-05. ESPN runs different server-side validation in LM mode."""
    env = build_envelope(EnvelopeType.ROSTER, team_id=8, member_id=MEMBER, items=[])
    assert env["isLeagueManager"] is False
    assert env["isActingAsTeamOwner"] is False


def test_envelope_defaults_to_execute():
    env = build_envelope(EnvelopeType.ROSTER, team_id=8, member_id=MEMBER, items=[])
    assert env["executionType"] == "EXECUTE"


def test_envelope_omits_unset_optional_keys():
    """Strict deserialization: any unknown or null key is a 400."""
    env = build_envelope(EnvelopeType.ROSTER, team_id=8, member_id=MEMBER, items=[])
    assert "bidAmount" not in env
    assert "relatedTransactionId" not in env
    assert None not in env.values()


def test_lineup_moves_use_roster_for_the_current_week():
    env = build_lineup_moves(
        team_id=8, member_id=MEMBER, moves=[(7, BENCH, 2)], scoring_period=3, latest_period=3
    )
    assert env["type"] == "ROSTER"


def test_lineup_moves_use_future_roster_for_a_later_week():
    """Every published implementation hardcodes ROSTER and gets this wrong."""
    env = build_lineup_moves(
        team_id=8, member_id=MEMBER, moves=[(7, BENCH, 2)], scoring_period=5, latest_period=3
    )
    assert env["type"] == "FUTURE_ROSTER"


def test_lineup_moves_batch_into_one_transaction():
    env = build_lineup_moves(
        team_id=8,
        member_id=MEMBER,
        moves=[(7, BENCH, 2), (9, 2, BENCH)],
        scoring_period=1,
        latest_period=1,
    )
    assert len(env["items"]) == 2
    assert all(i["type"] == ItemType.LINEUP for i in env["items"])


def test_lineup_moves_drop_no_op_swaps():
    """An all-no-op transaction 409s with "TransactionItems are missing"."""
    with pytest.raises(ValueError, match="no changes"):
        build_lineup_moves(
            team_id=8, member_id=MEMBER, moves=[(7, 2, 2)], scoring_period=1, latest_period=1
        )


def test_a_standalone_drop_uses_roster_not_freeagent():
    """The other place every published repo is wrong."""
    env = build_add_drop(team_id=8, member_id=MEMBER, add_player=None, drop_player=7)
    assert env["type"] == "ROSTER"
    assert env["items"][0]["type"] == ItemType.DROP


def test_an_add_uses_freeagent():
    env = build_add_drop(team_id=8, member_id=MEMBER, add_player=5, drop_player=None)
    assert env["type"] == "FREEAGENT"
    assert env["items"][0]["type"] == ItemType.ADD


def test_an_add_with_a_drop_orders_add_before_drop():
    env = build_add_drop(team_id=8, member_id=MEMBER, add_player=5, drop_player=7)
    assert [i["type"] for i in env["items"]] == [ItemType.ADD, ItemType.DROP]


def test_add_drop_with_neither_is_rejected():
    with pytest.raises(ValueError, match="nothing to do"):
        build_add_drop(team_id=8, member_id=MEMBER, add_player=None, drop_player=None)


def test_waiver_claim_puts_the_bid_on_the_envelope():
    env = build_waiver_claim(team_id=8, member_id=MEMBER, add_player=5, drop_player=None, bid=17)
    assert env["type"] == "WAIVER"
    assert env["bidAmount"] == 17


def test_waiver_claim_without_a_bid_omits_the_field():
    """A bid means nothing in a rolling-priority league, and a stray field 400s."""
    env = build_waiver_claim(team_id=8, member_id=MEMBER, add_player=5, drop_player=None, bid=None)
    assert "bidAmount" not in env


def test_a_zero_bid_is_kept_because_zero_is_a_legal_faab_bid():
    env = build_waiver_claim(team_id=8, member_id=MEMBER, add_player=5, drop_player=None, bid=0)
    assert env["bidAmount"] == 0


def test_negative_bids_are_rejected():
    with pytest.raises(ValueError, match="negative"):
        build_waiver_claim(team_id=8, member_id=MEMBER, add_player=5, drop_player=None, bid=-1)
