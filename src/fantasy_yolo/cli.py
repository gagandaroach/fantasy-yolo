"""CLI frontend. Same registry as the MCP server, so the two cannot drift (M-18)."""

from __future__ import annotations

import inspect
import json
import types
import typing

import typer
from pydantic import BaseModel

import fantasy_yolo.tools  # noqa: F401  (importing registers the tools)
from fantasy_yolo.creds import redact
from fantasy_yolo.registry import Kind, ToolSpec, registered

# Conditions a user causes and can fix. A stack trace helps nobody here (J-06),
# and error text is redacted on the way out because it can quote a request (J-03).
EXPECTED_ERRORS = (
    FileNotFoundError,
    PermissionError,
    LookupError,
    ValueError,
)


def _current_credentials():
    """Best effort, so redaction still works when config itself is broken."""
    try:
        from fantasy_yolo.config import load_settings
        from fantasy_yolo.creds import load_credentials

        settings = load_settings()
        if settings.credentials_file is None:
            return None
        return load_credentials(settings.credentials_file)
    except Exception:
        return None


def error_message(exc: BaseException) -> str:
    """KeyError stringifies as repr(arg), wrapping the message in quotes. Only
    that case needs unwrapping — stripping every message mangles quoted names."""
    if isinstance(exc, KeyError) and exc.args:
        return str(exc.args[0])
    return str(exc)


def render(result: object) -> str:
    if isinstance(result, BaseModel):
        return json.dumps(result.model_dump(mode="json"), indent=2, default=str)
    return str(result)


def cli_name(tool_name: str) -> str:
    """`get_roster` reads better as `fy roster`.

    Only the `get_` prefix is dropped: on a write tool the verb carries meaning,
    so `preview_lineup` and `execute_lineup` keep theirs.
    """
    stem = tool_name.removeprefix("get_")
    return stem.replace("_", "-")


def _typer_annotation(annotation: object) -> object:
    """Typer cannot parse PEP 604 unions (``int | None``); rewrite them as Optional.

    Tools are written in modern syntax and stay that way — the adaptation belongs
    at the CLI boundary, not in the tool signatures.
    """
    if isinstance(annotation, types.UnionType):
        return typing.Union[typing.get_args(annotation)]  # noqa: UP007
    return annotation


def _cli_signature(fn: object) -> inspect.Signature:
    # eval_str resolves the strings that `from __future__ import annotations`
    # leaves behind; without it every annotation is str and the rewrite misses.
    sig = inspect.signature(fn, eval_str=True)
    params = [
        p.replace(annotation=_typer_annotation(p.annotation))
        for p in sig.parameters.values()
    ]
    return sig.replace(parameters=params, return_annotation=inspect.Signature.empty)


def _make_command(spec: ToolSpec):
    def command(**kwargs: object) -> None:
        if spec.kind is Kind.WRITE_EXECUTE and not kwargs.pop("yes", False):
            typer.confirm("This writes to your ESPN account. Continue?", abort=True)
        try:
            typer.echo(render(spec.fn(**kwargs)))
        except EXPECTED_ERRORS as exc:
            message = redact(error_message(exc), _current_credentials())
            typer.secho(f"error: {message}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from None

    command.__name__ = spec.name
    command.__doc__ = spec.description
    command.__signature__ = _cli_signature(spec.fn)
    return command


def build_cli() -> typer.Typer:
    app = typer.Typer(
        help="Talk to your own ESPN fantasy football team.",
        no_args_is_help=True,
    )
    for spec in registered():
        app.command(
            name=cli_name(spec.name),
            help=spec.description.splitlines()[0],
        )(_make_command(spec))
    return app


def main() -> None:
    build_cli()()
