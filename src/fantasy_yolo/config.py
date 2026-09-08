"""Configuration.

League and team are pinned here so nothing can act on a team that isn't yours
(A-04). Several of your own leagues are supported (A-06); acting for someone
else is not (X-05, J-05).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, model_validator

DEFAULT_PATH = Path.home() / ".config" / "fantasy-yolo" / "config.json"


class LeagueConfig(BaseModel):
    name: str
    league_id: int
    team_id: int
    year: int


class Settings(BaseModel):
    leagues: list[LeagueConfig]
    active: str
    write_enabled: bool = False
    credentials_file: Path | None = None

    @model_validator(mode="after")
    def _active_exists(self) -> Settings:
        if self.active not in {league.name for league in self.leagues}:
            raise ValueError(f"active league {self.active!r} is not in leagues")
        return self

    def league(self, name: str | None = None) -> LeagueConfig:
        """Resolve a league by name, defaulting to the active one (A-06)."""
        wanted = name or self.active
        for league in self.leagues:
            if league.name == wanted:
                return league
        options = ", ".join(sorted(league.name for league in self.leagues))
        raise KeyError(f"no league named {wanted!r}; configured: {options}")


def load_settings(path: Path | None = None) -> Settings:
    resolved = path or Path(os.environ.get("FANTASY_YOLO_CONFIG", DEFAULT_PATH))
    if not resolved.exists():
        raise FileNotFoundError(f"no config at {resolved}; see docs/setup.md")
    return Settings.model_validate(json.loads(resolved.read_text()))
