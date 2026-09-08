"""Interpreting ESPN's transaction responses.

ESPN's own handler makes no distinction between 400 and 409 and reads the rule
out of details[].type. So a 400 must never be reported as "malformed body,
nothing happened" — a rule may well have been broken.

Codes are matched by PREFIX. The real constants ship in _ONE / _PLURAL / _LM
variants, and exact matching breaks on every variant but the one you saw.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class Outcome(StrEnum):
    APPLIED = "applied"
    PENDING = "pending"
    """Accepted and waiting — a waiver claim until the run, a trade until answered."""

    REJECTED = "rejected"
    UNKNOWN = "unknown"
    """Never report this as either success or failure (J-04)."""


PREFIX_EXPLANATIONS: tuple[tuple[str, str], ...] = (
    ("TRAN_ROSTER_LIMIT_EXCEEDED", "your roster is full — drop someone in the same transaction"),
    ("TRAN_ROSTER_POSITION_LIMIT_EXCEEDED", "you are at your league's limit for that position"),
    ("TRAN_ROSTER_SLOT_LIMIT_EXCEEDED", "that lineup slot is already full"),
    ("FAILED_ROSTERLOCK", "the roster is locked — that player's game has started"),
)

STATUS_EXPLANATIONS: dict[int, str] = {
    401: "ESPN rejected your credentials; your espn_s2 cookie has most likely expired",
    403: "ESPN refused this action for this account",
    404: "ESPN did not recognise that league or season",
    415: "ESPN requires a JSON Content-Type on this request",
}


def _codes(body: dict[str, Any]) -> list[str]:
    return [str(d.get("type", "")) for d in (body.get("details") or []) if d.get("type")]


def explain(status: int, body: dict[str, Any]) -> str:
    """A plain-language explanation, never a bare code (J-06)."""
    # Success first. explain() runs on every response including 200s, and
    # falling through to the refusal wording after a write that actually landed
    # is the worst false alarm this codebase can produce: there is no
    # idempotency key, so a user who believes it failed will submit it twice.
    outcome = outcome_for(status, body)
    if outcome is Outcome.APPLIED:
        txn = body.get("id")
        return "applied by ESPN" + (f" (transaction {txn})" if txn else "")
    if outcome is Outcome.PENDING:
        txn = body.get("id")
        return (
            "accepted by ESPN and pending — it has not happened yet, and will be "
            "processed at your league's next waiver run"
            + (f" (transaction {txn})" if txn else "")
        )

    for code in _codes(body):
        for prefix, text in PREFIX_EXPLANATIONS:
            if code.startswith(prefix):
                return text
        return f"ESPN refused this with an unrecognised code: {code}"

    messages = " ".join(str(m) for m in (body.get("messages") or []))
    if "TransactionItems are missing" in messages:
        return "no changes to make — the roster is already in that arrangement"
    if status in STATUS_EXPLANATIONS:
        return STATUS_EXPLANATIONS[status]
    if messages:
        return messages
    return f"ESPN refused this (HTTP {status}) without saying why"


def outcome_for(status: int, body: dict[str, Any]) -> Outcome:
    if status in (401, 403, 404, 415) or 400 <= status < 500:
        return Outcome.REJECTED
    if status != 200:
        return Outcome.UNKNOWN
    state = str(body.get("status", "")).upper()
    if state == "EXECUTED":
        return Outcome.APPLIED
    if state in ("PENDING", "QUEUED"):
        return Outcome.PENDING
    # ESPN sends isPending alongside status; trust it when status is absent or
    # unrecognised rather than calling a real pending claim unknown.
    if body.get("isPending") is True:
        return Outcome.PENDING
    return Outcome.UNKNOWN
