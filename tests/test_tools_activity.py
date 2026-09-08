
from fantasy_yolo.tools.activity import build_transaction_rows, summarise_pending


def test_pending_summary_counts_by_type():
    pending = [{"type": "WAIVER"}, {"type": "WAIVER"}, {"type": "TRADE_PROPOSAL"}]
    assert summarise_pending(pending) == {"WAIVER": 2, "TRADE_PROPOSAL": 1}


def test_pending_summary_of_nothing_is_empty():
    assert summarise_pending([]) == {}




RAW_DRAFT = {
    "id": "abc",
    "type": "DRAFT",
    "status": "EXECUTED",
    "teamId": 13,
    "scoringPeriodId": 1,
    "bidAmount": 0,
    "proposedDate": 1788832530025,
    "items": [{"playerId": 1, "type": "DRAFT", "toTeamId": 13}],
}
RAW_WAIVER = {**RAW_DRAFT, "id": "def", "type": "WAIVER", "bidAmount": 17}


def test_transaction_rows_carry_type_status_and_team():
    rows = build_transaction_rows([RAW_DRAFT], {13: "My Team"}, {1: "A Player"})
    assert rows[0].type == "DRAFT"
    assert rows[0].status == "EXECUTED"
    assert rows[0].team == "My Team"


def test_transaction_rows_resolve_player_names_when_known():
    rows = build_transaction_rows([RAW_DRAFT], {13: "My Team"}, {1: "A Player"})
    assert rows[0].players == ["A Player"]


def test_unknown_player_ids_are_shown_as_ids_not_dropped():
    """Silently omitting a player would make the row quietly wrong."""
    rows = build_transaction_rows([RAW_DRAFT], {13: "My Team"}, {})
    assert rows[0].players == ["player 1"]


def test_a_zero_bid_is_none_but_a_real_bid_is_kept():
    assert build_transaction_rows([RAW_DRAFT], {}, {})[0].bid is None
    assert build_transaction_rows([RAW_WAIVER], {}, {})[0].bid == 17


def test_transaction_rows_have_a_real_timestamp():
    assert build_transaction_rows([RAW_DRAFT], {}, {})[0].when.tzinfo is not None
