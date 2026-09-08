import pytest

from fantasy_yolo.write.oracle import Verdict, transactions_url, verdict_for


def test_401_means_the_body_parsed():
    assert verdict_for(401) is Verdict.WELL_FORMED


def test_400_means_the_body_did_not():
    assert verdict_for(400) is Verdict.MALFORMED


def test_other_statuses_are_inconclusive():
    assert verdict_for(415) is Verdict.INCONCLUSIVE
    assert verdict_for(200) is Verdict.INCONCLUSIVE


def test_url_targets_the_write_host_transactions_collection():
    url = transactions_url(2026, 123)
    assert url.endswith("/seasons/2026/segments/0/leagues/123/transactions/")
    assert "lm-api-writes" in url


def test_check_shape_cannot_be_given_credentials():
    """The safety property is structural: no cookie parameter exists, so this
    function cannot be made to execute a transaction."""
    import inspect

    from fantasy_yolo.write.oracle import check_shape

    params = set(inspect.signature(check_shape).parameters)
    assert params == {"payload", "year", "league_id"}
    assert not {"cookies", "creds", "credentials", "session"} & params


@pytest.mark.network
def test_builders_emit_shapes_espn_accepts():
    """Run with -m network. Sends unauthenticated POSTs; changes nothing."""
    from fantasy_yolo.write.oracle import check_shape
    from fantasy_yolo.write.payloads import (
        BENCH,
        build_add_drop,
        build_lineup_moves,
        build_waiver_claim,
    )

    member = "{00000000-0000-0000-0000-000000000000}"
    cases = {
        "lineup": build_lineup_moves(8, member, [(1, BENCH, 2)], 1, 1),
        "future_lineup": build_lineup_moves(8, member, [(1, BENCH, 2)], 5, 1),
        "add_drop": build_add_drop(8, member, add_player=1, drop_player=2),
        "standalone_drop": build_add_drop(8, member, add_player=None, drop_player=2),
        "waiver": build_waiver_claim(8, member, add_player=1, drop_player=None, bid=5),
    }
    for name, payload in cases.items():
        got, body = check_shape(payload, 2026, 1)
        assert got is Verdict.WELL_FORMED, f"{name} rejected by ESPN: {body}"


@pytest.mark.network
def test_the_oracle_actually_discriminates():
    """A guard on the guard: if a deliberately broken payload also came back
    well-formed, the oracle would be proving nothing."""
    from fantasy_yolo.write.oracle import check_shape

    got, _ = check_shape({"type": "NOT_A_REAL_TYPE", "items": "not a list"}, 2026, 1)
    assert got is Verdict.MALFORMED
