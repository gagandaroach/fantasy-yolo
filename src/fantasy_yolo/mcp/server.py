"""MCP frontend. Reads the registry; it is not the source of truth (M-18)."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

import fantasy_yolo.tools  # noqa: F401  (importing registers the tools)
from fantasy_yolo import __version__
from fantasy_yolo.config import load_settings
from fantasy_yolo.registry import Kind, registered

INSTRUCTIONS = """\
Read and act on one ESPN Fantasy Football team, on the user's behalf.

What this server does NOT have, and you must not infer (M-15):
- No projections beyond ESPN's own number. There is no model here.
- No injury news, no news feed, no reporter text.
- No timestamps on injury designations. ESPN reports a status word and nothing
  else, so never say how recent it is or narrate a recovery.
- No ranking of players on merit. The user decides who is better.

Every response states the season, the week it resolved to, and when it was
fetched. Report those rather than assuming which week the user means.
"""


def annotations_for(kind: Kind) -> ToolAnnotations:
    """J-08.

    Preview is read-only and execute is destructive, which is why they must be
    separate tools — one tool cannot carry both hints.
    """
    return ToolAnnotations(
        read_only_hint=kind is not Kind.WRITE_EXECUTE,
        destructive_hint=kind is Kind.WRITE_EXECUTE,
        idempotent_hint=False,
        open_world_hint=True,
    )


def build_server(include_writes: bool) -> MCPServer:
    server = MCPServer(name="fantasy-yolo", version=__version__, instructions=INSTRUCTIONS)
    for spec in registered(include_writes=include_writes):
        server.tool(
            name=spec.name,
            description=spec.description,
            annotations=annotations_for(spec.kind),
        )(spec.fn)
    return server


def main() -> None:
    """J-02: with writes disabled the tools are not registered at all, so a model
    cannot see or offer them."""
    try:
        write_enabled = load_settings().write_enabled
    except FileNotFoundError:
        write_enabled = False
    build_server(include_writes=write_enabled).run(transport="stdio")
