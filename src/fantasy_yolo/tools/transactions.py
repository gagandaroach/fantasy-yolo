"""Adds, drops and waiver claims (F-04, F-05, F-07, F-08).

Every write is split into preview and execute (J-01). The preview runs the
client-side legality checks ESPN's missing dry run would otherwise have caught,
shows the change in player names, and hands back a single-use code bound to that
exact transaction.
"""

from __future__ import annotations

from fantasy_yolo.context import get_audit, get_client, get_tokens, get_write_client
from fantasy_yolo.models import Response
from fantasy_yolo.policy.legality import check_add_drop, check_bid
from fantasy_yolo.read.weeks import provenance, resolve_week
from fantasy_yolo.registry import Kind, tool
from fantasy_yolo.tools.league import WaiverSystem, detect_waiver_system
from fantasy_yolo.tools.players import resolve_one
from fantasy_yolo.tools.team import to_player_view
from fantasy_yolo.write.payloads import (
    EnvelopeType,
    ExecutionType,
    build_add_drop,
    build_envelope,
    build_waiver_claim,
)

FREE_AGENT_SCAN = 300


class TransactionPreview(Response):
    adding: str | None
    dropping: str | None
    bid: int | None
    problems: list[str]
    confirm: str | None
    """None when the change cannot legally be made."""


class WriteOutcome(Response):
    outcome: str
    explanation: str


def format_problems(problems: list[str]) -> str:
    return "cannot do this: " + "; ".join(problems)


def _context(league: str | None, week: int | None):
    client = get_client(league)
    resolved = resolve_week(week, client.latest_scoring_period())
    roster = [to_player_view(p, resolved) for p in client.my_team().roster]
    return client, resolved, roster


def _free_agents(client, week: int):
    agents = client.league.free_agents(week=week, size=FREE_AGENT_SCAN)
    return [to_player_view(p, week) for p in agents]


def _waiver_settings(client) -> tuple[WaiverSystem, int, int]:
    raw, _ = client.raw(["mSettings"])
    acquisition = raw.get("settings", {}).get("acquisitionSettings", {})
    system = detect_waiver_system(acquisition)
    total = int(acquisition.get("acquisitionBudget") or 0)
    minimum = int(acquisition.get("minimumBid") or 0)
    spent = int(client.my_team().acquisition_budget_spent or 0)
    return system, total - spent, minimum


def _resolve_pair(client, roster, week, add: str | None, drop: str | None):
    adding = resolve_one(add, _free_agents(client, week)) if add else None
    dropping = resolve_one(drop, roster) if drop else None
    return adding, dropping


def _outcome(tool_name: str, payload, league: str | None, client, resolved) -> WriteOutcome:
    audit = get_audit(league)
    audit.intent(tool_name, payload)
    result = get_write_client(league).post(payload)
    if result.outcome.value == "unknown":
        audit.unknown(tool_name, result.explanation)
    else:
        audit.outcome(tool_name, result.status or 0, result.body)
    return WriteOutcome(
        summary=f"{result.outcome.value}: {result.explanation}",
        provenance=provenance(client.cfg.year, resolved),
        outcome=result.outcome.value,
        explanation=result.explanation,
    )


@tool(kind=Kind.WRITE_PREVIEW)
def preview_add_drop(
    add: str | None = None,
    drop: str | None = None,
    week: int | None = None,
    league: str | None = None,
) -> TransactionPreview:
    """Show what adding and/or dropping these players would do.

    Checks what can be checked first — roster space, whether they are actually
    free or actually yours — because ESPN offers no dry run and decides at
    execution. Nothing is written.

    A drop cannot be undone: the player goes to waivers and anyone can claim him.
    """
    client, resolved, roster = _context(league, week)
    adding, dropping = _resolve_pair(client, roster, resolved, add, drop)
    problems = check_add_drop(roster, client.lineup_slot_counts(), adding, dropping)

    confirm = None
    if not problems:
        payload = build_add_drop(
            team_id=client.cfg.team_id,
            member_id=client.creds.member_id(),
            add_player=adding.player_id if adding else None,
            drop_player=dropping.player_id if dropping else None,
            scoring_period=resolved,
        )
        confirm = get_tokens().issue(payload)

    parts = []
    if adding:
        parts.append(f"add {adding.name} ({adding.position}, {adding.pro_team})")
    if dropping:
        parts.append(f"drop {dropping.name} ({dropping.position}, {dropping.pro_team})")
    return TransactionPreview(
        summary=format_problems(problems) if problems else ", ".join(parts),
        provenance=provenance(client.cfg.year, resolved),
        adding=adding.name if adding else None,
        dropping=dropping.name if dropping else None,
        bid=None,
        problems=problems,
        confirm=confirm,
    )


@tool(kind=Kind.WRITE_EXECUTE)
def execute_add_drop(
    confirm: str,
    add: str | None = None,
    drop: str | None = None,
    week: int | None = None,
    league: str | None = None,
) -> WriteOutcome:
    """Add and/or drop a player. This writes to your ESPN account.

    Requires the code from preview_add_drop for this exact change. A drop is
    irreversible. Nothing is ever retried.
    """
    client, resolved, roster = _context(league, week)
    adding, dropping = _resolve_pair(client, roster, resolved, add, drop)
    problems = check_add_drop(roster, client.lineup_slot_counts(), adding, dropping)
    if problems:
        raise ValueError(format_problems(problems))

    payload = build_add_drop(
        team_id=client.cfg.team_id,
        member_id=client.creds.member_id(),
        add_player=adding.player_id if adding else None,
        drop_player=dropping.player_id if dropping else None,
        scoring_period=resolved,
    )
    get_tokens().consume(confirm, payload)
    return _outcome("execute_add_drop", payload, league, client, resolved)


@tool(kind=Kind.WRITE_PREVIEW)
def preview_waiver(
    add: str,
    drop: str | None = None,
    bid: int | None = None,
    week: int | None = None,
    league: str | None = None,
) -> TransactionPreview:
    """Show what a waiver claim would do, and check the bid against your budget.

    In a FAAB league a bid is required; in a rolling-priority league a bid is not
    valid at all. Nothing is written.
    """
    client, resolved, roster = _context(league, week)
    adding, dropping = _resolve_pair(client, roster, resolved, add, drop)
    system, remaining, minimum = _waiver_settings(client)

    problems = check_add_drop(roster, client.lineup_slot_counts(), adding, dropping)
    problems += check_bid(system, bid, remaining, minimum)

    confirm = None
    if not problems and adding is not None:
        payload = build_waiver_claim(
            team_id=client.cfg.team_id,
            member_id=client.creds.member_id(),
            add_player=adding.player_id,
            drop_player=dropping.player_id if dropping else None,
            bid=bid,
            scoring_period=resolved,
        )
        confirm = get_tokens().issue(payload)

    detail = f"claim {adding.name}" if adding else "claim"
    if bid is not None:
        detail += f" for {bid} of {remaining} remaining"
    if dropping:
        detail += f", dropping {dropping.name}"
    return TransactionPreview(
        summary=format_problems(problems) if problems else detail,
        provenance=provenance(client.cfg.year, resolved),
        adding=adding.name if adding else None,
        dropping=dropping.name if dropping else None,
        bid=bid,
        problems=problems,
        confirm=confirm,
    )


@tool(kind=Kind.WRITE_EXECUTE)
def execute_waiver(
    confirm: str,
    add: str,
    drop: str | None = None,
    bid: int | None = None,
    week: int | None = None,
    league: str | None = None,
) -> WriteOutcome:
    """Submit a waiver claim. This writes to your ESPN account.

    Requires the code from preview_waiver for this exact claim. The claim sits
    pending until your league's waiver run — pending is not success. Nothing is
    ever retried.
    """
    client, resolved, roster = _context(league, week)
    adding, dropping = _resolve_pair(client, roster, resolved, add, drop)
    system, remaining, minimum = _waiver_settings(client)
    problems = check_add_drop(roster, client.lineup_slot_counts(), adding, dropping)
    problems += check_bid(system, bid, remaining, minimum)
    if problems:
        raise ValueError(format_problems(problems))

    payload = build_waiver_claim(
        team_id=client.cfg.team_id,
        member_id=client.creds.member_id(),
        add_player=adding.player_id,
        drop_player=dropping.player_id if dropping else None,
        bid=bid,
        scoring_period=resolved,
    )
    get_tokens().consume(confirm, payload)
    return _outcome("execute_waiver", payload, league, client, resolved)


@tool(kind=Kind.WRITE_EXECUTE)
def cancel_waiver(
    confirm: str,
    transaction_id: str,
    week: int | None = None,
    league: str | None = None,
) -> WriteOutcome:
    """Cancel a pending waiver claim. This writes to your ESPN account.

    Take the transaction id from get_pending. Requires a confirmation code from
    preview_cancel_waiver.
    """
    client, resolved, _ = _context(league, week)
    payload = build_envelope(
        EnvelopeType.WAIVER,
        team_id=client.cfg.team_id,
        member_id=client.creds.member_id(),
        items=[],
        scoring_period=resolved,
        execution_type=ExecutionType.CANCEL,
        related_transaction_id=transaction_id,
    )
    get_tokens().consume(confirm, payload)
    return _outcome("cancel_waiver", payload, league, client, resolved)


@tool(kind=Kind.WRITE_PREVIEW)
def preview_cancel_waiver(
    transaction_id: str,
    week: int | None = None,
    league: str | None = None,
) -> TransactionPreview:
    """Show what cancelling a pending claim would do, and hand back a code."""
    client, resolved, _ = _context(league, week)
    payload = build_envelope(
        EnvelopeType.WAIVER,
        team_id=client.cfg.team_id,
        member_id=client.creds.member_id(),
        items=[],
        scoring_period=resolved,
        execution_type=ExecutionType.CANCEL,
        related_transaction_id=transaction_id,
    )
    return TransactionPreview(
        summary=f"cancel pending claim {transaction_id}",
        provenance=provenance(client.cfg.year, resolved),
        adding=None,
        dropping=None,
        bid=None,
        problems=[],
        confirm=get_tokens().issue(payload),
    )
