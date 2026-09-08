import pytest

from fantasy_yolo.tools.moves import describe_moves, format_preview_summary

BENCH, QB, RB, FLEX = 20, 0, 2, 23
NAMES = {1: "Runner One", 2: "Quarter Back"}


def test_moves_are_described_in_player_names_not_ids():
    """J-01: the preview must read in names. An id tells a human nothing."""
    lines = describe_moves([(1, BENCH, RB)], NAMES)
    assert "Runner One" in lines[0]
    assert "1" not in lines[0].replace("Runner One", "")


def test_a_move_states_both_ends():
    (line,) = describe_moves([(1, BENCH, RB)], NAMES)
    assert "BE" in line and "RB" in line


def test_an_unknown_player_id_is_shown_not_hidden():
    (line,) = describe_moves([(99, BENCH, RB)], {})
    assert "99" in line


def test_summary_names_anyone_who_cannot_fit():
    summary = format_preview_summary([(1, BENCH, RB)], ["Extra Guy"], NAMES)
    assert "Extra Guy" in summary


def test_summary_of_no_moves_says_so():
    assert "no changes" in format_preview_summary([], [], NAMES).lower()


def test_preview_and_execute_are_separate_tools():
    """One tool cannot be both readOnlyHint and destructiveHint (design §3.1)."""
    import fantasy_yolo.tools  # noqa: F401
    from fantasy_yolo.registry import Kind, registered

    kinds = {s.name: s.kind for s in registered()}
    assert kinds["preview_lineup"] is Kind.WRITE_PREVIEW
    assert kinds["execute_lineup"] is Kind.WRITE_EXECUTE


def test_write_tools_disappear_in_read_only_mode():
    """J-02: not registered at all, so a model cannot offer them."""
    import fantasy_yolo.tools  # noqa: F401
    from fantasy_yolo.registry import registered

    names = {s.name for s in registered(include_writes=False)}
    assert "execute_lineup" not in names
    assert "get_roster" in names


def test_execute_requires_a_confirmation_code():
    import inspect

    from fantasy_yolo.tools.moves import execute_lineup

    assert "confirm" in inspect.signature(execute_lineup).parameters


@pytest.mark.parametrize("tool", ["preview_lineup", "execute_lineup"])
def test_write_tools_are_registered(tool):
    import fantasy_yolo.tools  # noqa: F401
    from fantasy_yolo.registry import registered

    assert tool in {s.name for s in registered()}
