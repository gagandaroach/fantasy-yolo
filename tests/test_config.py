import json

import pytest

from fantasy_yolo.config import LeagueConfig, Settings, load_settings


def _settings(**kw):
    base = dict(
        leagues=[
            LeagueConfig(name="office", league_id=1, team_id=2, year=2026),
            LeagueConfig(name="money", league_id=3, team_id=4, year=2026),
        ],
        active="office",
    )
    return Settings(**{**base, **kw})


def test_writes_are_disabled_by_default():
    assert _settings().write_enabled is False


def test_resolves_the_active_league():
    assert _settings().league().name == "office"


def test_resolves_a_named_league():
    assert _settings().league("money").league_id == 3


def test_unknown_league_names_the_options():
    with pytest.raises(KeyError, match="money"):
        _settings().league("nope")


def test_active_must_exist():
    with pytest.raises(ValueError, match="active league"):
        _settings(active="ghost")


def test_load_settings_reads_json(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(
        json.dumps(
            {
                "leagues": [{"name": "office", "league_id": 1, "team_id": 2, "year": 2026}],
                "active": "office",
            }
        )
    )
    assert load_settings(p).league().team_id == 2
