"""Tools are plain functions, so they test with no server and no network (M-03)."""

from fantasy_yolo.models import PlayerView
from fantasy_yolo.registry import Kind, registered
from fantasy_yolo.tools.team import build_roster_view, split_starters

BENCH_SLOT = 20


def _p(name, slot, position="RB"):
    return PlayerView(
        player_id=1,
        name=name,
        position=position,
        slot=slot,
        pro_team="KC",
        opponent="LV",
        projected=1.0,
        injury_status="ACTIVE",
    )


def test_starters_and_bench_are_split():
    starters, bench = split_starters([_p("A", "RB"), _p("B", "BE"), _p("C", "IR")])
    assert [p.name for p in starters] == ["A"]
    assert [p.name for p in bench] == ["B", "C"]


def test_roster_view_counts_by_position():
    view = build_roster_view(
        players=[_p("A", "RB"), _p("B", "BE")],
        slot_counts={2: 2, BENCH_SLOT: 6},
        season=2026,
        week=1,
    )
    assert view.counts_by_position["RB"] == 2


def test_roster_view_reports_open_spots():
    view = build_roster_view(
        players=[_p("A", "RB")],
        slot_counts={2: 2, BENCH_SLOT: 6},
        season=2026,
        week=1,
    )
    assert view.open_roster_spots == 7


def test_roster_summary_is_one_line():
    view = build_roster_view(
        players=[_p("A", "RB")],
        slot_counts={2: 2, BENCH_SLOT: 6},
        season=2026,
        week=1,
    )
    assert "\n" not in view.summary


def test_tools_are_registered_as_reads():
    import fantasy_yolo.tools  # noqa: F401

    names = {s.name: s.kind for s in registered()}
    assert names["get_roster"] is Kind.READ
    assert names["get_matchup"] is Kind.READ


def test_no_write_tools_exist_yet():
    import fantasy_yolo.tools  # noqa: F401

    assert registered(include_writes=False) == registered()
