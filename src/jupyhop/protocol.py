"""Strict version negotiation and allowlisted nonsecret doctor fields."""

import json
import re
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


DISCOVERY_STATES = {"ready", "stale", "unsupported", "unreachable", "starting", "failed"}
DISCOVERY_REASONS = {
    "verified",
    "invalid_metadata",
    "legacy_metadata",
    "https_or_unix_socket",
    "unsupported_address",
    "unverified_process_or_listener",
    "endpoint_unavailable",
    "unsupported_jupyter_or_auth",
    "process_or_file_gone",
    "managed_starting",
    "managed_failed",
    "managed_stale",
    "managed_unreachable",
}


def parse_discovery(raw: bytes) -> dict[str, Any]:
    """Rebuild the response, excluding tokens/URLs and any future unknown fields."""
    from jupyhop._discovery_probe import valid_base

    if len(raw) > STDOUT_LIMIT:
        raise ProtocolError("Remote discovery response exceeds 64 KiB.")
    try:
        envelope = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_invalid_constant
        )
        version = envelope["protocol"]
        major, minor = _integer(version["major"]), _integer(version["minor"])
        if major != 1:
            raise ProtocolError(
                "Incompatible discovery protocol major; no remote update was attempted."
            )
        if envelope["operation"] != "discover":
            raise ValueError
        data = envelope["data"]
        identity = data["identity"]
        scope = _text(identity["scope"])
        if re.fullmatch(r"[0-9a-f]{24}", scope) is None or data["complete"] is not False:
            raise ValueError
        if not isinstance(data["paths"], list) or len(data["paths"]) > 145:
            raise ValueError
        paths = []
        for entry in data["paths"]:
            path = _text(entry["path"])
            if len(path) > 1024 or not path.startswith("/"):
                raise ValueError
            if entry["source"] not in {
                "jupyter-core",
                "linux-default",
                "explicit",
                "managed",
            } or entry["status"] not in {"ok", "missing", "unsafe", "limited"}:
                raise ValueError
            paths.append({"path": path, "source": entry["source"], "status": entry["status"]})
        if not isinstance(data["servers"], list) or len(data["servers"]) > 192:
            raise ValueError
        servers = []
        for entry in data["servers"]:
            identifier = _text(entry["id"])
            origin = entry["origin"]
            if (
                origin not in ("managed", "unmanaged")
                or re.fullmatch(
                    r"[0-9a-f]{32}" if origin == "managed" else r"[0-9a-f]{24}", identifier
                )
                is None
            ):
                raise ValueError
            observed = entry.get("observed_id", identifier if origin == "unmanaged" else None)
            if observed is not None and (
                not isinstance(observed, str) or re.fullmatch(r"[0-9a-f]{24}", observed) is None
            ):
                raise ValueError
            name = entry.get("name")
            if origin == "managed" and (
                not isinstance(name, str)
                or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", name) is None
            ):
                raise ValueError
            if entry["state"] not in DISCOVERY_STATES or entry["reason"] not in DISCOVERY_REASONS:
                raise ValueError
            port = None if entry["port"] is None else _integer(entry["port"])
            pid = None if entry["pid"] is None else _integer(entry["pid"])
            if port is not None and not 1 <= port <= 65535 or pid == 0:
                raise ValueError
            base = entry["base_url"]
            if base is not None and not valid_base(base):
                raise ValueError
            if entry["address"] not in (None, "127.0.0.1"):
                raise ValueError
            sources = entry["sources"]
            if (
                not isinstance(sources, list)
                or not 1 <= len(sources) <= 145
                or any(
                    not isinstance(path, str) or path not in {p["path"] for p in paths}
                    for path in sources
                )
            ):
                raise ValueError
            server_version = _version(entry["version"])
            if (
                server_version is not None
                and re.fullmatch(r"2\.[0-9][A-Za-z0-9.!+_-]{0,62}", server_version) is None
            ):
                raise ValueError
            if entry["state"] == "ready" and (
                entry["address"] != "127.0.0.1"
                or pid is None
                or port is None
                or base is None
                or server_version is None
                or entry["reason"] != "verified"
                or observed is None
            ):
                raise ValueError
            servers.append(
                {
                    "id": identifier,
                    "origin": origin,
                    "observed_id": observed,
                    "name": name if origin == "managed" else None,
                    "state": entry["state"],
                    "reason": entry["reason"],
                    "pid": pid,
                    "port": port,
                    "address": entry["address"],
                    "base_url": base,
                    "version": server_version,
                    "sources": list(dict.fromkeys(sources)),
                }
            )
        issues = data["issues"]
        if (
            not isinstance(issues, list)
            or len(issues) > 32
            or any(
                issue
                not in (
                    "entry_limit",
                    "time_limit",
                    "output_limit",
                    "probe_failed",
                    "managed_state_unavailable",
                )
                for issue in issues
            )
        ):
            raise ValueError
        return {
            "protocol": {"major": major, "minor": minor},
            "operation": "discover",
            "data": {
                "identity": {
                    "uid": _integer(identity["uid"]),
                    "user": _text(identity["user"]),
                    "scope": scope,
                },
                "complete": False,
                "paths": paths,
                "servers": servers,
                "issues": issues,
            },
        }
    except (KeyError, ValueError, TypeError, UnicodeError, RecursionError):
        raise ProtocolError(
            "Malformed discovery response; raw remote output was suppressed."
        ) from None
