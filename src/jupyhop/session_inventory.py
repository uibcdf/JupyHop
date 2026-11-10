"""Versioned read-only inventory; display names never replace lifecycle UUIDs."""

import json
import re
from importlib.resources import files
from typing import Any

from jupyhop.discovery import validate_python
from jupyhop.errors import ProtocolError
from jupyhop.lifecycle import _ERRORS
from jupyhop.protocol import (
    DISCOVERY_REASONS,
    DISCOVERY_STATES,
    _boolean,
    _integer,
    _invalid_constant,
    _text,
    _unique_object,
)
from jupyhop.ssh import STDOUT_LIMIT, SSHTransport, ssh_failure

_BOOTSTRAP = "import json,sys; p=json.load(sys.stdin); n={'__name__':'jupyhop_remote'}; [exec(compile(s,'<jupyhop-remote>','exec'),n) for s in p['sources']]; n['inventory_main'](p['request'])"


def _item(entry: Any, *, archived: bool) -> dict[str, str]:
    sid, name = _text(entry["id"]), _text(entry["name"])
    if (
        re.fullmatch(r"[a-f0-9]{32}", sid) is None
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", name) is None
    ):
        raise ValueError
    result = {"id": sid, "name": name}
    if archived:
        if entry["record_state"] not in {"requested", "starting", "ready", "failed", "exited"}:
            raise ValueError
        result["record_state"] = entry["record_state"]
    else:
        if entry["state"] not in DISCOVERY_STATES or entry["reason"] not in DISCOVERY_REASONS:
            raise ValueError
        result.update(state=entry["state"], reason=entry["reason"])
    return result


def parse_inventory(raw: bytes) -> dict[str, Any]:
    if len(raw) > STDOUT_LIMIT:
        raise ProtocolError("Session inventory exceeds its size limit; counts are unknown.")
    try:
        envelope = json.loads(
            raw.decode(), object_pairs_hook=_unique_object, parse_constant=_invalid_constant
        )
        version = envelope["protocol"]
        if (
            _integer(version["major"]) != 1
            or _integer(version["minor"]) < 5
            or envelope["operation"] != "inventory"
        ):
            raise ValueError
        data = envelope["data"]
        identity = data["identity"]
        scope = _text(identity["scope"])
        if re.fullmatch(r"[a-f0-9]{24}", scope) is None:
            raise ValueError
        sessions = data["sessions"]
        if not isinstance(sessions, list) or len(sessions) > 128:
            raise ValueError
        active = [_item(entry, archived=False) for entry in sessions]
        if len({entry["id"] for entry in active}) != len(active) or len(
            {entry["name"] for entry in active}
        ) != len(active):
            raise ValueError
        error, history_error = data["error"], data["history_error"]
        errors = _ERRORS | {"time_limit", "inventory_unavailable", "history_unavailable"}
        if (
            error is not None
            and error not in errors
            or history_error is not None
            and history_error not in errors
        ):
            raise ValueError
        complete = _boolean(data["complete"])
        if complete and error is not None:
            raise ValueError
        history = data["history"]
        if history is not None:
            entries = history["entries"]
            if not isinstance(entries, list) or len(entries) > 64:
                raise ValueError
            offset = _integer(history["offset"])
            following = history["next_offset"]
            if (
                offset > 4096
                or following is not None
                and (type(following) is not int or following != offset + 64 or following > 4096)
            ):
                raise ValueError
            historical = [_item(entry, archived=True) for entry in entries]
            if len({entry["id"] for entry in historical}) != len(historical):
                raise ValueError
            exact = _boolean(history["complete"])
            if exact and (offset != 0 or following is not None):
                raise ValueError
            history = {
                "entries": historical,
                "offset": offset,
                "next_offset": following,
                "complete": exact,
            }
        return {
            "version": 1,
            "identity": {
                "uid": _integer(identity["uid"]),
                "user": _text(identity["user"]),
                "scope": scope,
            },
            "sessions": active,
            "complete": complete,
            "history": history,
            "error": error,
            "history_error": history_error,
        }
    except (KeyError, ValueError, TypeError, UnicodeError, RecursionError):
        raise ProtocolError(
            "Malformed session inventory; raw output suppressed and counts unknown."
        ) from None


def inspect_sessions(
    transport: SSHTransport, *, python: str = "python3", history_offset: int = 0
) -> dict[str, Any]:
    if type(history_offset) is not int or not 0 <= history_offset <= 4096:
        raise ValueError("History offset must be between 0 and 4096.")
    sources = [
        files("jupyhop").joinpath(name).read_text()
        for name in ("_discovery_probe.py", "_managed_remote.py", "_inventory_remote.py")
    ]
    request = {
        "protocol": {"major": 1, "minor": 5},
        "operation": "inventory",
        "history_offset": history_offset,
        "budget": min(10, max(0.1, transport.timeout - 1)),
    }
    result = transport.run(
        [validate_python(python), "-I", "-B", "-c", _BOOTSTRAP],
        stdin=json.dumps({"sources": sources, "request": request}).encode(),
    )
    if result.returncode == 255:
        raise ssh_failure(result.stderr)
    if result.returncode:
        raise ProtocolError(
            "Session inventory could not run; counts are unknown. Check --remote-python."
        )
    report = parse_inventory(result.stdout)
    report["host"] = transport.host
    return report


def summary(report: dict[str, Any]) -> dict[str, Any]:
    sessions = report["sessions"]
    exact = report["complete"] and report["error"] is None
    history = report["history"]
    return {
        "ready": sum(s["state"] == "ready" for s in sessions) if exact else None,
        "stopped": sum(s["state"] == "stopped" for s in sessions) if exact else None,
        "review": sum(s["state"] not in {"ready", "stopped"} for s in sessions) if exact else None,
        "unarchived": len(sessions) if exact else None,
        "archived": len(history["entries"]) if history is not None else None,
        "archive_count_exact": history is not None
        and history["complete"]
        and report["history_error"] is None,
    }
