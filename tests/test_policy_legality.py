"""Client-side legality (design §7.2).

ESPN offers no dry run and decides at execution, so everything checkable is
checked here first. What cannot be known is said plainly rather than guessed —
a false clean bill of health is worse than no check, because the user acts on it.
"""

import pytest

from fantasy_yolo.models import PlayerView
from fantasy_yolo.policy.legality import (
    WaiverSystem,
    check_add_drop,
    check_bid,
)

SLOTS = {0: 1, 2: 2, 4: 2, 20: 5}  # capacity 10


def _p(name, position="RB"):
    return PlayerView(
        player_id=abs(hash(name)) % 100000,
        name=name,
        position=position,
        slot="BE",
        pro_team="KC",
        opponent="LV",
        projected=1.0,
        eligible_slots=[position, "BE"],
        injury_status="ACTIVE",
    )


def _roster(n):
    return [_p(f"Player {i}") for i in range(n)]


def test_an_add_with_room_is_fine():
    assert check_add_drop(_roster(5), SLOTS, adding=_p("New"), dropping=None) == []


def test_an_add_onto_a_full_roster_is_refused():
    problems = check_add_drop(_roster(10), SLOTS, adding=_p("New"), dropping=None)
    assert any("full" in p.lower() for p in problems)


def test_an_add_with_a_paired_drop_fits_a_full_roster():
    roster = _roster(10)
    assert check_add_drop(roster, SLOTS, adding=_p("New"), dropping=roster[0]) == []


def test_dropping_someone_not_on_the_roster_is_refused():
    problems = check_add_drop(_roster(5), SLOTS, adding=None, dropping=_p("Stranger"))
    assert any("not on your roster" in p.lower() for p in problems)


def test_adding_someone_already_rostered_is_refused():
    roster = _roster(5)
    problems = check_add_drop(roster, SLOTS, adding=roster[0], dropping=None)
    assert any("already" in p.lower() for p in problems)


def test_doing_nothing_is_refused():
    problems = check_add_drop(_roster(5), SLOTS, adding=None, dropping=None)
    assert any("nothing" in p.lower() for p in problems)


def test_a_bid_within_budget_is_fine():
    assert check_bid(WaiverSystem.FAAB, bid=20, remaining=100, minimum=0) == []


def test_a_bid_over_budget_is_refused():
    problems = check_bid(WaiverSystem.FAAB, bid=120, remaining=100, minimum=0)
    assert any("budget" in p.lower() for p in problems)


def test_a_bid_below_the_league_minimum_is_refused():
    problems = check_bid(WaiverSystem.FAAB, bid=0, remaining=100, minimum=1)
    assert any("minimum" in p.lower() for p in problems)


def test_a_bid_in_a_priority_league_is_refused():
    """A bid field is a malformed transaction there, and it costs a real move."""
    problems = check_bid(WaiverSystem.PRIORITY, bid=5, remaining=0, minimum=0)
    assert any("priority" in p.lower() for p in problems)


def test_no_bid_in_a_faab_league_is_refused():
    problems = check_bid(WaiverSystem.FAAB, bid=None, remaining=100, minimum=0)
    assert any("faab" in p.lower() for p in problems)


def test_no_bid_in_a_priority_league_is_correct():
    assert check_bid(WaiverSystem.PRIORITY, bid=None, remaining=0, minimum=0) == []


@pytest.mark.parametrize("bid", [-1, -100])
def test_negative_bids_are_refused(bid):
    assert check_bid(WaiverSystem.FAAB, bid=bid, remaining=100, minimum=0) != []
