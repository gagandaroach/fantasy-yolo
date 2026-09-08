from fantasy_yolo.write.errors import Outcome, explain, outcome_for


def test_roster_limit_matches_by_prefix_not_exact_string():
    """The real constants come in _ONE / _PLURAL / _LM variants; exact matching
    breaks on every variant but the one you happened to see."""
    for code in (
        "TRAN_ROSTER_LIMIT_EXCEEDED_ONE",
        "TRAN_ROSTER_LIMIT_EXCEEDED_PLURAL_LM",
        "TRAN_ROSTER_LIMIT_EXCEEDED_TRADE_RESERVED_ONE",
    ):
        assert "roster is full" in explain(400, {"details": [{"type": code}]}).lower()


def test_slot_limit_is_explained_distinctly():
    got = explain(400, {"details": [{"type": "TRAN_ROSTER_SLOT_LIMIT_EXCEEDED"}]})
    assert "slot" in got.lower()


def test_roster_lock_is_explained():
    got = explain(409, {"details": [{"type": "FAILED_ROSTERLOCK"}]})
    assert "locked" in got.lower()


def test_missing_items_is_explained_as_a_no_op():
    got = explain(409, {"messages": ["TransactionItems are missing"]})
    assert "no changes" in got.lower()


def test_an_unknown_code_is_reported_verbatim_not_swallowed():
    got = explain(400, {"details": [{"type": "TRAN_SOMETHING_NEW"}]})
    assert "TRAN_SOMETHING_NEW" in got


def test_a_400_is_never_reported_as_nothing_happened():
    """ESPN's own handler makes no distinction between 400 and 409 and reads the
    rule out of details[].type, so a 400 can mean a rule was broken."""
    assert "nothing happened" not in explain(400, {"details": []}).lower()


def test_415_names_the_content_type():
    assert "content-type" in explain(415, {}).lower()


def test_executed_is_applied():
    assert outcome_for(200, {"status": "EXECUTED"}) is Outcome.APPLIED


def test_pending_is_pending_not_applied():
    """A waiver claim sits pending until the run; calling that success is a lie."""
    assert outcome_for(200, {"status": "PENDING"}) is Outcome.PENDING


def test_a_401_is_rejected_not_unknown():
    assert outcome_for(401, {}) is Outcome.REJECTED


def test_a_200_with_an_unrecognised_status_is_unknown():
    assert outcome_for(200, {"status": "WHAT"}) is Outcome.UNKNOWN


# Captured from a real EXECUTED lineup write against league 2013746535, 2026 wk1
# (txn 337c7ea1-a1dc-42ca-bcfe-34adbae5e4d4). The first authenticated write this
# project ever made, and the fixture the success branch is built on.
EXECUTED_BODY = {
    "bidAmount": 0,
    "executionType": "EXECUTE",
    "id": "337c7ea1-a1dc-42ca-bcfe-34adbae5e4d4",
    "isActingAsTeamOwner": False,
    "isLeagueManager": False,
    "isPending": False,
    "proposedDate": 1788859039655,
    "rating": 0,
    "scoringPeriodId": 1,
    "skipTransactionCounters": False,
    "status": "EXECUTED",
    "subOrder": 0,
    "teamId": 8,
    "type": "ROSTER",
}


def test_a_successful_write_is_not_described_as_a_refusal():
    """The worst possible false alarm on a never-retry path: a user who reads
    "ESPN refused this" after a write that landed will re-run it."""
    got = explain(200, EXECUTED_BODY)
    assert "refused" not in got.lower()
    assert "applied" in got.lower() or "executed" in got.lower()


def test_a_successful_write_quotes_its_transaction_id():
    assert "337c7ea1-a1dc-42ca-bcfe-34adbae5e4d4" in explain(200, EXECUTED_BODY)


def test_a_pending_write_says_it_is_pending_not_done():
    body = {**EXECUTED_BODY, "status": "PENDING", "isPending": True}
    got = explain(200, body).lower()
    assert "pending" in got
    assert "refused" not in got


def test_isPending_true_is_pending_even_if_status_is_missing():
    """ESPN sends isPending alongside status; trust it when status is absent."""
    assert outcome_for(200, {"isPending": True}) is Outcome.PENDING


def test_the_real_executed_body_reads_as_applied():
    assert outcome_for(200, EXECUTED_BODY) is Outcome.APPLIED
