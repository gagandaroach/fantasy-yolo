from datetime import datetime

from fantasy_yolo.tools.league import (
    WaiverSystem,
    build_standings,
    detect_waiver_system,
    epoch_ms_to_local,
)


def test_faab_league_is_detected_from_a_positive_budget():
    assert detect_waiver_system({"acquisitionBudget": 100}) is WaiverSystem.FAAB


def test_priority_league_is_detected_from_a_zero_budget():
    """F-05: a bid field in a rolling-priority league is a malformed transaction."""
    assert detect_waiver_system({"acquisitionBudget": 0}) is WaiverSystem.PRIORITY


def test_missing_budget_means_priority():
    assert detect_waiver_system({}) is WaiverSystem.PRIORITY


def test_epoch_ms_becomes_a_local_datetime():
    """D-02: dates are real timestamps in the user's zone, not settings fields."""
    got = epoch_ms_to_local(1757332800000)
    assert isinstance(got, datetime)
    assert got.tzinfo is not None


def test_epoch_zero_is_treated_as_unset():
    assert epoch_ms_to_local(0) is None


def test_standings_are_ordered_by_wins_then_points():
    rows = build_standings(
        [
            {"name": "B", "wins": 1, "losses": 0, "points_for": 90.0, "points_against": 80.0},
            {"name": "A", "wins": 1, "losses": 0, "points_for": 100.0, "points_against": 80.0},
            {"name": "C", "wins": 0, "losses": 1, "points_for": 120.0, "points_against": 80.0},
        ]
    )
    assert [r.name for r in rows] == ["A", "B", "C"]
    assert rows[0].rank == 1
