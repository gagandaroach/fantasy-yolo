"""Single source of truth for tools exposed over MCP and the CLI (M-18).

A tool is a plain typed function. Both frontends read this registry, so neither
is the source of truth and the two interfaces cannot drift apart.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])


class Kind(StrEnum):
    """What a tool does.

    Load-bearing in three places at once: MCP annotations (J-08), CLI
    confirmation, and read-only filtering (J-02).
    """

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
    """Register a function as a tool, returning it unchanged so it stays callable."""

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
    """Registered tools, sorted by name.

    J-02 read-only mode passes include_writes=False, so disabled write tools are
    never registered at all and a model cannot see or offer them.
    """
    specs = sorted(_REGISTRY.values(), key=lambda s: s.name)
    if include_writes:
        return specs
    return [s for s in specs if not s.kind.is_write]


def clear_registry() -> None:
    """Test helper."""
    _REGISTRY.clear()
