import pytest

from fantasy_yolo.models import PlayerView
from fantasy_yolo.tools.players import (
    AmbiguousPlayer,
    PlayerNotFound,
    Pool,
    resolve_one,
    sort_players,
)


def _p(name, projected=10.0, position="RB", pro_team="KC"):
    return PlayerView(
        player_id=abs(hash(name)) % 10000,
        name=name,
        position=position,
        slot="BE",
        pro_team=pro_team,
        opponent="LV",
        projected=projected,
        injury_status="ACTIVE",
    )


def test_exact_name_resolves():
    got = resolve_one("Josh Allen", [_p("Josh Allen"), _p("Josh Jacobs")])
    assert got.name == "Josh Allen"


def test_case_and_whitespace_are_forgiven():
    assert resolve_one("  josh allen ", [_p("Josh Allen")]).name == "Josh Allen"


def test_two_matches_are_a_choice_not_a_guess():
    """E-05: a misresolved drop is irreversible, so never pick for the user."""
    with pytest.raises(AmbiguousPlayer) as exc:
        resolve_one("Josh", [_p("Josh Allen", position="QB"), _p("Josh Jacobs")])
    assert "Josh Allen" in str(exc.value)
    assert "Josh Jacobs" in str(exc.value)


def test_no_match_is_no_match():
    with pytest.raises(PlayerNotFound):
        resolve_one("Nobody At All", [_p("Josh Allen")])


def test_substring_resolves_when_unique():
    assert resolve_one("Achane", [_p("De'Von Achane"), _p("Josh Allen")]).name == "De'Von Achane"


def test_sorting_by_projection_puts_missing_data_last():
    """None is absence; it must not sort as zero and must not outrank a real 0.0."""
    players = [_p("None", projected=None), _p("Zero", projected=0.0), _p("Ten", projected=10.0)]
    assert [p.name for p in sort_players(players, "projected")] == ["Ten", "Zero", "None"]


def test_sorting_by_name_is_alphabetical():
    players = [_p("Zeta"), _p("Alpha")]
    assert [p.name for p in sort_players(players, "name")] == ["Alpha", "Zeta"]


def test_unknown_sort_basis_is_rejected_naming_the_options():
    with pytest.raises(ValueError, match="projected"):
        sort_players([_p("A")], "vibes")


def test_pool_values_are_explicit():
    assert {p.value for p in Pool} == {"free_agents", "rostered", "all"}
