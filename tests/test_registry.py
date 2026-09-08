import pytest

from fantasy_yolo.registry import Kind, clear_registry, registered, restore, snapshot, tool


@pytest.fixture(autouse=True)
def _clean():
    """Isolate each test without discarding tools registered at import time."""
    saved = snapshot()
    clear_registry()
    yield
    restore(saved)


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
