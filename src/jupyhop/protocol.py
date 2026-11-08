"""Strict version negotiation and allowlisted nonsecret doctor fields."""

import json
import unicodedata
from typing import Any

from jupyhop.errors import ProtocolError
from jupyhop.ssh import STDOUT_LIMIT


def _text(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 4096
        or any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in value)
    ):
        raise ValueError
    return value


def _version(value: Any) -> str | None:
    return None if value is None else _text(value)


def _boolean(value: Any) -> bool:
    if type(value) is not bool:
        raise ValueError
    return value


def _integer(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError


def parse_doctor(raw: bytes) -> dict[str, Any]:
    if len(raw) > STDOUT_LIMIT:
        raise ProtocolError("Remote probe response exceeds 64 KiB.")
    try:
        envelope = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_invalid_constant
        )
        protocol = envelope["protocol"]
        major, minor = _integer(protocol["major"]), _integer(protocol["minor"])
        if major != 1:
            raise ProtocolError(
                "Incompatible remote probe protocol major. Use a matching JupyHop client; no remote update or state write was attempted."
            )
        if envelope["operation"] != "doctor":
            raise ValueError
        data = envelope["data"]
        identity, python = data["identity"], data["python"]
        managers = data["process_managers"]
        manager = managers["systemd_user"]
        if manager not in ("missing", "available", "unavailable"):
            raise ValueError
        dirs = data["runtime_dirs"]
        if not isinstance(dirs, list) or len(dirs) > 32:
            raise ValueError
        runtime_dirs = []
        for entry in dirs:
            if (
                entry["status"] not in ("missing", "accessible", "inaccessible")
                or entry["source"] != "selected-python"
            ):
                raise ValueError
            runtime_dirs.append(
                {
                    "path": _text(entry["path"]),
                    "source": "selected-python",
                    "status": entry["status"],
                }
            )
        if data["coverage"] != "selected-interpreter-only":
            raise ValueError
        # Rebuild from known fields: never forward arbitrary remote JSON/secrets.
        return {
            "protocol": {"major": major, "minor": minor},
            "operation": "doctor",
            "data": {
                "identity": {"uid": _integer(identity["uid"]), "user": _text(identity["user"])},
                "python": {
                    "version": _text(python["version"]),
                    "executable": _text(python["executable"]),
                    "supported": _boolean(python["supported"]),
                },
                "jupyter_server": {"version": _version(data["jupyter_server"]["version"])},
                "jupyter_core": {"version": _version(data["jupyter_core"]["version"])},
                "runtime_dirs": runtime_dirs,
                "coverage": "selected-interpreter-only",
                "process_managers": {"systemd_user": manager, "tmux": _boolean(managers["tmux"])},
            },
        }
    except (ValueError, TypeError, KeyError, RecursionError, UnicodeError):
        raise ProtocolError(
            "Malformed remote probe response. Expected versioned JSON only; check remote shell startup banners and interpreter configuration."
        ) from None
