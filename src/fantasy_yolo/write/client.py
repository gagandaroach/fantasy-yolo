"""The transaction POST.

Two rules, both from the platform:

  * Never retry. ESPN offers no idempotency key, so a retried write genuinely
    submits the move a second time (J-04). requests and urllib3 retry by default,
    so retries are disabled explicitly rather than merely not requested.

  * An unknown outcome is unknown. On a timeout or a dropped connection we do not
    know whether the transaction executed. Reporting "failed" invites the user to
    redo a move that already landed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import requests
from requests.adapters import HTTPAdapter

from fantasy_yolo.write.errors import Outcome, explain, outcome_for

WRITE_HOST = "https://lm-api-writes.fantasy.espn.com"
TIMEOUT = 30


@dataclass(frozen=True)
class WriteResult:
    outcome: Outcome
    status: int | None
    body: dict[str, Any]
    explanation: str
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        """Only APPLIED is success. PENDING is accepted-but-not-done; UNKNOWN is
        neither, and must never be presented as either."""
        return self.outcome is Outcome.APPLIED


def build_session() -> requests.Session:
    session = requests.Session()
    no_retries = HTTPAdapter(max_retries=0)
    session.mount("https://", no_retries)
    session.mount("http://", no_retries)
    return session


class WriteClient:
    def __init__(self, year: int, league_id: int, cookies: dict[str, str]) -> None:
        self.year = year
        self.league_id = league_id
        self.cookies = cookies
        self.session = build_session()

    @staticmethod
    def url(year: int, league_id: int) -> str:
        return (
            f"{WRITE_HOST}/apis/v3/games/ffl/seasons/{year}"
            f"/segments/0/leagues/{league_id}/transactions/"
        )

    def post(self, payload: dict[str, Any]) -> WriteResult:
        """Submit one transaction. Exactly once, or not at all."""
        try:
            response = self.session.post(
                self.url(self.year, self.league_id),
                json=payload,
                headers={"Content-Type": "application/json"},
                cookies=self.cookies,
                timeout=TIMEOUT,
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            return WriteResult(
                outcome=Outcome.UNKNOWN,
                status=None,
                body={},
                explanation=(
                    f"the request did not complete ({exc.__class__.__name__}: {exc}), so we do "
                    "not know whether ESPN applied it. Nothing was retried. "
                    "Re-read your roster and pending transactions before trying again."
                ),
                payload=payload,
            )

        try:
            body = response.json()
        except ValueError:
            body = {}

        return WriteResult(
            outcome=outcome_for(response.status_code, body),
            status=response.status_code,
            body=body,
            explanation=explain(response.status_code, body),
            payload=payload,
        )
