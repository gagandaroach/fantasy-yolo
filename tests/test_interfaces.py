import typer.main

from fantasy_yolo.cli import build_cli, cli_name
from fantasy_yolo.mcp.server import annotations_for, build_server
from fantasy_yolo.registry import Kind, registered


def test_read_tools_are_annotated_read_only():
    a = annotations_for(Kind.READ)
    assert a.read_only_hint is True
    assert a.destructive_hint is False


def test_execute_tools_are_annotated_destructive():
    a = annotations_for(Kind.WRITE_EXECUTE)
    assert a.read_only_hint is False
    assert a.destructive_hint is True


def test_preview_tools_are_read_only():
    """Preview and execute must be separate tools: one tool cannot carry both hints."""
    assert annotations_for(Kind.WRITE_PREVIEW).read_only_hint is True


def test_server_registers_every_tool():
    import fantasy_yolo.tools  # noqa: F401

    server = build_server(include_writes=True)
    names = {t.name for t in server._tool_manager.list_tools()}
    assert {"get_roster", "get_matchup"} <= names


def test_cli_exposes_a_command_per_tool():
    import fantasy_yolo.tools  # noqa: F401

    names = {c.name for c in build_cli().registered_commands}
    assert {cli_name(s.name) for s in registered()} <= names


def test_cli_names_drop_the_get_prefix_but_keep_write_verbs():
    assert cli_name("get_roster") == "roster"
    assert cli_name("execute_lineup") == "execute-lineup"
    assert cli_name("preview_lineup") == "preview-lineup"


def test_cli_actually_builds_a_click_app():
    """Typer rejects PEP 604 unions, so listing command names is not enough —
    the app has to be built for real."""
    import fantasy_yolo.tools  # noqa: F401

    group = typer.main.get_command(build_cli())
    assert "roster" in group.commands


def test_cli_optional_week_becomes_an_option():
    import fantasy_yolo.tools  # noqa: F401

    group = typer.main.get_command(build_cli())
    params = {p.name for p in group.commands["roster"].params}
    assert {"week", "league"} <= params
