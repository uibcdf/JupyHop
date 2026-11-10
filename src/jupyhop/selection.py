"""Shared terminal selection; resolve friendly names once to a pinned UUID."""

import re
import sys
from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from jupyhop.errors import SelectionError

T = TypeVar("T")


def validate_name(name: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", name) is None:
        raise ValueError(
            "Use an exact managed name of 1–64 simple characters, starting with a letter/digit."
        )
    return name


def choose(
    candidates: Sequence[T],
    describe: Callable[[T], str],
    *,
    interactive: bool,
    explicit: bool = False,
    prompt: str = "Select a session number (Enter cancels): ",
) -> T:
    if not candidates:
        raise SelectionError(
            "No eligible session found. Inspect status/discover; remote state was not changed."
        )
    if len(candidates) == 1 and (explicit or not interactive):
        return candidates[0]
    if not interactive:
        raise SelectionError(
            "Multiple sessions/routes found. Supply an exact host and UUID; no target was selected."
        )
    for index, candidate in enumerate(candidates, 1):
        print(f"{index}: {describe(candidate)}", file=sys.stderr)
    print(prompt, end="", file=sys.stderr, flush=True)
    value = sys.stdin.readline().strip()
    if not value.isascii() or not value.isdigit() or not 1 <= int(value) <= len(candidates):
        raise SelectionError("Selection cancelled or invalid; no lifecycle action was authorized.")
    return candidates[int(value) - 1]


def describe_session(session: dict[str, Any]) -> str:
    return f"{session.get('name') or '(unnamed)'}  {session.get('origin', 'managed')}  {session['state']}  {session['id']}"


def resolve_name(sessions: list[dict[str, Any]], name: str) -> dict[str, Any]:
    validate_name(name)
    found = [
        s for s in sessions if s.get("origin", "managed") == "managed" and s.get("name") == name
    ]
    if len(found) != 1:
        raise SelectionError(
            "The exact name did not identify one current managed session. Inspect status; archived names are not selectors."
        )
    return found[0]
