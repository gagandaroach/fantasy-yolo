"""The X-01 boundary. Assigning named players to eligible slots is constraint
satisfaction over the league's own rules. Ranking them is not this tool's job."""

import pytest

from fantasy_yolo.models import PlayerView
from fantasy_yolo.policy.plan import CannotFit, plan_lineup

BENCH, QB, RB, WR, TE, FLEX = 20, 0, 2, 4, 6, 23
SLOTS = {QB: 1, RB: 2, WR: 2, FLEX: 1, BENCH: 5}


def _p(name, position, slot="BE", eligible=None, pid=None):
    return PlayerView(
        player_id=pid if pid is not None else abs(hash(name)) % 100000,
        name=name,
        position=position,
        slot=slot,
        pro_team="KC",
        opponent="LV",
        projected=10.0,
        eligible_slots=eligible if eligible is not None else [position, "BE", "RB/WR/TE"],
        injury_status="ACTIVE",
    )


ROSTER = [
    _p("Quarter Back", "QB", eligible=["QB", "BE"]),
    _p("Runner One", "RB"),
    _p("Runner Two", "RB"),
    _p("Runner Three", "RB"),
    _p("Wide One", "WR"),
    _p("Wide Two", "WR"),
]


def test_named_players_are_assigned_to_their_natural_slots():
    moves, unplaced = plan_lineup(ROSTER, ["Quarter Back", "Runner One", "Wide One"], SLOTS)
    assert unplaced == []
    placed = {m[0]: m[2] for m in moves}
    assert placed[ROSTER[0].player_id] == QB


def test_the_overflow_runner_goes_to_flex_deterministically():
    """Three RBs, two RB slots and one flex: the third lands in flex, and which
    one is decided by the order named, never by projection."""
    moves, unplaced = plan_lineup(
        ROSTER, ["Runner One", "Runner Two", "Runner Three"], SLOTS
    )
    assert unplaced == []
    placed = {m[0]: m[2] for m in moves}
    assert placed[ROSTER[3].player_id] == FLEX


def test_assignment_is_stable_across_runs():
    first = plan_lineup(ROSTER, ["Runner One", "Runner Two", "Runner Three"], SLOTS)
    second = plan_lineup(ROSTER, ["Runner One", "Runner Two", "Runner Three"], SLOTS)
    assert first == second


def test_assignment_ignores_projection_entirely():
    """Same roster, reversed projections: the plan must not change."""
    flipped = [p.model_copy(update={"projected": 100.0 - p.projected}) for p in ROSTER]
    assert plan_lineup(ROSTER, ["Runner One", "Runner Two"], SLOTS) == plan_lineup(
        flipped, ["Runner One", "Runner Two"], SLOTS
    )


def test_a_player_who_cannot_fit_is_named_not_dropped():
    """H-01: the preview names anyone who cannot fit."""
    roster = ROSTER + [_p("Extra QB", "QB", eligible=["QB", "BE"])]
    _, unplaced = plan_lineup(roster, ["Quarter Back", "Extra QB"], SLOTS)
    assert unplaced == ["Extra QB"]


def test_players_not_named_are_benched():
    starting = [_p("Runner One", "RB", slot="RB")]
    moves, _ = plan_lineup(starting, [], SLOTS)
    assert moves == [(starting[0].player_id, RB, BENCH)]


def test_a_player_already_in_the_right_slot_produces_no_move():
    starting = [_p("Runner One", "RB", slot="RB")]
    moves, _ = plan_lineup(starting, ["Runner One"], SLOTS)
    assert moves == []


def test_an_unknown_name_is_an_error_not_a_silent_skip():
    with pytest.raises(CannotFit, match="Nobody"):
        plan_lineup(ROSTER, ["Nobody"], SLOTS)


def test_an_ambiguous_name_is_an_error():
    roster = [_p("Josh Allen", "QB"), _p("Josh Jacobs", "RB")]
    with pytest.raises(CannotFit, match="several"):
        plan_lineup(roster, ["Josh"], {QB: 1, RB: 1, BENCH: 5})


def test_bench_ir_and_flex_labels_all_resolve():
    """espn-api's own reverse map has none of these; getting a None here would
    silently drop the moves a lineup change is made of."""
    from fantasy_yolo.policy.plan import slot_id

    assert slot_id("BE") == 20
    assert slot_id("IR") == 21
    assert slot_id("RB/WR/TE") == 23
    assert slot_id("FLEX") == 23
    assert slot_id("QB") == 0
