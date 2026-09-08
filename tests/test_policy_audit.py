import json

import pytest

from fantasy_yolo.creds import Credentials
from fantasy_yolo.policy.audit import AuditLog

CREDS = Credentials(espn_s2="SUPER_SECRET_S2", swid="{ABC-123}")
PAYLOAD = {"type": "ROSTER", "teamId": 8, "items": [{"playerId": 1}]}


@pytest.fixture
def log(tmp_path):
    return AuditLog(tmp_path / "audit.jsonl", CREDS)


def _lines(log):
    return [json.loads(x) for x in log.path.read_text().splitlines() if x.strip()]


def test_intent_is_written_before_the_request_leaves(log):
    log.intent("execute_lineup", PAYLOAD)
    assert _lines(log)[0]["event"] == "intent"


def test_outcome_is_written_after(log):
    log.intent("execute_lineup", PAYLOAD)
    log.outcome("execute_lineup", 200, {"status": "EXECUTED"})
    assert [e["event"] for e in _lines(log)] == ["intent", "outcome"]


def test_an_interrupted_write_still_leaves_its_intent(log):
    """J-04's read-back is only reconcilable if intent survives a crash."""
    log.intent("execute_lineup", PAYLOAD)
    assert _lines(log)[0]["payload"]["items"] == [{"playerId": 1}]


def test_credentials_are_redacted_from_every_line(log):
    log.outcome("execute_lineup", 401, {"messages": ["cookie SUPER_SECRET_S2 rejected"]})
    assert "SUPER_SECRET_S2" not in log.path.read_text()


def test_the_swid_is_redacted_too(log):
    log.intent("execute_lineup", {"memberId": "{ABC-123}"})
    assert "ABC-123" not in log.path.read_text()


def test_reads_are_logged_by_name_and_arguments_only(log):
    """Logging read responses would bury the entries that matter under rosters."""
    log.read("get_roster", {"week": 1})
    entry = _lines(log)[0]
    assert entry["tool"] == "get_roster"
    assert entry["args"] == {"week": 1}
    assert "response" not in entry


def test_the_log_is_append_only(log):
    log.read("get_roster", {})
    log.read("get_matchup", {})
    assert len(_lines(log)) == 2


def test_the_log_file_is_private(log):
    log.read("get_roster", {})
    assert oct(log.path.stat().st_mode)[-3:] == "600"
