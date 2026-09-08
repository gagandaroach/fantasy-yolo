from datetime import datetime

from fantasy_yolo.models import Page, PlayerView, Provenance, Response

PROV = Provenance(season=2026, week_resolved=1, fetched_at=datetime(2026, 9, 8, 12, 0))


def test_every_response_carries_provenance():
    r = Response(summary="ok", provenance=PROV)
    assert r.provenance.season == 2026
    assert r.provenance.week_resolved == 1


def test_page_reports_truncation():
    p = Page(summary="s", provenance=PROV, total=200, returned=50, offset=0)
    assert p.truncated is True


def test_page_is_not_truncated_when_complete():
    p = Page(summary="s", provenance=PROV, total=50, returned=50, offset=0)
    assert p.truncated is False


def test_player_view_stays_flat():
    p = PlayerView(
        player_id=1,
        name="A Player",
        position="RB",
        slot="RB",
        pro_team="KC",
        opponent="LV",
        projected=12.5,
        injury_status="ACTIVE",
    )
    assert set(p.model_dump()) == {
        "player_id",
        "name",
        "position",
        "slot",
        "pro_team",
        "opponent",
        "projected",
        "injury_status",
    }
