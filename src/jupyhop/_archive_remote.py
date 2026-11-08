"""Explicit retirement of inactive records. Move evidence; never delete or kill."""

from typing import TYPE_CHECKING

if TYPE_CHECKING or __name__ == "jupyhop._archive_remote":
    import hashlib
    import json
    import os
    import pwd
    import stat
    import subprocess
    from typing import Any

    from jupyhop._discovery_probe import Unsupported, process_identity
    from jupyhop._managed_remote import (
        _SID,
        ManagedProblem,
        Registry,
        _load,
        _private_dir,
        _read,
        boot_id,
        state_root,
        validate_record,
    )


def _archived(registry: Registry, sid: str) -> dict[str, str] | None:
    root = os.path.join(registry.root, "archive", sid)
    try:
        descriptor = _private_dir(root)
    except FileNotFoundError:
        return None
    try:
        record = validate_record(_load(descriptor, "record.json"), sid)
        if (
            hashlib.sha256(_read(descriptor, "launch.py", 96 * 1024)).hexdigest()
            != record["runner_sha256"]
        ):
            raise ManagedProblem("corrupt_state")
    finally:
        os.close(descriptor)
    return {"id": sid, "path": root}


def _inactive(record: dict[str, Any]) -> None:
    if record["pid"] is None:
        if record["state"] != "failed":
            raise ManagedProblem("launch_unconfirmed")
    else:
        try:
            if process_identity(record["pid"]) == record["process_start"]:
                raise ManagedProblem("session_active")
            # Damaged start-time metadata must not hide a live launcher at this
            # exact state path, even if the recorded tmux socket is unavailable.
            launcher = os.path.join(os.path.dirname(record["runtime"]), "launch.py")
            with open(f"/proc/{record['pid']}/cmdline", "rb") as stream:
                arguments = stream.read(16385).split(b"\0")
            if os.fsencode(launcher) in arguments:
                raise ManagedProblem("session_active")
        except (FileNotFoundError, ProcessLookupError):
            pass
        except (Unsupported, OSError, ValueError):
            raise ManagedProblem("session_unknown") from None
    # Refuse any live pane on the dedicated socket, including a damaged record.
    try:
        descriptor = _private_dir(os.path.dirname(record["socket"]))
        os.close(descriptor)
        info = os.stat(record["socket"], follow_symlinks=False)
    except FileNotFoundError:
        return
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ManagedProblem("unsafe_state")
    try:
        result = subprocess.run(
            ["tmux", "-S", record["socket"], "list-panes", "-a", "-F", "#{pane_pid}"],
            capture_output=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ManagedProblem("session_unknown") from None
    if result.returncode == 0 and result.stdout.strip():
        raise ManagedProblem("session_active")


def archive_record(sid: str) -> dict[str, str]:
    with Registry() as registry, registry.lock():
        records = registry.records()
        record = next((r for r in records if r["id"] == sid), None)
        previous = _archived(registry, sid)
        if record is None:
            if previous is not None:
                return previous
            raise ManagedProblem("not_managed")
        if previous is not None:
            raise ManagedProblem("archive_conflict")
        _inactive(record)
        descriptor = _private_dir(os.path.join(registry.root, "archive"), True)
        try:
            os.rename(sid, sid, src_dir_fd=registry.sessions, dst_dir_fd=descriptor)
            os.fsync(registry.sessions)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return {"id": sid, "path": os.path.join(registry.root, "archive", sid)}


def archive_main(request: dict[str, Any]) -> None:
    scope = hashlib.sha256(
        json.dumps((boot_id(), os.getuid()), separators=(",", ":")).encode()
    ).hexdigest()[:24]
    data: dict[str, Any] = {
        "identity": {"uid": os.getuid(), "user": pwd.getpwuid(os.getuid()).pw_name, "scope": scope},
        "complete": False,
        "paths": [],
        "servers": [],
        "issues": [],
        "error": None,
        "archived": None,
    }
    try:
        sid = request.get("id")
        if (
            request.get("protocol") != {"major": 1, "minor": 4}
            or request.get("operation") != "archive"
            or not isinstance(sid, str)
            or not _SID.fullmatch(sid)
        ):
            raise ManagedProblem("invalid_request")
        data["archived"] = archive_record(sid)
    except FileNotFoundError:
        data["error"] = "corrupt_state" if os.path.lexists(state_root()) else "not_managed"
    except ManagedProblem as error:
        data["error"] = error.code
    except Exception:
        data["error"] = "archive_unknown"
    print(json.dumps({"protocol": {"major": 1, "minor": 4}, "operation": "archive", "data": data}))
