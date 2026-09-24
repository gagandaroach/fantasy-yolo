import inspect

import pytest

from fantasy_yolo.registry import Kind, registered


def _kinds():
    import fantasy_yolo.tools  # noqa: F401

    return {s.name: s.kind for s in registered()}


@pytest.mark.parametrize(
    "name,kind",
    [
        ("preview_add_drop", Kind.WRITE_PREVIEW),
        ("execute_add_drop", Kind.WRITE_EXECUTE),
        ("preview_waiver", Kind.WRITE_PREVIEW),
        ("execute_waiver", Kind.WRITE_EXECUTE),
        ("cancel_waiver", Kind.WRITE_EXECUTE),
    ],
)
def test_write_tools_are_registered_with_the_right_kind(name, kind):
    assert _kinds()[name] is kind


@pytest.mark.parametrize("name", ["execute_add_drop", "execute_waiver", "cancel_waiver"])
def test_every_execute_demands_a_confirmation_code(name):
    from fantasy_yolo.tools import transactions

    fn = getattr(transactions, name)
    assert "confirm" in inspect.signature(fn).parameters


def test_dropping_is_flagged_as_the_irreversible_one():
    """F-08. A misresolved drop cannot be undone: the player hits waivers."""
    from fantasy_yolo.tools.transactions import preview_add_drop

    doc = inspect.getdoc(preview_add_drop).lower()
    assert "cannot be undone" in doc or "irreversible" in doc


def test_previews_do_not_appear_as_destructive():
    from fantasy_yolo.mcp.server import annotations_for

    assert annotations_for(Kind.WRITE_PREVIEW).destructive_hint is False
    assert annotations_for(Kind.WRITE_EXECUTE).destructive_hint is True


def test_all_write_tools_vanish_in_read_only_mode():
    import fantasy_yolo.tools  # noqa: F401

    reads = {s.name for s in registered(include_writes=False)}
    for name in (
        "execute_add_drop",
        "execute_waiver",
        "cancel_waiver",
        "preview_add_drop",
        "preview_waiver",
    ):
        assert name not in reads


def test_summary_lists_every_legality_problem_not_just_the_first():
    from fantasy_yolo.tools.transactions import format_problems

    got = format_problems(["roster is full", "already on your roster"])
    assert "roster is full" in got and "already on your roster" in got


@pytest.fixture
def tokens(tmp_path, monkeypatch):
    from fantasy_yolo.policy.tokens import TokenStore
    from fantasy_yolo.tools import transactions

    store = TokenStore(tmp_path / "pending.json", ttl_seconds=300)
    monkeypatch.setattr(transactions, "get_tokens", lambda: store)
    return store


def test_the_code_alone_recovers_the_players_from_the_preview(tokens):
    """Like execute_lineup: the code carries the request, so nothing is retyped."""
    from fantasy_yolo.tools.transactions import _recall

    code = tokens.issue({"p": 1}, intent={"add": "Kaleb Johnson", "drop": "Sam Darnold"})
    assert _recall(code, "preview_add_drop") == {"add": "Kaleb Johnson", "drop": "Sam Darnold"}


def test_recall_refuses_an_unknown_code(tokens):
    from fantasy_yolo.tools.transactions import _recall

    with pytest.raises(LookupError, match="preview_waiver"):
        _recall("deadbeef", "preview_waiver")


def test_recall_refuses_a_code_that_carries_no_request(tokens):
    """A code from before intents were carried must not execute as 'nothing'."""
    from fantasy_yolo.tools.transactions import _recall

    code = tokens.issue({"p": 1})
    with pytest.raises(LookupError):
        _recall(code, "preview_add_drop")


def test_execute_waiver_no_longer_demands_the_player_be_retyped():
    from fantasy_yolo.tools.transactions import execute_waiver

    assert inspect.signature(execute_waiver).parameters["add"].default is None
