"""B-09: one pre-kickoff check. Every element is a read of state or the
schedule, so nothing here renders an opinion (X-01)."""

from datetime import datetime, timedelta

from fantasy_yolo.models import PlayerView
from fantasy_yolo.tools.lineup import Alert, build_lineup_check, empty_starting_slots

NOW = datetime(2026, 9, 13, 12, 0).astimezone()


def _p(name, slot, injury="ACTIVE", projected=10.0, opponent="LV"):
    return PlayerView(
        player_id=abs(hash(name)) % 10000,
        name=name,
        position="RB",
        slot=slot,
        pro_team="KC",
        opponent=opponent,
        projected=projected,
        injury_status=injury,
    )


def test_flags_a_starter_espn_lists_as_out():
    alerts = build_lineup_check([_p("Out Guy", "RB", injury="OUT")], {2: 1}, {}, NOW)
    assert any(a.kind == "starter_out" and "Out Guy" in a.detail for a in alerts)


def test_flags_a_starter_on_bye():
    alerts = build_lineup_check([_p("Bye Guy", "RB", opponent="")], {2: 1}, {}, NOW)
    assert any(a.kind == "starter_on_bye" for a in alerts)


def test_does_not_flag_a_benched_player_on_bye():
    alerts = build_lineup_check([_p("Bye Guy", "BE", opponent="")], {2: 1, 20: 1}, {}, NOW)
    assert not any(a.kind == "starter_on_bye" for a in alerts)


def test_flags_an_empty_starting_slot():
    assert empty_starting_slots([], {2: 2}) == {"RB": 2}


def test_full_lineup_has_no_empty_slots():
    assert empty_starting_slots([_p("A", "RB"), _p("B", "RB")], {2: 2}) == {}


def test_flags_a_starter_whose_game_kicked_off():
    kicked = {"Early Guy": NOW - timedelta(hours=1)}
    alerts = build_lineup_check([_p("Early Guy", "RB")], {2: 1}, kicked, NOW)
    assert any(a.kind == "already_locked" for a in alerts)


def test_does_not_flag_a_game_still_to_come():
    later = {"Late Guy": NOW + timedelta(hours=3)}
    alerts = build_lineup_check([_p("Late Guy", "RB")], {2: 1}, later, NOW)
    assert not any(a.kind == "already_locked" for a in alerts)


def test_flags_a_starter_espn_projects_at_zero():
    alerts = build_lineup_check([_p("Zero Guy", "RB", projected=0.0)], {2: 1}, {}, NOW)
    assert any(a.kind == "projected_zero" for a in alerts)


def test_does_not_flag_a_missing_projection_as_zero():
    """None is absence, not a projection of zero (M-15)."""
    alerts = build_lineup_check([_p("No Data", "RB", projected=None)], {2: 1}, {}, NOW)
    assert not any(a.kind == "projected_zero" for a in alerts)


def test_a_clean_lineup_produces_no_alerts():
    players = [_p("Fine", "RB"), _p("Benched", "BE", injury="OUT")]
    assert build_lineup_check(players, {2: 1, 20: 1}, {}, NOW) == []


def test_alerts_state_facts_not_advice():
    """X-01: the tool reports, the human decides. No alert may recommend."""
    alerts = build_lineup_check([_p("Out Guy", "RB", injury="OUT")], {2: 1}, {}, NOW)
    banned = ("should", "recommend", "better", "instead", "start ", "bench ")
    for a in alerts:
        assert not any(word in a.detail.lower() for word in banned), a.detail


def test_alert_is_hashable_for_dedup():
    assert isinstance(hash(Alert(kind="k", detail="d")), int)
