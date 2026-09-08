import pytest

from fantasy_yolo.policy.tokens import (
    ExpiredToken,
    TokenMismatch,
    TokenStore,
    UnknownToken,
    payload_fingerprint,
)

PAYLOAD = {"type": "ROSTER", "teamId": 8, "items": [{"playerId": 1}]}
OTHER = {"type": "ROSTER", "teamId": 8, "items": [{"playerId": 2}]}


@pytest.fixture
def store(tmp_path):
    return TokenStore(tmp_path / "pending.json", ttl_seconds=300)


def test_a_token_authorises_the_payload_it_was_issued_for(store):
    token = store.issue(PAYLOAD)
    store.consume(token, PAYLOAD)


def test_a_token_cannot_be_spent_on_a_different_payload(store):
    """J-01: an approval given for one add must not execute another."""
    token = store.issue(PAYLOAD)
    with pytest.raises(TokenMismatch):
        store.consume(token, OTHER)


def test_a_token_is_single_use(store):
    """Which is also what stops a retried execute double-submitting."""
    token = store.issue(PAYLOAD)
    store.consume(token, PAYLOAD)
    with pytest.raises(UnknownToken):
        store.consume(token, PAYLOAD)


def test_an_unknown_token_is_refused(store):
    with pytest.raises(UnknownToken):
        store.consume("nonsense", PAYLOAD)


def test_an_expired_token_is_refused(tmp_path):
    store = TokenStore(tmp_path / "pending.json", ttl_seconds=0)
    token = store.issue(PAYLOAD)
    with pytest.raises(ExpiredToken):
        store.consume(token, PAYLOAD)


def test_tokens_survive_across_processes(tmp_path):
    """The CLI previews in one process and executes in another (M-18)."""
    path = tmp_path / "pending.json"
    token = TokenStore(path, ttl_seconds=300).issue(PAYLOAD)
    TokenStore(path, ttl_seconds=300).consume(token, PAYLOAD)


def test_fingerprint_ignores_key_order():
    a = {"type": "ROSTER", "teamId": 8}
    b = {"teamId": 8, "type": "ROSTER"}
    assert payload_fingerprint(a) == payload_fingerprint(b)


def test_fingerprint_changes_with_any_value():
    assert payload_fingerprint(PAYLOAD) != payload_fingerprint(OTHER)


def test_the_store_never_holds_the_payload_itself(tmp_path):
    """Only the fingerprint is persisted, so the pending file is not a record of
    what you were about to do to your roster."""
    path = tmp_path / "pending.json"
    TokenStore(path, ttl_seconds=300).issue(PAYLOAD)
    assert "playerId" not in path.read_text()
