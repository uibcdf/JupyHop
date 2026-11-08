"""Explicit lifecycle RPC; stdlib source sent only for status/stop.

No process is signalled by PID. A pidfd is opened before identity checks and
remains pinned until SIGTERM and exit observation. No escalation to SIGKILL.
"""

import ctypes
import errno
import select
import signal
from typing import TYPE_CHECKING

if TYPE_CHECKING or __name__ == "jupyhop._lifecycle_remote":
    import hashlib
    import json
    import os
    import pwd
    from typing import Any

    from jupyhop._discovery_probe import Unsupported, _candidate, listener_inode
    from jupyhop._managed_remote import (
        _SID,
        ManagedProblem,
        Registry,
        _private_dir,
        _save,
        boot_id,
        mark_managed,
        missing_managed,
        runner_matches,
        state_root,
    )


class PinnedProcess:
    """Prefer Python's APIs; some Conda builds omit them despite kernel support."""

    def __init__(self, pid: int):
        self.fd = -1
        native_open = getattr(os, "pidfd_open", None)
        self.native_send = getattr(signal, "pidfd_send_signal", None)
        self.libc_send: Any = None
        if native_open is not None and self.native_send is not None:
            self.fd = native_open(pid, 0)
        else:
            try:
                library = ctypes.CDLL(None, use_errno=True)
                opener = library.pidfd_open
                opener.argtypes = [ctypes.c_int, ctypes.c_uint]
                opener.restype = ctypes.c_int
                self.libc_send = library.pidfd_send_signal
                self.libc_send.argtypes = [
                    ctypes.c_int,
                    ctypes.c_int,
                    ctypes.c_void_p,
                    ctypes.c_uint,
                ]
                self.libc_send.restype = ctypes.c_int
            except (AttributeError, OSError):
                raise ManagedProblem("pidfd_unavailable") from None
            self.fd = opener(pid, 0)
            if self.fd == -1:
                code = ctypes.get_errno()
                raise OSError(code, os.strerror(code))
        os.set_inheritable(self.fd, False)

    def send_term(self) -> None:
        if self.libc_send is None:
            assert self.native_send is not None
            self.native_send(self.fd, signal.SIGTERM, None, 0)
        elif self.libc_send(self.fd, signal.SIGTERM, None, 0) == -1:
            code = ctypes.get_errno()
            raise OSError(code, os.strerror(code))

    def exited(self, timeout: float = 0) -> bool:
        return bool(select.select([self.fd], [], [], timeout)[0])

    def close(self) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1


def _identity() -> dict[str, Any]:
    scope = hashlib.sha256(
        json.dumps((boot_id(), os.getuid()), separators=(",", ":")).encode()
    ).hexdigest()[:24]
    return {"uid": os.getuid(), "user": pwd.getpwuid(os.getuid()).pw_name, "scope": scope}


def _observe(record: dict[str, Any], scope: str) -> dict[str, Any]:
    if record["pid"] and record["port"] and record["socket_inode"]:
        try:
            descriptor = _private_dir(record["runtime"])
            try:
                candidate = _candidate(
                    descriptor, f"jpserver-{record['pid']}.json", record["runtime"], scope
                )
                candidate = mark_managed(candidate, [record])
                if candidate["origin"] == "managed":
                    return candidate
            finally:
                os.close(descriptor)
        except (OSError, Unsupported, ManagedProblem, ValueError):
            pass
    return missing_managed([record], set())[0]


def _stop(registry: Registry, sid: str, budget: float) -> None:
    pinned = None
    try:
        with registry.lock():
            record = next((r for r in registry.records() if r["id"] == sid), None)
            if record is None:
                raise ManagedProblem("not_managed")
            state = missing_managed([record], set())[0]["state"]
            if state in {"stale", "stopped"}:
                return  # Lost old identity, never signal a replacement/rebooted PID.
            if not record["pid"]:
                raise ManagedProblem("launch_unconfirmed")
            try:
                pinned = PinnedProcess(record["pid"])
            except OSError as error:
                if error.errno == errno.ESRCH:
                    return
                raise ManagedProblem("pidfd_unavailable") from None
            if pinned.exited():
                return
            if not runner_matches(record):
                if pinned.exited():
                    return
                if record.get("stop_requested"):
                    raise ManagedProblem("stop_pending")
                raise ManagedProblem("unverified_owner")
            if record["port"] and not record.get("stop_requested"):
                try:
                    if listener_inode(record["pid"], record["port"]) != record["socket_inode"]:
                        raise ManagedProblem("unverified_owner")
                except (OSError, Unsupported):
                    raise ManagedProblem("unverified_owner") from None
            record["stop_requested"] = True
            with registry.session(sid) as descriptor:
                _save(descriptor, "record.json", record)
            # A disconnect here is recoverable: a retry pins/revalidates again.
            try:
                pinned.send_term()
            except ProcessLookupError:
                pass
        if not pinned.exited(min(10, max(0, budget))):
            raise ManagedProblem("stop_pending")
    finally:
        if pinned is not None:
            pinned.close()


def lifecycle_main(request: dict[str, Any]) -> None:
    operation = request.get("operation")
    data: dict[str, Any] = {
        "identity": _identity(),
        "complete": False,
        "paths": [],
        "servers": [],
        "issues": [],
        "error": None,
    }
    try:
        sid = request.get("id")
        if (
            request.get("protocol") != {"major": 1, "minor": 3}
            or operation not in {"status", "stop"}
            or sid is not None
            and (not isinstance(sid, str) or not _SID.fullmatch(sid))
            or operation == "stop"
            and sid is None
        ):
            raise ManagedProblem("invalid_request")
        try:
            with Registry() as registry:
                records = registry.records()
                if sid is not None and not any(r["id"] == sid for r in records):
                    raise ManagedProblem("not_managed")
                if operation == "stop":
                    assert sid is not None
                    try:
                        _stop(registry, sid, request["budget"])
                    except ManagedProblem as error:
                        data["error"] = error.code
                    records = registry.records()
                    if not any(r["id"] == sid for r in records):
                        data["error"] = "not_managed"
                for record in records:
                    if sid is not None and record["id"] != sid:
                        continue
                    server = _observe(record, data["identity"]["scope"])
                    # Readiness recovery after the initiating client disappeared.
                    if server["state"] == "ready" and record["state"] == "starting":
                        registry.update(record["id"], {"state": "ready", "error": None})
                    data["paths"].append(
                        {"path": record["runtime"], "source": "managed", "status": "ok"}
                    )
                    data["servers"].append(server)
        except FileNotFoundError:
            if os.path.lexists(state_root()):
                raise ManagedProblem("corrupt_state") from None
            if sid is not None:
                raise ManagedProblem("not_managed") from None
    except ManagedProblem as error:
        data["error"] = error.code
    except Exception:
        data["error"] = "lifecycle_unknown"
    envelope = {"protocol": {"major": 1, "minor": 3}, "operation": operation, "data": data}
    if len(json.dumps(envelope).encode()) > 60 * 1024:
        data.update({"paths": [], "servers": [], "error": "response_too_large"})
    print(json.dumps(envelope))
