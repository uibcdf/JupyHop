"""Managed observations/reconciliation and explicitly authorized graceful stop."""

import json
import re
from importlib.resources import files
from typing import Any

from jupyhop.discovery import validate_python
from jupyhop.errors import (
    LifecycleError,
    OwnershipError,
    PrerequisiteError,
    ProtocolError,
    SSHError,
)
from jupyhop.protocol import _invalid_constant, _unique_object, parse_discovery
from jupyhop.ssh import STDOUT_LIMIT, SSHTransport, ssh_failure

_BOOTSTRAP = "import json,sys; p=json.load(sys.stdin); n={'__name__':'jupyhop_remote'}; [exec(compile(s,'<jupyhop-remote>','exec'),n) for s in p['sources']]; n['lifecycle_main'](p['request'])"
_ERRORS = {
    "invalid_request",
    "not_managed",
    "unverified_owner",
    "launch_unconfirmed",
    "pidfd_unavailable",
    "stop_pending",
    "lifecycle_unknown",
    "unsafe_state",
    "corrupt_state",
    "incompatible_registry",
    "registry_busy",
    "state_write_failed",
    "state_limit_or_corruption",
    "host_identity_unavailable",
    "response_too_large",
    "session_active",
    "session_unknown",
    "archive_conflict",
    "archive_unknown",
}


def validate_managed_id(identifier: str) -> str:
    if re.fullmatch(r"[a-f0-9]{32}", identifier) is None:
        raise OwnershipError(
            "An exact managed session UUID is required; unmanaged IDs, names and PIDs cannot authorize lifecycle actions. No SSH command was sent."
        )
    return identifier


def parse_lifecycle(raw: bytes, operation: str) -> dict[str, Any]:
    if len(raw) > STDOUT_LIMIT:
        raise ProtocolError("Lifecycle response exceeds its size limit; remote state is unknown.")
    try:
        envelope = json.loads(
            raw.decode(), object_pairs_hook=_unique_object, parse_constant=_invalid_constant
        )
        if (
            envelope["operation"] != operation
            or type(envelope["protocol"]["minor"]) is not int
            or envelope["protocol"]["minor"] < (4 if operation == "archive" else 3)
        ):
            raise ValueError
        error = envelope["data"].get("error")
        if error is not None and error not in _ERRORS:
            raise ValueError
        envelope["operation"] = "discover"
        data = parse_discovery(json.dumps(envelope).encode())["data"]
        result = {
            "identity": data["identity"],
            "servers": data["servers"],
            "error": error,
        }
        if operation == "archive":
            archived = envelope["data"].get("archived")
            if archived is not None:
                from jupyhop.protocol import _text

                sid, path = _text(archived["id"]), _text(archived["path"])
                if (
                    re.fullmatch(r"[a-f0-9]{32}", sid) is None
                    or not path.startswith("/")
                    or not path.endswith("/archive/" + sid)
                ):
                    raise ValueError
                archived = {"id": sid, "path": path}
            if (error is None) != (archived is not None):
                raise ValueError
            result["archived"] = archived
        return result
    except (KeyError, TypeError, ValueError, UnicodeError, RecursionError):
        raise ProtocolError(
            "Malformed lifecycle response; raw output was suppressed. Use status before retrying stop."
        ) from None


def lifecycle(
    transport: SSHTransport,
    operation: str,
    identifier: str | None = None,
    *,
    python: str = "python3",
) -> dict[str, Any]:
    if operation not in {"status", "stop", "archive"}:
        raise ValueError("Unsupported lifecycle operation.")
    if identifier is not None:
        validate_managed_id(identifier)
    elif operation != "status":
        raise OwnershipError(
            "Lifecycle action requires an exact managed UUID; no SSH command was sent."
        )
    sources = [
        files("jupyhop").joinpath(name).read_text()
        for name in (
            "_discovery_probe.py",
            "_managed_remote.py",
            "_archive_remote.py" if operation == "archive" else "_lifecycle_remote.py",
        )
    ]
    request = {
        "protocol": {"major": 1, "minor": 4 if operation == "archive" else 3},
        "operation": operation,
        "id": identifier,
        "budget": max(0.2, transport.timeout - 3),
    }
    try:
        result = transport.run(
            [
                validate_python(python),
                "-I",
                "-B",
                "-c",
                _BOOTSTRAP.replace("lifecycle_main", "archive_main")
                if operation == "archive"
                else _BOOTSTRAP,
            ],
            stdin=json.dumps({"sources": sources, "request": request}).encode(),
        )
    except SSHError:
        if operation != "status":
            raise LifecycleError(
                "Lifecycle action could not be confirmed. Use status before retrying stop, or retry archive with the same UUID. No automatic restart/deletion was attempted."
            ) from None
        raise
    if result.returncode == 255:
        problem = ssh_failure(result.stderr)
        if operation != "status":
            raise LifecycleError(f"Stop outcome is unknown; use status. {problem}")
        raise problem
    if result.returncode:
        raise LifecycleError(
            "Remote lifecycle request failed; use status and check --remote-python. Remote state is unknown."
        )
    report = parse_lifecycle(result.stdout, operation)
    if identifier is not None and any(s["id"] != identifier for s in report["servers"]):
        raise ProtocolError(
            "Lifecycle response selected a different session; remote state needs inspection."
        )
    if (
        operation == "archive"
        and report.get("archived") is not None
        and report["archived"]["id"] != identifier
    ):
        raise ProtocolError("Archive response selected a different session; inspect remote state.")
    report["host"] = transport.host
    return report


def require_lifecycle_ok(report: dict[str, Any]) -> None:
    error = report["error"]
    if error is None:
        return
    if error in {"not_managed", "unverified_owner"}:
        raise OwnershipError(
            "Lifecycle authority was not verified. Only exact owned managed sessions can be stopped; no unmanaged process was signalled."
        )
    if error in {"session_active", "session_unknown", "archive_conflict"}:
        raise OwnershipError(
            "Cannot retire a live, unconfirmed or conflicting session. Verify status and stop first; no archive move was authorized by uncertain identity."
        )
    if error in {"incompatible_registry", "corrupt_state", "unsafe_state", "response_too_large"}:
        raise ProtocolError(
            f"Managed state unavailable ({error}); no migration or automatic cleanup was attempted. Select one UUID for large status results."
        )
    if error == "pidfd_unavailable":
        raise PrerequisiteError(
            "Safe stop requires Linux pidfd support exposed by Python or native libc. Select another helper with --remote-python; no PID-only signal was sent."
        )
    raise LifecycleError(
        f"Lifecycle request is unconfirmed ({error}). Use status before retrying; kernel continuity is not implied."
    )
