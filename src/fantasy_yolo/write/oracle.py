"""The unauthenticated schema oracle.

ESPN deserializes the request body before it authenticates, so an
UNAUTHENTICATED POST answers 401 for a well-formed body and 400 for a malformed
one. That is a free, side-effect-free check on every payload the builders emit.

NEVER call this with cookies attached. The identical request then executes.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

import requests

WRITE_HOST = "https://lm-api-writes.fantasy.espn.com"
TIMEOUT = 30


class Verdict(StrEnum):
    WELL_FORMED = "well_formed"
    """401 — ESPN parsed the body and then refused us. The shape is acceptable."""

    MALFORMED = "malformed"
    """400 — ESPN rejected the body itself."""

    INCONCLUSIVE = "inconclusive"


def transactions_url(year: int, league_id: int) -> str:
    return (
        f"{WRITE_HOST}/apis/v3/games/ffl/seasons/{year}"
        f"/segments/0/leagues/{league_id}/transactions/"
    )


def verdict_for(status: int) -> Verdict:
    if status == 401:
        return Verdict.WELL_FORMED
    if status == 400:
        return Verdict.MALFORMED
    return Verdict.INCONCLUSIVE


def check_shape(payload: dict[str, Any], year: int, league_id: int) -> tuple[Verdict, str]:
    """Ask ESPN whether a payload parses, without authenticating and without
    changing anything.

    Deliberately takes no credentials parameter: there is no way to call this
    function with cookies, so there is no way for it to execute a transaction.
    """
    response = requests.post(
        transactions_url(year, league_id),
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=TIMEOUT,
    )
    return verdict_for(response.status_code), response.text[:300]
