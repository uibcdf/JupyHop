"""Explicit managed start RPC. Plaintext credentials only cross encrypted stdin."""

import getpass
import json
import re
import sys
import uuid
import warnings
from importlib.resources import files
from typing import Any

from jupyhop.discovery import validate_python
from jupyhop.errors import LaunchError, PrerequisiteError, ProtocolError, SSHError
from jupyhop.protocol import _invalid_constant, _text, _unique_object, parse_discovery
from jupyhop.ssh import STDIN_LIMIT, STDOUT_LIMIT, SSHTransport, ssh_failure

BOOTSTRAP = "import json,sys; p=json.load(sys.stdin); n={'__name__':'jupyhop_remote','_SOURCES':p['sources']}; [exec(compile(s,'<jupyhop-remote>','exec'),n) for s in p['sources']]; n['start_main'](p['request'])"
_ERRORS = {
    "invalid_request",
    "unsafe_state",
    "corrupt_state",
    "incompatible_registry",
    "registry_busy",
    "registry_full",
    "state_write_failed",
    "state_limit_or_corruption",
    "name_conflict",
    "id_conflict",
    "missing_tmux",
    "missing_python",
    "server_prerequisites",
    "unsupported_server_version",
    "invalid_workdir",
    "launch_failed",
    "readiness_timeout",
    "server_initialization_failed",
    "launch_unknown",
    "host_identity_unavailable",
}


def password_input(from_stdin: bool) -> str:
    if from_stdin:
        try:
            raw = sys.stdin.buffer.readline(4097)
            if len(raw) > 4096:
                raise ValueError
            password = raw.removesuffix(b"\n").decode("utf-8")
        except (UnicodeError, ValueError):
            raise ValueError(
                "Password input must be a UTF-8 line of at most 1024 characters."
            ) from None
    else:
        if not sys.stdin.isatty():
            raise ValueError(
                "Managed start requires a password. Use a terminal prompt or --password-stdin with a protected input source; never put passwords in argv."
            )
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            try:
                password = getpass.getpass("New Jupyter session password: ")
                if password != getpass.getpass("Confirm password: "):
                    raise ValueError("Passwords did not match.")
            except getpass.GetPassWarning:
                raise ValueError(
                    "A private password prompt is unavailable. Use --password-stdin with a protected source."
                ) from None
    if not 8 <= len(password) <= 1024 or any(ord(c) < 32 or ord(c) == 127 for c in password):
        raise ValueError("Password must have 8–1024 characters without control characters.")
    return password


def new_id() -> str:
    return uuid.uuid4().hex


def parse_start(raw: bytes, expected_id: str, expected_mode: str | None = None) -> dict[str, Any]:
    if len(raw) > STDOUT_LIMIT:
        raise ProtocolError(
            "Managed start response exceeds its size limit; remote state is unknown."
        )
    try:
        envelope = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_invalid_constant
        )
        protocol = envelope["protocol"]
        if type(protocol["major"]) is not int or protocol["major"] != 1:
            raise ProtocolError(
                "Incompatible managed start protocol major; inspect remote state before retrying."
            )
        if (
            type(protocol["minor"]) is not int
            or protocol["minor"] < 2
            or envelope["operation"] != "start"
        ):
            raise ValueError
        data = envelope["data"]
        if expected_mode is not None and (
            protocol["minor"] != 8 or data.get("auth_mode") != expected_mode
        ):
            raise ValueError
        if data["id"] != expected_id or data["state"] not in {
            "ready",
            "starting",
            "requested",
            "failed",
        }:
            raise ValueError
        error = data["error"]
        if error is not None and error not in _ERRORS:
            raise ValueError
        path = data["record_path"]
        if path is not None:
            path = _text(path)
            if not path.startswith("/") or not path.endswith("/" + expected_id + "/record.json"):
                raise ValueError
        server = identity = None
        if data["state"] == "ready":
            if error is not None:
                raise ValueError
            candidate = data["server"]
            wire = {
                "protocol": protocol,
                "operation": "discover",
                "data": {
                    "identity": data["identity"],
                    "complete": False,
                    "paths": [
                        {"path": path, "source": "managed", "status": "ok"}
                        for path in candidate["sources"]
                    ],
                    "servers": [candidate],
                    "issues": [],
                },
            }
            checked = parse_discovery(json.dumps(wire).encode())["data"]
            server = checked["servers"][0]
            identity = checked["identity"]
            if (
                server["origin"] != "managed"
                or server["id"] != expected_id
                or server["state"] != "ready"
            ):
                raise ValueError
        return {
            "id": expected_id,
            "state": data["state"],
            "error": error,
            "record_path": path,
            "server": server,
            "identity": identity,
        }
    except (KeyError, TypeError, ValueError, UnicodeError, RecursionError):
        raise ProtocolError(
            "Malformed managed start response; credentials and raw remote output were suppressed. Remote state may require inspection."
        ) from None


def start(
    transport: SSHTransport,
    *,
    server_python: str,
    helper_python: str = "python3",
    workdir: str = "~",
    name: str | None = None,
    password: str | None = None,
    auth_mode: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    session_id = new_id() if session_id is None else session_id
    name = "session-" + session_id[:8] if name is None else name
    if (
        re.fullmatch(r"[a-f0-9]{32}", session_id) is None
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", name) is None
    ):
        raise ValueError(
            "Use a simple session name of 1–64 letters, digits, underscores, dots or hyphens, starting with a letter/digit."
        )
    validate_python(helper_python)
    validate_python(server_python)
    if (
        not workdir
        or len(workdir) > 4096
        or any(ord(c) < 32 for c in workdir)
        or workdir.startswith("~")
        and not (workdir == "~" or workdir.startswith("~/"))
    ):
        raise ValueError(
            "Workdir must be a remote path or ~/ path without control characters; ~other is unsupported."
        )
    legacy = auth_mode is None and password is not None
    mode = auth_mode if auth_mode is not None else "password" if legacy else "token"
    if mode not in ("password", "token") or (mode == "token" and password is not None):
        raise ValueError("Token mode accepts no Jupyter password.")
    if mode == "password" and (
        password is None
        or not 8 <= len(password) <= 1024
        or any(ord(c) < 32 or ord(c) == 127 for c in password)
    ):
        raise ValueError("A password of 8–1024 characters without control characters is required.")
    sources = [
        files("jupyhop").joinpath(name).read_text()
        for name in ("_discovery_probe.py", "_managed_remote.py")
    ]
    request: dict[str, Any] = {
        "protocol": {"major": 1, "minor": 2 if legacy else 8},
        "id": session_id,
        "name": name,
        "server_python": server_python,
        "workdir": workdir,
        "budget": max(1, transport.timeout - 3),
    }
    if not legacy:
        request["auth_mode"] = mode
    if password is not None:
        request["password"] = password
    payload = json.dumps({"sources": sources, "request": request}, ensure_ascii=False).encode()
    if len(payload) > STDIN_LIMIT:
        raise ValueError(
            "Managed start request exceeds 64 KiB. Shorten the remote paths or password."
        )
    try:
        result = transport.run(
            [helper_python, "-I", "-B", "-c", BOOTSTRAP],
            stdin=payload,
        )
    except SSHError as transport_error:
        raise LaunchError(
            f"Start request {session_id} could not be confirmed. Remote state is unknown; inspect discover before retrying. {transport_error}"
        ) from None
    except ProtocolError:
        raise ProtocolError(
            f"Start request {session_id} returned invalid or oversized output. Remote state is unknown; inspect discover before retrying."
        ) from None
    if result.returncode == 255:
        problem = ssh_failure(result.stderr)
        raise LaunchError(
            f"SSH failed during start request {session_id}. Remote state is unknown; use discover before starting again. {problem}"
        )
    if result.returncode:
        raise LaunchError(
            f"Start request {session_id} could not be confirmed. Run discover to inspect remote state; do not assume a server was stopped."
        )
    report = parse_start(result.stdout, session_id, None if legacy else mode)
    report["host"] = transport.host
    return report


def require_ready(report: dict[str, Any]) -> None:
    error = report["error"]
    context = f"Session request {report['id']}: "
    if error == "registry_full":
        raise LaunchError(
            context
            + "the remote registry already contains 128 unarchived records. Inspect status and archive verified inactive entries before starting another session. No session was created for this request."
        )
    if error == "unsupported_server_version":
        raise PrerequisiteError(
            context
            + "managed start requires Jupyter Server >=2.20,<3 for native ephemeral ports. "
            + "Choose an existing compatible --server-python environment. "
            + "No session was created and nothing was installed remotely."
        )
    if error == "incompatible_registry":
        raise ProtocolError(
            context
            + "remote registry schema is incompatible. No migration or running-session update was attempted."
        )
    if error == "host_identity_unavailable":
        raise PrerequisiteError(
            context
            + "managed state needs a readable Linux /etc/machine-id or /var/lib/dbus/machine-id. No host identity or system configuration was created automatically."
        )
    if error in {
        "missing_tmux",
        "missing_python",
        "server_prerequisites",
        "invalid_workdir",
        "host_identity_unavailable",
    }:
        raise PrerequisiteError(
            context
            + "remote launch prerequisites failed ("
            + error
            + "). Verify tmux, an existing Jupyter Server >=2.20,<3 Python with kernels, and the remote directory. Nothing was installed remotely."
        )
    if report["state"] != "ready":
        raise LaunchError(
            context
            + "launch did not reach verified readiness ("
            + str(error)
            + "). A server may remain running. Inspect discover and the private session record before retrying; no process was stopped automatically."
        )
