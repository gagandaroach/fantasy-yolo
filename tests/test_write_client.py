import pytest
import requests

from fantasy_yolo.write.client import WriteClient, WriteResult, build_session
from fantasy_yolo.write.errors import Outcome

PAYLOAD = {"type": "ROSTER", "teamId": 8, "items": [{"playerId": 1}]}


def test_the_session_is_configured_to_never_retry():
    """J-04: every Python HTTP stack retries by default, and a retried write
    genuinely double-submits. The invariant has to be structural."""
    session = build_session()
    for adapter in session.adapters.values():
        assert adapter.max_retries.total == 0


def test_the_write_url_targets_the_write_host():
    assert "lm-api-writes" in WriteClient.url(2026, 123)


def test_a_timeout_is_unknown_not_failure(monkeypatch):
    """The dangerous case: we do not know whether it executed, and saying
    "failed" invites the user to redo a move that already landed."""
    client = WriteClient(year=2026, league_id=1, cookies={})

    def boom(*a, **k):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(client.session, "post", boom)
    result = client.post(PAYLOAD)
    assert result.outcome is Outcome.UNKNOWN
    assert "timed out" in result.explanation.lower() or "unknown" in result.explanation.lower()


def test_a_connection_error_is_also_unknown(monkeypatch):
    client = WriteClient(year=2026, league_id=1, cookies={})

    def boom(*a, **k):
        raise requests.ConnectionError("reset")

    monkeypatch.setattr(client.session, "post", boom)
    assert client.post(PAYLOAD).outcome is Outcome.UNKNOWN


def test_an_executed_response_is_applied(monkeypatch):
    client = WriteClient(year=2026, league_id=1, cookies={})
    monkeypatch.setattr(client.session, "post", _fake(200, {"status": "EXECUTED"}))
    assert client.post(PAYLOAD).outcome is Outcome.APPLIED


def test_a_rule_violation_is_explained_in_plain_language(monkeypatch):
    client = WriteClient(year=2026, league_id=1, cookies={})
    monkeypatch.setattr(
        client.session,
        "post",
        _fake(400, {"details": [{"type": "TRAN_ROSTER_LIMIT_EXCEEDED_ONE"}]}),
    )
    result = client.post(PAYLOAD)
    assert result.outcome is Outcome.REJECTED
    assert "roster is full" in result.explanation


def test_a_result_carries_the_payload_for_reconciliation():
    result = WriteResult(
        outcome=Outcome.UNKNOWN, status=None, body={}, explanation="x", payload=PAYLOAD
    )
    assert result.payload == PAYLOAD


def test_unknown_outcomes_are_never_reported_as_success():
    result = WriteResult(
        outcome=Outcome.UNKNOWN, status=None, body={}, explanation="x", payload=PAYLOAD
    )
    assert result.succeeded is False


def test_pending_is_not_reported_as_applied():
    result = WriteResult(
        outcome=Outcome.PENDING, status=200, body={}, explanation="x", payload=PAYLOAD
    )
    assert result.succeeded is False


def _fake(status, body):
    class R:
        status_code = status

        @staticmethod
        def json():
            return body

        text = str(body)

    def post(*a, **k):
        return R()

    return post


@pytest.mark.parametrize("status", [401, 403, 415])
def test_auth_and_content_type_failures_are_rejected(monkeypatch, status):
    client = WriteClient(year=2026, league_id=1, cookies={})
    monkeypatch.setattr(client.session, "post", _fake(status, {}))
    assert client.post(PAYLOAD).outcome is Outcome.REJECTED
