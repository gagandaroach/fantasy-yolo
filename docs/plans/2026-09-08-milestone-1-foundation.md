# Milestone 1: Foundation & Read Path — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A working `fy` CLI and MCP server that answer "what is my roster" and "who am I playing" against a real ESPN league, sharing one tool definition.

**Architecture:** Plain typed functions in `tools/` are registered by a decorator we own. `cli.py` and `mcp/server.py` both read that registry, so neither is the source of truth and they cannot drift. Reads go through `espn-api` plus raw fetches for the fields it doesn't parse. No write code exists in the repo at the end of this milestone.

**Tech Stack:** Python 3.13, `uv`, `espn-api` 0.46, `mcp` 2.2 (`MCPServer`), `typer`, `pydantic` v2, `pytest`, `ruff`.

**Spec:** [`docs/design.md`](../design.md) — read §3 (Architecture), §4 (Reads), §5 (Response contract) before starting.

## Global Constraints

- **Python 3.13.** Not 3.14 — the dependency tree does not resolve there yet.
- **`mcp` 2.x API.** `from mcp.server.mcpserver import MCPServer`. `FastMCP` does not exist in 2.x. `ToolAnnotations` fields are snake_case: `read_only_hint`, `destructive_hint`, `idempotent_hint`, `open_world_hint`.
- **`write/` imports nothing** from `policy/`, `tools/`, `cli`, or `mcp/` (M-08). Not exercised this milestone; the boundary is established now.
- **No write code.** No module may import `lm-api-writes`, and no tool may be registered with a write `Kind` (§13 build order).
- **Credentials never logged.** `espn_s2` and `SWID` are redacted from every log line, error and response (J-03).
- **Every response carries** `season`, `week_resolved`, `fetched_at` (M-13), and every list carries `total`/`returned` (M-14).
- **Tests run with no credentials and no network** (M-03).

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`, `src/fantasy_yolo/__init__.py`, `tests/test_smoke.py`, `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: nothing
- Produces: an installed `fantasy_yolo` package; `uv run pytest` and `uv run ruff check` both green.

- [ ] **Step 1: Create the project**

```bash
cd /home/gagan/repos/fantasy-yolo
uv init --lib --name fantasy-yolo --python 3.13
uv add espn-api "mcp>=2.2,<3" typer pydantic
uv add --dev pytest ruff
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_smoke.py
def test_package_imports():
    import fantasy_yolo
    assert fantasy_yolo.__version__
```

- [ ] **Step 3: Run it and watch it fail**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: FAIL — `AttributeError: module 'fantasy_yolo' has no attribute '__version__'`

- [ ] **Step 4: Make it pass**

```python
# src/fantasy_yolo/__init__.py
__version__ = "0.1.0"
```

- [ ] **Step 5: Run tests and lint**

Run: `uv run pytest -v && uv run ruff check .`
Expected: 1 passed, no lint errors.

- [ ] **Step 6: Add CI (M-06)**

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.13"
      - run: uv sync --all-extras --dev
      - run: uv run ruff check .
      - run: uv run pytest -v
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "Add project scaffold and CI"
```

---

### Task 2: The tool registry

This is the single source of truth for both interfaces (M-18). `kind` drives MCP annotations (J-08), CLI confirmation, and read-only filtering (J-02).

**Files:**
- Create: `src/fantasy_yolo/registry.py`, `tests/test_registry.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `class Kind(StrEnum): READ, WRITE_PREVIEW, WRITE_EXECUTE`
  - `@dataclass(frozen=True) class ToolSpec: name: str, fn: Callable, kind: Kind, description: str`
  - `def tool(kind: Kind) -> Callable[[F], F]` — decorator, registers and returns the function unchanged
  - `def registered(include_writes: bool = True) -> list[ToolSpec]`
  - `def clear_registry() -> None` — test helper

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_registry.py
import pytest
from fantasy_yolo.registry import Kind, tool, registered, clear_registry


@pytest.fixture(autouse=True)
def _clean():
    clear_registry()
    yield
    clear_registry()


def test_decorator_returns_function_unchanged():
    @tool(kind=Kind.READ)
    def get_thing(n: int) -> int:
        """Docstring becomes the description."""
        return n * 2

    assert get_thing(3) == 6


def test_registers_name_kind_and_description():
    @tool(kind=Kind.READ)
    def get_thing() -> None:
        """Docstring becomes the description."""

    (spec,) = registered()
    assert spec.name == "get_thing"
    assert spec.kind is Kind.READ
    assert spec.description == "Docstring becomes the description."


def test_read_only_mode_excludes_write_tools():
    @tool(kind=Kind.READ)
    def get_thing() -> None:
        """r"""

    @tool(kind=Kind.WRITE_EXECUTE)
    def execute_thing() -> None:
        """w"""

    assert {s.name for s in registered()} == {"get_thing", "execute_thing"}
    assert {s.name for s in registered(include_writes=False)} == {"get_thing"}


def test_duplicate_name_is_an_error():
    @tool(kind=Kind.READ)
    def get_thing() -> None:
        """r"""

    with pytest.raises(ValueError, match="already registered"):

        @tool(kind=Kind.READ)
        def get_thing() -> None:  # noqa: F811
            """r"""


def test_missing_docstring_is_an_error():
    with pytest.raises(ValueError, match="docstring"):

        @tool(kind=Kind.READ)
        def get_thing() -> None:
            pass
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest tests/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fantasy_yolo.registry'`

- [ ] **Step 3: Implement**

```python
# src/fantasy_yolo/registry.py
"""Single source of truth for tools exposed over MCP and the CLI (M-18)."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])


class Kind(StrEnum):
    """What a tool does. Drives MCP annotations, CLI confirmation, J-02 filtering."""

    READ = "read"
    WRITE_PREVIEW = "write_preview"
    WRITE_EXECUTE = "write_execute"

    @property
    def is_write(self) -> bool:
        return self is not Kind.READ


@dataclass(frozen=True)
class ToolSpec:
    name: str
    fn: Callable[..., object]
    kind: Kind
    description: str


_REGISTRY: dict[str, ToolSpec] = {}


def tool(kind: Kind) -> Callable[[F], F]:
    """Register a function as a tool. Returns it unchanged so it stays directly callable."""

    def decorate(fn: F) -> F:
        name = fn.__name__
        if name in _REGISTRY:
            raise ValueError(f"tool {name!r} is already registered")
        doc = inspect.getdoc(fn)
        if not doc:
            raise ValueError(f"tool {name!r} needs a docstring; it becomes the description")
        _REGISTRY[name] = ToolSpec(name=name, fn=fn, kind=kind, description=doc)
        return fn

    return decorate


def registered(include_writes: bool = True) -> list[ToolSpec]:
    """Registered tools, sorted by name. J-02 read-only mode passes include_writes=False."""
    specs = sorted(_REGISTRY.values(), key=lambda s: s.name)
    if include_writes:
        return specs
    return [s for s in specs if not s.kind.is_write]


def clear_registry() -> None:
    """Test helper."""
    _REGISTRY.clear()
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_registry.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Add tool registry (M-18, J-02, J-08)"
```

---

### Task 3: Configuration

**Files:**
- Create: `src/fantasy_yolo/config.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `class LeagueConfig(BaseModel): name: str, league_id: int, team_id: int, year: int`
  - `class Settings(BaseModel): leagues: list[LeagueConfig], active: str, write_enabled: bool = False, credentials_file: Path | None = None`
  - `Settings.league(name: str | None = None) -> LeagueConfig` — resolves the active league (A-06)
  - `def load_settings(path: Path | None = None) -> Settings` — reads `FANTASY_YOLO_CONFIG` or `~/.config/fantasy-yolo/config.json`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config.py
import json
import pytest
from fantasy_yolo.config import LeagueConfig, Settings, load_settings


def _settings(**kw):
    base = dict(
        leagues=[
            LeagueConfig(name="office", league_id=1, team_id=2, year=2026),
            LeagueConfig(name="money", league_id=3, team_id=4, year=2026),
        ],
        active="office",
    )
    return Settings(**{**base, **kw})


def test_writes_are_disabled_by_default():
    assert _settings().write_enabled is False


def test_resolves_the_active_league():
    assert _settings().league().name == "office"


def test_resolves_a_named_league(): # A-06
    assert _settings().league("money").league_id == 3


def test_unknown_league_names_the_options():
    with pytest.raises(KeyError, match="money"):
        _settings().league("nope")


def test_active_must_exist():
    with pytest.raises(ValueError, match="active league"):
        _settings(active="ghost")


def test_load_settings_reads_json(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({
        "leagues": [{"name": "office", "league_id": 1, "team_id": 2, "year": 2026}],
        "active": "office",
    }))
    assert load_settings(p).league().team_id == 2
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fantasy_yolo.config'`

- [ ] **Step 3: Implement**

```python
# src/fantasy_yolo/config.py
"""Configuration. Team and league are pinned here so nothing can act elsewhere (A-04)."""

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
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_config.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Add configuration with league pinning (A-04, A-06)"
```

---

### Task 4: Credentials and redaction

**Files:**
- Create: `src/fantasy_yolo/creds.py`, `tests/test_creds.py`

**Interfaces:**
- Consumes: `fantasy_yolo.config.Settings`
- Produces:
  - `class Credentials(BaseModel): espn_s2: str, swid: str`
  - `Credentials.cookies() -> dict[str, str]` — `{"espn_s2": ..., "SWID": ...}`, uppercase `SWID` per §14.5
  - `Credentials.member_id() -> str` — braced SWID
  - `Credentials.captured_at() -> datetime | None` — file mtime, for A-05
  - `def load_credentials(path: Path) -> Credentials`
  - `def redact(text: str, creds: Credentials | None) -> str` (J-03)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_creds.py
import json
import pytest
from fantasy_yolo.creds import Credentials, load_credentials, redact

CREDS = Credentials(espn_s2="SECRET_S2_VALUE", swid="{ABC-123}")


def test_cookies_use_uppercase_swid():
    assert CREDS.cookies() == {"espn_s2": "SECRET_S2_VALUE", "SWID": "{ABC-123}"}


def test_member_id_keeps_the_braces():
    assert CREDS.member_id() == "{ABC-123}"


def test_member_id_adds_missing_braces():
    assert Credentials(espn_s2="x", swid="ABC-123").member_id() == "{ABC-123}"


def test_redact_removes_the_session_cookie():
    assert "SECRET_S2_VALUE" not in redact("cookie=SECRET_S2_VALUE bad", CREDS)


def test_redact_removes_the_swid():
    assert "ABC-123" not in redact("swid {ABC-123} here", CREDS)


def test_redact_is_a_noop_without_credentials():
    assert redact("plain text", None) == "plain text"


def test_load_credentials_rejects_a_world_readable_file(tmp_path):
    p = tmp_path / "creds.json"
    p.write_text(json.dumps({"espn_s2": "a", "swid": "{b}"}))
    p.chmod(0o644)
    with pytest.raises(PermissionError, match="0600"):
        load_credentials(p)


def test_load_credentials_reads_a_private_file(tmp_path):
    p = tmp_path / "creds.json"
    p.write_text(json.dumps({"espn_s2": "a", "swid": "{b}"}))
    p.chmod(0o600)
    assert load_credentials(p).espn_s2 == "a"
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest tests/test_creds.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fantasy_yolo.creds'`

- [ ] **Step 3: Implement**

```python
# src/fantasy_yolo/creds.py
"""Credential loading and redaction.

espn_s2 is a full ESPN/Disney session cookie, not a scoped token. Leaking it is
account compromise, so it is read from a file (M-09) and scrubbed from every
log line, error and response (J-03).
"""

from __future__ import annotations

import json
import stat
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

REDACTED = "[redacted]"


class Credentials(BaseModel):
    espn_s2: str
    swid: str

    def cookies(self) -> dict[str, str]:
        """Uppercase SWID — repos disagree and §14.5 standardises on it."""
        return {"espn_s2": self.espn_s2, "SWID": self.swid}

    def member_id(self) -> str:
        """The braced SWID, as the write envelope's memberId expects."""
        value = self.swid
        if not value.startswith("{"):
            value = "{" + value
        if not value.endswith("}"):
            value = value + "}"
        return value

    def secrets(self) -> list[str]:
        return [self.espn_s2, self.swid, self.swid.strip("{}")]


def load_credentials(path: Path) -> Credentials:
    mode = path.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise PermissionError(f"{path} is group/world readable; chmod 0600 it")
    return Credentials.model_validate(json.loads(path.read_text()))


def captured_at(path: Path) -> datetime:
    """When the user last supplied cookies. ESPN publishes no expiry to read (A-05)."""
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone()


def redact(text: str, creds: Credentials | None) -> str:
    """Scrub credentials from any string leaving the process (J-03)."""
    if creds is None:
        return text
    for secret in creds.secrets():
        if secret:
            text = text.replace(secret, REDACTED)
    return text
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_creds.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Add credential loading and redaction (M-09, J-03, A-05)"
```

---

### Task 5: Response contract

Every tool returns one of these. Never a serialized `espn-api` object — `Player` carries a nested per-week stats dict and a naive roster dump is tens of kilobytes (M-14).

**Files:**
- Create: `src/fantasy_yolo/models.py`, `tests/test_models.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `class Provenance(BaseModel): season: int, week_resolved: int, fetched_at: datetime, from_cache: bool = False`
  - `class Response(BaseModel): summary: str, provenance: Provenance`
  - `class Page(Response): total: int, returned: int, offset: int` with `truncated` property
  - `class PlayerView(BaseModel)` — the flat player shape
  - `class RosterView(Response)` — starters, bench, counts

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_models.py
from datetime import datetime
from fantasy_yolo.models import Page, PlayerView, Provenance, Response

PROV = Provenance(season=2026, week_resolved=1, fetched_at=datetime(2026, 9, 8, 12, 0))


def test_every_response_carries_provenance():  # M-13
    r = Response(summary="ok", provenance=PROV)
    assert r.provenance.season == 2026
    assert r.provenance.week_resolved == 1


def test_page_reports_truncation():  # M-14
    p = Page(summary="s", provenance=PROV, total=200, returned=50, offset=0)
    assert p.truncated is True


def test_page_is_not_truncated_when_complete():
    p = Page(summary="s", provenance=PROV, total=50, returned=50, offset=0)
    assert p.truncated is False


def test_player_view_stays_flat():
    p = PlayerView(
        player_id=1, name="A Player", position="RB", slot="RB",
        pro_team="KC", opponent="LV", projected=12.5, injury_status="ACTIVE",
    )
    assert set(p.model_dump()) == {
        "player_id", "name", "position", "slot", "pro_team",
        "opponent", "projected", "injury_status",
    }
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fantasy_yolo.models'`

- [ ] **Step 3: Implement**

```python
# src/fantasy_yolo/models.py
"""Response contract (M-13, M-14).

Small, flat, explicitly listed fields plus a one-line human summary. The CLI
renders these as tables; the MCP server returns them structured.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Provenance(BaseModel):
    """So "this week" can never mean two different weeks (M-13)."""

    season: int
    week_resolved: int
    fetched_at: datetime
    from_cache: bool = False


class Response(BaseModel):
    summary: str
    provenance: Provenance


class Page(Response):
    """Truncation is stated, never silent (M-14)."""

    total: int
    returned: int
    offset: int

    @property
    def truncated(self) -> bool:
        return self.offset + self.returned < self.total


class PlayerView(BaseModel):
    player_id: int
    name: str
    position: str
    slot: str
    pro_team: str
    opponent: str
    projected: float
    injury_status: str


class RosterView(Response):
    starters: list[PlayerView]
    bench: list[PlayerView]
    counts_by_position: dict[str, int]
    open_roster_spots: int
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_models.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Add response contract (M-13, M-14)"
```

---

### Task 6: ESPN read client

Wraps `espn-api`, and adds the raw fetches it does not parse (§4.1).

**Files:**
- Create: `src/fantasy_yolo/read/__init__.py`, `src/fantasy_yolo/read/client.py`, `tests/test_read_client.py`, `tests/fixtures/mSettings.json`

**Interfaces:**
- Consumes: `config.LeagueConfig`, `creds.Credentials`
- Produces:
  - `class ReadClient` with `league` (an `espn_api.football.League`), `latest_scoring_period() -> int`, `lineup_slot_counts() -> dict[int, int]`, `role_is_authenticated() -> bool`
  - `READ_HOST = "https://lm-api-reads.fantasy.espn.com"`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_read_client.py
import pytest
from fantasy_yolo.read.client import ReadClient, slot_counts_from_settings


def test_slot_counts_come_from_the_raw_dict_keyed_by_slot_id():
    """Never Settings.position_slot_counts — it zips labels against counts and misaligns (§4.1)."""
    raw = {"settings": {"rosterSettings": {"lineupSlotCounts": {"0": 1, "2": 2, "20": 6}}}}
    assert slot_counts_from_settings(raw) == {0: 1, 2: 2, 20: 6}


def test_slot_counts_reject_missing_settings():
    with pytest.raises(KeyError, match="lineupSlotCounts"):
        slot_counts_from_settings({"settings": {}})


def test_read_client_refuses_a_write_host():
    with pytest.raises(ValueError, match="lm-api-writes"):
        ReadClient.assert_read_host("https://lm-api-writes.fantasy.espn.com/x")


def test_read_client_accepts_the_read_host():
    ReadClient.assert_read_host("https://lm-api-reads.fantasy.espn.com/x")


def test_role_header_none_means_unauthenticated():  # A-02
    assert ReadClient.role_is_authenticated({"X-Fantasy-Role": "NONE"}) is False
    assert ReadClient.role_is_authenticated({"X-Fantasy-Role": "MEMBER"}) is True
    assert ReadClient.role_is_authenticated({}) is False
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest tests/test_read_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fantasy_yolo.read'`

- [ ] **Step 3: Implement**

```python
# src/fantasy_yolo/read/client.py
"""Reads via espn-api, plus the raw fetches it does not parse (§4.1)."""

from __future__ import annotations

from typing import Any, Mapping

import requests
from espn_api.football import League

from fantasy_yolo.config import LeagueConfig
from fantasy_yolo.creds import Credentials

READ_HOST = "https://lm-api-reads.fantasy.espn.com"
WRITE_HOST = "lm-api-writes"


def slot_counts_from_settings(raw: Mapping[str, Any]) -> dict[int, int]:
    """Raw lineupSlotCounts keyed by slot id.

    Never use football's Settings.position_slot_counts: it positionally zips
    list(POSITION_MAP.values())[:n] against lineupSlotCounts.values(), so the
    labels and counts silently misalign (§4.1).
    """
    counts = raw["settings"]["rosterSettings"]["lineupSlotCounts"]
    return {int(slot): int(n) for slot, n in counts.items()}


class ReadClient:
    def __init__(self, cfg: LeagueConfig, creds: Credentials) -> None:
        self.cfg = cfg
        self.creds = creds
        self.league = League(
            league_id=cfg.league_id,
            year=cfg.year,
            espn_s2=creds.espn_s2,
            swid=creds.swid,
        )

    @staticmethod
    def assert_read_host(url: str) -> None:
        """Host choice is not a safety barrier, but this catches an obvious mistake (§2)."""
        if WRITE_HOST in url:
            raise ValueError(f"read client refuses the write host: {url}")

    @staticmethod
    def role_is_authenticated(headers: Mapping[str, str]) -> bool:
        """X-Fantasy-Role reads NONE when unauthenticated — a free liveness canary (A-02)."""
        return headers.get("X-Fantasy-Role", "NONE") != "NONE"

    def _endpoint(self) -> str:
        return (
            f"{READ_HOST}/apis/v3/games/ffl/seasons/{self.cfg.year}"
            f"/segments/0/leagues/{self.cfg.league_id}"
        )

    def raw(self, views: list[str]) -> tuple[dict[str, Any], Mapping[str, str]]:
        url = self._endpoint()
        self.assert_read_host(url)
        r = requests.get(url, params=[("view", v) for v in views],
                         cookies=self.creds.cookies(), timeout=30)
        r.raise_for_status()
        return r.json(), r.headers

    def latest_scoring_period(self) -> int:
        """espn-api never parses league.status.latestScoringPeriod (§4.1)."""
        data, _ = self.raw(["mStatus"])
        return int(data["status"]["latestScoringPeriod"])

    def lineup_slot_counts(self) -> dict[int, int]:
        data, _ = self.raw(["mSettings"])
        return slot_counts_from_settings(data)
```

```python
# src/fantasy_yolo/read/__init__.py
from fantasy_yolo.read.client import ReadClient

__all__ = ["ReadClient"]
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_read_client.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Add ESPN read client with raw fetches espn-api misses"
```

---

### Task 7: Week resolution

**Files:**
- Create: `src/fantasy_yolo/read/weeks.py`, `tests/test_weeks.py`

**Interfaces:**
- Consumes: `read.client.ReadClient`
- Produces: `def resolve_week(requested: int | None, latest: int) -> int` and `def provenance(season, week, from_cache=False) -> Provenance`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_weeks.py
import pytest
from fantasy_yolo.read.weeks import resolve_week


def test_none_resolves_to_the_latest_scoring_period():  # M-13
    assert resolve_week(None, latest=3) == 3


def test_an_explicit_week_is_honoured():
    assert resolve_week(5, latest=3) == 5


def test_week_zero_is_rejected():
    with pytest.raises(ValueError, match="between 1 and 18"):
        resolve_week(0, latest=3)


def test_week_past_the_season_is_rejected():
    with pytest.raises(ValueError, match="between 1 and 18"):
        resolve_week(19, latest=3)
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest tests/test_weeks.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/fantasy_yolo/read/weeks.py
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
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_weeks.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Add week resolution (M-13)"
```

---

### Task 8: The first two tools

**Files:**
- Create: `src/fantasy_yolo/tools/__init__.py`, `src/fantasy_yolo/tools/team.py`, `src/fantasy_yolo/context.py`, `tests/test_tools_team.py`

**Interfaces:**
- Consumes: registry, models, read client, weeks
- Produces:
  - `context.get_client(league: str | None) -> ReadClient` — resolves settings, creds, and the pinned team
  - `tools.team.get_roster(week: int | None = None, league: str | None = None) -> RosterView` (B-01, B-02, B-08)
  - `tools.team.get_matchup(week: int | None = None, league: str | None = None) -> MatchupView` (C-01, C-02)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_tools_team.py
"""Tools are plain functions, so they test without a server or a network (M-03)."""
import pytest
from fantasy_yolo.models import PlayerView
from fantasy_yolo.registry import Kind, registered
from fantasy_yolo.tools.team import build_roster_view, split_starters


BENCH_SLOT = 20


def _p(name, slot):
    return PlayerView(player_id=1, name=name, position="RB", slot=slot,
                      pro_team="KC", opponent="LV", projected=1.0,
                      injury_status="ACTIVE")


def test_starters_and_bench_are_split():  # B-01
    starters, bench = split_starters([_p("A", "RB"), _p("B", "BE"), _p("C", "IR")])
    assert [p.name for p in starters] == ["A"]
    assert [p.name for p in bench] == ["B", "C"]


def test_roster_view_counts_by_position():  # B-08
    view = build_roster_view(
        players=[_p("A", "RB"), _p("B", "BE")],
        slot_counts={2: 2, BENCH_SLOT: 6},
        season=2026, week=1,
    )
    assert view.counts_by_position["RB"] == 2


def test_roster_view_reports_open_spots():  # B-08
    view = build_roster_view(
        players=[_p("A", "RB")], slot_counts={2: 2, BENCH_SLOT: 6},
        season=2026, week=1,
    )
    assert view.open_roster_spots == 7


def test_roster_summary_is_one_line():  # M-14
    view = build_roster_view(
        players=[_p("A", "RB")], slot_counts={2: 2, BENCH_SLOT: 6},
        season=2026, week=1,
    )
    assert "\n" not in view.summary


def test_tools_are_registered_as_reads():  # J-08
    import fantasy_yolo.tools  # noqa: F401  (import registers them)
    names = {s.name: s.kind for s in registered()}
    assert names["get_roster"] is Kind.READ
    assert names["get_matchup"] is Kind.READ


def test_no_write_tools_exist_yet():  # §13 build order
    import fantasy_yolo.tools  # noqa: F401
    assert registered(include_writes=False) == registered()
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest tests/test_tools_team.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fantasy_yolo.tools'`

- [ ] **Step 3: Implement the pure helpers and the tools**

```python
# src/fantasy_yolo/tools/team.py
"""My-team reads. Pure helpers are separated so they test without a network (M-03)."""

from __future__ import annotations

from collections import Counter

from fantasy_yolo.context import get_client
from fantasy_yolo.models import PlayerView, Response, RosterView
from fantasy_yolo.read.weeks import provenance, resolve_week
from fantasy_yolo.registry import Kind, tool

BENCH_SLOTS = {"BE", "IR"}


def split_starters(players: list[PlayerView]) -> tuple[list[PlayerView], list[PlayerView]]:
    """B-01 shows starters and bench separately."""
    starters = [p for p in players if p.slot not in BENCH_SLOTS]
    bench = [p for p in players if p.slot in BENCH_SLOTS]
    return starters, bench


def build_roster_view(
    players: list[PlayerView], slot_counts: dict[int, int], season: int, week: int
) -> RosterView:
    starters, bench = split_starters(players)
    counts = Counter(p.position for p in players)
    capacity = sum(slot_counts.values())
    return RosterView(
        summary=(
            f"{len(starters)} starters, {len(bench)} bench, "
            f"{capacity - len(players)} open of {capacity}"
        ),
        provenance=provenance(season, week),
        starters=starters,
        bench=bench,
        counts_by_position=dict(counts),
        open_roster_spots=capacity - len(players),
    )


class MatchupView(Response):
    opponent: str
    my_projected: float
    their_projected: float


@tool(kind=Kind.READ)
def get_roster(week: int | None = None, league: str | None = None) -> RosterView:
    """Your roster with lineup slots, opponents, projections and injury designations.

    Injury designations are exactly what ESPN reports. There is no timestamp and
    no news text behind them (B-02).
    """
    client = get_client(league)
    resolved = resolve_week(week, client.latest_scoring_period())
    team = client.league.teams[0]
    for candidate in client.league.teams:
        if candidate.team_id == client.cfg.team_id:
            team = candidate
            break
    players = [
        PlayerView(
            player_id=p.playerId,
            name=p.name,
            position=p.position,
            slot=p.lineupSlot,
            pro_team=p.proTeam,
            opponent=getattr(p, "pro_opponent", "") or "",
            projected=float(getattr(p, "projected_points", 0.0) or 0.0),
            injury_status=getattr(p, "injuryStatus", "") or "ACTIVE",
        )
        for p in team.roster
    ]
    return build_roster_view(players, client.lineup_slot_counts(), client.cfg.year, resolved)


@tool(kind=Kind.READ)
def get_matchup(week: int | None = None, league: str | None = None) -> MatchupView:
    """Who you are playing this week and the projected score for both sides."""
    client = get_client(league)
    resolved = resolve_week(week, client.latest_scoring_period())
    for box in client.league.box_scores(resolved):
        if box.home_team.team_id == client.cfg.team_id:
            mine, theirs = box.home_projected, box.away_projected
            opponent = box.away_team.team_name
            break
        if box.away_team.team_id == client.cfg.team_id:
            mine, theirs = box.away_projected, box.home_projected
            opponent = box.home_team.team_name
            break
    else:
        raise LookupError(f"no matchup for team {client.cfg.team_id} in week {resolved}")
    return MatchupView(
        summary=f"vs {opponent}: {mine:.1f} projected to {theirs:.1f}",
        provenance=provenance(client.cfg.year, resolved),
        opponent=opponent,
        my_projected=mine,
        their_projected=theirs,
    )
```

```python
# src/fantasy_yolo/tools/__init__.py
"""Importing this package registers every tool."""

from fantasy_yolo.tools import team  # noqa: F401

__all__ = ["team"]
```

```python
# src/fantasy_yolo/context.py
"""Resolves settings and credentials into a client."""

from __future__ import annotations

from functools import lru_cache

from fantasy_yolo.config import load_settings
from fantasy_yolo.creds import load_credentials
from fantasy_yolo.read.client import ReadClient


@lru_cache(maxsize=8)
def get_client(league: str | None = None) -> ReadClient:
    """Session-scoped cache (§10). Never used for live scoring or post-write read-back."""
    settings = load_settings()
    if settings.credentials_file is None:
        raise FileNotFoundError("credentials_file is not set in config; see docs/setup.md")
    return ReadClient(settings.league(league), load_credentials(settings.credentials_file))
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_tools_team.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Add get_roster and get_matchup (B-01, B-02, B-08, C-01, C-02)"
```

---

### Task 9: The dual interface

Both frontends read the registry. Neither is the source of truth (M-18).

**Files:**
- Create: `src/fantasy_yolo/cli.py`, `src/fantasy_yolo/mcp/__init__.py`, `src/fantasy_yolo/mcp/server.py`, `tests/test_interfaces.py`
- Modify: `pyproject.toml` (add `[project.scripts]`)

**Interfaces:**
- Consumes: `registry.registered`, `tools`
- Produces: `fy` console script; `def build_server(include_writes: bool) -> MCPServer`; `def build_cli() -> typer.Typer`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_interfaces.py
from mcp.types import ToolAnnotations
from fantasy_yolo.mcp.server import annotations_for, build_server
from fantasy_yolo.cli import build_cli
from fantasy_yolo.registry import Kind, registered


def test_read_tools_are_annotated_read_only():  # J-08
    a = annotations_for(Kind.READ)
    assert a.read_only_hint is True
    assert a.destructive_hint is False


def test_execute_tools_are_annotated_destructive():  # J-08
    a = annotations_for(Kind.WRITE_EXECUTE)
    assert a.read_only_hint is False
    assert a.destructive_hint is True


def test_preview_tools_are_read_only():  # §3.1 — preview and execute are separate tools
    assert annotations_for(Kind.WRITE_PREVIEW).read_only_hint is True


def test_server_registers_every_tool():
    import fantasy_yolo.tools  # noqa: F401
    server = build_server(include_writes=True)
    assert {t.name for t in server._tool_manager.list_tools()} >= {"get_roster", "get_matchup"}


def test_cli_exposes_a_command_per_tool():  # M-18
    import fantasy_yolo.tools  # noqa: F401
    names = {c.name for c in build_cli().registered_commands}
    assert {s.name.replace("_", "-") for s in registered()} <= names
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest tests/test_interfaces.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fantasy_yolo.mcp'`

- [ ] **Step 3: Implement the MCP server**

```python
# src/fantasy_yolo/mcp/server.py
"""MCP frontend. Reads the registry; is not the source of truth (M-18)."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

import fantasy_yolo.tools  # noqa: F401  (registers tools)
from fantasy_yolo.config import load_settings
from fantasy_yolo.registry import Kind, registered

INSTRUCTIONS = """\
Read and write one ESPN Fantasy Football team on the user's behalf.

What this server does NOT have, and you must not infer (M-15):
- No projections beyond ESPN's own number. There is no model here.
- No injury news, no news feed, no reporter text.
- No timestamps on injury designations. ESPN reports a status word and nothing
  else, so never describe how recent it is or narrate a recovery.
- No ranking of players on merit. The user decides who is better.

Every response states the season, the week it resolved, and when it was fetched.
Report those rather than assuming which week the user means.
"""


def annotations_for(kind: Kind) -> ToolAnnotations:
    """J-08. Note preview is read-only and execute is destructive, which is why
    they must be separate tools — one tool cannot carry both hints."""
    return ToolAnnotations(
        read_only_hint=kind is not Kind.WRITE_EXECUTE,
        destructive_hint=kind is Kind.WRITE_EXECUTE,
        idempotent_hint=False,
        open_world_hint=True,
    )


def build_server(include_writes: bool) -> MCPServer:
    server = MCPServer(name="fantasy-yolo", instructions=INSTRUCTIONS)
    for spec in registered(include_writes=include_writes):
        server.tool(
            name=spec.name,
            description=spec.description,
            annotations=annotations_for(spec.kind),
        )(spec.fn)
    return server


def main() -> None:
    # J-02: when writes are disabled the tools are not registered at all, so a
    # model cannot see or offer them.
    try:
        write_enabled = load_settings().write_enabled
    except FileNotFoundError:
        write_enabled = False
    build_server(include_writes=write_enabled).run(transport="stdio")
```

```python
# src/fantasy_yolo/mcp/__init__.py
from fantasy_yolo.mcp.server import build_server, main

__all__ = ["build_server", "main"]
```

- [ ] **Step 4: Implement the CLI**

```python
# src/fantasy_yolo/cli.py
"""CLI frontend. Same registry, so the interfaces cannot drift (M-18)."""

from __future__ import annotations

import json

import typer
from pydantic import BaseModel

import fantasy_yolo.tools  # noqa: F401  (registers tools)
from fantasy_yolo.registry import Kind, registered


def _render(result: object) -> str:
    if isinstance(result, BaseModel):
        return json.dumps(result.model_dump(mode="json"), indent=2, default=str)
    return str(result)


def build_cli() -> typer.Typer:
    app = typer.Typer(help="Talk to your ESPN fantasy football team.", no_args_is_help=True)
    for spec in registered():
        def make(spec=spec):
            def command(*args, **kwargs):
                if spec.kind is Kind.WRITE_EXECUTE and not kwargs.pop("yes", False):
                    typer.confirm("This writes to your ESPN account. Continue?", abort=True)
                typer.echo(_render(spec.fn(*args, **kwargs)))
            command.__name__ = spec.name
            command.__doc__ = spec.description
            command.__signature__ = __import__("inspect").signature(spec.fn)
            return command

        app.command(name=spec.name.replace("_", "-"), help=spec.description)(make())
    return app


def main() -> None:
    build_cli()()
```

- [ ] **Step 5: Register the entry points**

```toml
# pyproject.toml — append
[project.scripts]
fy = "fantasy_yolo.cli:main"
fantasy-yolo-mcp = "fantasy_yolo.mcp.server:main"
```

- [ ] **Step 6: Run the whole suite**

Run: `uv run pytest -v && uv run ruff check .`
Expected: all green.

- [ ] **Step 7: Verify the CLI is real**

Run: `uv run fy --help`
Expected: `roster` and `matchup` listed as commands.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "Add MCP server and CLI from one registry (M-18, J-02, J-08, M-15)"
```

---

### Task 10: Live verification

The first two steps of the §11.3 canary. No writes — the write half of the canary belongs to Milestone 3.

**Files:**
- Create: `docs/setup.md`

**Interfaces:**
- Consumes: everything above
- Produces: a documented, repeatable setup; confirmation that reads work against the real league.

- [ ] **Step 1: Write the setup doc**

`docs/setup.md` covering: getting `espn_s2` and `SWID` from browser devtools; what `espn_s2` actually is (a full ESPN/Disney session cookie, not a scoped API key — never paste it into Discord or a GitHub issue); `chmod 0600` on the credentials file; the config file shape; and the MCP client stanza pointing at `fantasy-yolo-mcp`.

- [ ] **Step 2: Create the real config**

```bash
mkdir -p ~/.config/fantasy-yolo
# credentials.json: {"espn_s2": "...", "swid": "{...}"}
chmod 0600 ~/.config/fantasy-yolo/credentials.json
# config.json per docs/setup.md
```

- [ ] **Step 3: Confirm the canary**

Run: `uv run fy roster`
Expected: the real roster. If `X-Fantasy-Role` is `NONE`, the error says the login expired rather than showing an empty roster (A-02).

- [ ] **Step 4: Confirm the matchup**

Run: `uv run fy matchup`
Expected: this week's opponent and projections, with `week_resolved` matching the real week.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Add setup documentation"
```

---

## Done when

- `uv run pytest` and `uv run ruff check .` are green with no credentials and no network (M-03).
- `uv run fy roster` and `uv run fy matchup` return real data from the real league.
- The MCP server starts over stdio and lists exactly the same two tools, annotated `read_only_hint: true` (J-08).
- `registered(include_writes=False) == registered()` — no write code exists yet (§13).

## Next milestones

- **Milestone 2 — the rest of the reads.** `check_lineup` (B-09), `find_players`, `get_league`, `get_team`, `get_transactions`, `get_pending`, `get_history`, `get_budgets`.
- **Milestone 3 — the write path.** Payload builders against the unauthenticated schema oracle (§11.2), the audit log (J-03), the two-call token protocol (J-01), reconciliation (J-09), then the live toggle-and-revert canary (§11.3).
