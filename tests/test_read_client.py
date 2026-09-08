import pytest

from fantasy_yolo.read.client import ReadClient, slot_counts_from_settings


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


def test_role_header_none_means_unauthenticated():
    assert ReadClient.role_is_authenticated({"X-Fantasy-Role": "NONE"}) is False
    assert ReadClient.role_is_authenticated({"X-Fantasy-Role": "MEMBER"}) is True
    assert ReadClient.role_is_authenticated({}) is False
