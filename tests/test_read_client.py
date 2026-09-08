import pytest

from fantasy_yolo.read.client import ReadClient, auth_error_for, slot_counts_from_settings


def test_slot_counts_come_from_the_raw_dict_keyed_by_slot_id():
    raw = {"settings": {"rosterSettings": {"lineupSlotCounts": {"0": 1, "2": 2, "20": 6}}}}
    assert slot_counts_from_settings(raw) == {0: 1, 2: 2, 20: 6}


def test_slot_counts_reject_missing_settings():
    with pytest.raises(KeyError, match="lineupSlotCounts"):
        slot_counts_from_settings({"settings": {}})


def test_read_client_refuses_a_write_host():
    with pytest.raises(ValueError, match="lm-api-writes"):
        ReadClient.assert_read_host("https://lm-api-writes.fantasy.espn.com/x")


def test_read_client_accepts_the_read_host():
    ReadClient.assert_read_host("https://lm-api-reads.fantasy.espn.com/x")


def test_an_authenticated_200_is_not_treated_as_expired():
    """Observed 2026-09-08: ESPN returns X-Fantasy-Role: NONE on authenticated
    200s for the league endpoint, so the header cannot be the auth signal."""
    assert auth_error_for(200, {"X-Fantasy-Role": "NONE"}) is None


def test_401_explains_the_login_rather_than_the_league():
    message = auth_error_for(401, {"X-Fantasy-Role": "NONE"})
    assert message is not None
    assert "expired" in message
    assert "docs/setup.md" in message


def test_403_is_also_an_auth_problem():
    assert auth_error_for(403, {}) is not None


def test_500_is_not_an_auth_problem():
    assert auth_error_for(500, {}) is None
