import pytest

from fantasy_yolo.read.weeks import resolve_week


def test_none_resolves_to_the_latest_scoring_period():
    assert resolve_week(None, latest=3) == 3


def test_an_explicit_week_is_honoured():
    assert resolve_week(5, latest=3) == 5


def test_week_zero_is_rejected():
    with pytest.raises(ValueError, match="between 1 and 18"):
        resolve_week(0, latest=3)


def test_week_past_the_season_is_rejected():
    with pytest.raises(ValueError, match="between 1 and 18"):
        resolve_week(19, latest=3)
