"""Week resolution (M-13).

scoringPeriodId and matchupPeriodId diverge in the playoffs and roll over
mid-week, so every week-sensitive call resolves once and echoes the answer.
"""

from __future__ import annotations

from datetime import datetime

from fantasy_yolo.models import Provenance

FIRST_WEEK = 1
LAST_WEEK = 18


def resolve_week(requested: int | None, latest: int) -> int:
    if requested is None:
        return latest
    if not FIRST_WEEK <= requested <= LAST_WEEK:
        raise ValueError(f"week must be between {FIRST_WEEK} and {LAST_WEEK}, got {requested}")
    return requested


def provenance(season: int, week: int, from_cache: bool = False) -> Provenance:
    return Provenance(
        season=season,
        week_resolved=week,
        fetched_at=datetime.now().astimezone(),
        from_cache=from_cache,
    )
