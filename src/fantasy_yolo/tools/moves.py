"""Lineup writes, split into preview and execute (J-01, H-01..H-04).

The two halves are separate tools rather than one tool with a mode, because MCP
annotations are per-tool and a single tool cannot be both readOnlyHint and
destructiveHint (design §3.1).

Writes are declarative. You say who should be starting; the moves are recomputed
from a fresh read at execute time rather than replayed from the preview, which is
what makes a crashed run safe to re-run on a platform with no idempotency key.
"""

from __future__ import annotations

from fantasy_yolo.context import get_audit, get_client, get_tokens, get_write_client
from fantasy_yolo.espn.football.constant import POSITION_MAP
from fantasy_yolo.models import Response
from fantasy_yolo.policy.plan import Move, plan_lineup
from fantasy_yolo.read.weeks import provenance, resolve_week
from fantasy_yolo.registry import Kind, tool
from fantasy_yolo.tools.team import to_player_view
from fantasy_yolo.write.payloads import build_lineup_moves


class LineupPreview(Response):
    moves: list[str]
    cannot_fit: list[str]
    confirm: str | None
    """Pass this back to execute_lineup. None when there is nothing to do."""


class WriteOutcome(Response):
    outcome: str
    explanation: str
    applied_moves: list[str]


def _slot_label(slot: int) -> str:
    label = POSITION_MAP.get(slot)
    return label if isinstance(label, str) and label else str(slot)


def describe_moves(moves: list[Move], names: dict[int, str]) -> list[str]:
    """In player names, never ids — an id tells a human nothing (J-01)."""
    return [
        f"{names.get(pid, f'player {pid}')}: {_slot_label(src)} -> {_slot_label(dst)}"
        for pid, src, dst in moves
    ]


def format_preview_summary(
    moves: list[Move], cannot_fit: list[str], names: dict[int, str]
) -> str:
    parts = [f"{len(moves)} move(s)"] if moves else ["no changes needed"]
    if cannot_fit:
        parts.append("could not fit: " + ", ".join(cannot_fit))
    return "; ".join(parts)


def _plan(start: list[str], week: int | None, league: str | None):
    client = get_client(league)
    latest = client.latest_scoring_period()
    resolved = resolve_week(week, latest)
    roster = [to_player_view(p, resolved) for p in client.my_team().roster]
    names = {p.player_id: p.name for p in roster}
    moves, cannot_fit = plan_lineup(roster, start, client.lineup_slot_counts())
    return client, latest, resolved, roster, names, moves, cannot_fit


@tool(kind=Kind.WRITE_PREVIEW)
def preview_lineup(
    start: list[str],
    week: int | None = None,
    league: str | None = None,
) -> LineupPreview:
    """Show exactly what setting this lineup would do, and hand back a code.

    Name the players you want starting; slots are worked out for you from your
    league's own rules. Anyone who cannot be fitted legally is named. Nothing is
    written. Pass the returned code to execute_lineup to actually make it happen.
    """
    client, latest, resolved, roster, names, moves, cannot_fit = _plan(start, week, league)

    confirm = None
    if moves:
        payload = build_lineup_moves(
            team_id=client.cfg.team_id,
            member_id=client.creds.member_id(),
            moves=moves,
            scoring_period=resolved,
            latest_period=latest,
        )
        confirm = get_tokens().issue(payload)

    return LineupPreview(
        summary=format_preview_summary(moves, cannot_fit, names),
        provenance=provenance(client.cfg.year, resolved),
        moves=describe_moves(moves, names),
        cannot_fit=cannot_fit,
        confirm=confirm,
    )


@tool(kind=Kind.WRITE_EXECUTE)
def execute_lineup(
    confirm: str,
    start: list[str],
    week: int | None = None,
    league: str | None = None,
) -> WriteOutcome:
    """Set your starting lineup. This writes to your ESPN account.

    Requires the code from preview_lineup for this exact change. Your roster is
    re-read immediately beforehand, and the write is refused if anything moved
    since the preview. Nothing is ever retried.
    """
    audit = get_audit(league)
    # J-09: re-read and re-plan from current state, so a lineup set on your phone
    # between preview and execute is never silently clobbered. The token is bound
    # to the payload, so a changed roster produces a different payload and the
    # confirmation is refused rather than applied to something else.
    client, latest, resolved, roster, names, moves, cannot_fit = _plan(start, week, league)

    if not moves:
        return WriteOutcome(
            summary="no changes needed",
            provenance=provenance(client.cfg.year, resolved),
            outcome="applied",
            explanation="your lineup is already in that arrangement; nothing was sent",
            applied_moves=[],
        )

    payload = build_lineup_moves(
        team_id=client.cfg.team_id,
        member_id=client.creds.member_id(),
        moves=moves,
        scoring_period=resolved,
        latest_period=latest,
    )
    get_tokens().consume(confirm, payload)

    audit.intent("execute_lineup", payload)
    result = get_write_client(league).post(payload)
    if result.outcome.value == "unknown":
        audit.unknown("execute_lineup", result.explanation)
    else:
        audit.outcome("execute_lineup", result.status or 0, result.body)

    return WriteOutcome(
        summary=f"{result.outcome.value}: {result.explanation}",
        provenance=provenance(client.cfg.year, resolved),
        outcome=result.outcome.value,
        explanation=result.explanation,
        applied_moves=describe_moves(moves, names) if result.succeeded else [],
    )
