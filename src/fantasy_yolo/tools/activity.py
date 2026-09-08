"""League activity and pending transactions (I-01, F-06, G-06).

get_pending is also a prerequisite of the write path: J-09 re-reads pending
transactions immediately before any write, and refuses to submit a duplicate.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from fantasy_yolo.context import get_client
from fantasy_yolo.models import Page, Response
from fantasy_yolo.read.weeks import provenance, resolve_week
from fantasy_yolo.registry import Kind, tool

DEFAULT_LIMIT = 25


class TransactionRow(BaseModel):
    id: str
    type: str
    status: str
    team: str
    players: list[str]
    when: datetime
    scoring_period: int | None
    bid: int | None


class TransactionFeed(Page):
    rows: list[TransactionRow]
    types_present: dict[str, int]


class PendingView(Response):
    counts_by_type: dict[str, int]
    raw_count: int


def build_transaction_rows(
    raw: list[dict[str, Any]],
    team_names: dict[int, str],
    player_names: dict[int, str],
) -> list[TransactionRow]:
    """Parse ESPN's own transaction records.

    Note these echo back exactly the envelope the write path sends — type,
    status, teamId, scoringPeriodId, bidAmount, and items carrying playerId with
    fromLineupSlotId/toLineupSlotId in wire form.
    """
    rows: list[TransactionRow] = []
    for tx in raw:
        team_id = tx.get("teamId")
        players = [
            player_names.get(item.get("playerId"), f"player {item.get('playerId')}")
            for item in tx.get("items") or []
        ]
        bid = tx.get("bidAmount") or 0
        rows.append(
            TransactionRow(
                id=str(tx.get("id", "")),
                type=str(tx.get("type", "UNKNOWN")),
                status=str(tx.get("status", "UNKNOWN")),
                team=team_names.get(team_id, f"team {team_id}"),
                players=players,
                when=datetime.fromtimestamp(int(tx.get("proposedDate", 0)) / 1000.0).astimezone(),
                scoring_period=tx.get("scoringPeriodId"),
                bid=int(bid) if bid else None,
            )
        )
    return rows


def summarise_pending(pending: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(p.get("type", "UNKNOWN")) for p in pending))


@tool(kind=Kind.READ)
def get_transactions(
    limit: int = DEFAULT_LIMIT,
    team: str | None = None,
    type: str | None = None,
    week: int | None = None,
    league: str | None = None,
) -> TransactionFeed:
    """The league's transaction log: drafts, adds, drops, waivers and trades.

    Filter by team, by type (DRAFT, FREEAGENT, WAIVER, ROSTER, TRADE_PROPOSAL) or
    by week. The answer always states which types exist in the league, so an
    empty filtered result is never mistaken for an empty league.
    """
    client = get_client(league)
    resolved = resolve_week(week, client.latest_scoring_period())
    raw, _ = client.raw(["mTransactions2"])
    all_rows = build_transaction_rows(
        raw.get("transactions") or [],
        {t.team_id: t.team_name for t in client.league.teams},
        {p.playerId: p.name for t in client.league.teams for p in t.roster},
    )
    present = dict(Counter(r.type for r in all_rows))

    rows = all_rows
    if team is not None:
        rows = [r for r in rows if team.lower() in r.team.lower()]
    if type is not None:
        rows = [r for r in rows if r.type.upper() == type.upper()]
    if week is not None:
        rows = [r for r in rows if r.scoring_period == resolved]

    rows.sort(key=lambda r: r.when, reverse=True)
    window = rows[:limit]
    return TransactionFeed(
        summary=(
            f"{len(window)} of {len(rows)} matching; league has "
            + ", ".join(f"{n} {kind}" for kind, n in sorted(present.items()))
        ),
        provenance=provenance(client.cfg.year, resolved),
        total=len(rows),
        returned=len(window),
        offset=0,
        rows=window,
        types_present=present,
    )


@tool(kind=Kind.READ)
def get_pending(week: int | None = None, league: str | None = None) -> PendingView:
    """Transactions you have submitted that ESPN has not processed yet.

    Waiver claims awaiting the next run, and trades awaiting a response.
    """
    client = get_client(league)
    resolved = resolve_week(week, client.latest_scoring_period())
    raw, _ = client.raw(["mPendingTransactions"])
    pending = raw.get("pendingTransactions") or []
    counts = summarise_pending(pending)
    return PendingView(
        summary=(
            ", ".join(f"{n} {kind}" for kind, n in sorted(counts.items()))
            if counts
            else "nothing pending"
        ),
        provenance=provenance(client.cfg.year, resolved),
        counts_by_type=counts,
        raw_count=len(pending),
    )
