"""Read-only managed inventory and bounded private archive pages (wire 1.5)."""

from typing import TYPE_CHECKING

if TYPE_CHECKING or __name__ == "jupyhop._inventory_remote":
    import hashlib
    import json
    import os
    import pwd
    import signal
    from typing import Any

    from jupyhop._discovery_probe import Deadline, Unsupported, _candidate, _deadline
    from jupyhop._managed_remote import (
        _SID,
        ManagedProblem,
        Registry,
        _load,
        _private_dir,
        _read,
        boot_id,
        mark_managed,
        missing_managed,
        state_root,
        validate_record,
    )


def inventory_observe(record: dict[str, Any], scope: str) -> dict[str, Any]:
    server = missing_managed([record], set())[0]
    if record["pid"] and record["port"] and record["socket_inode"]:
        try:
            descriptor = _private_dir(record["runtime"])
            try:
                candidate = _candidate(
                    descriptor, f"jpserver-{record['pid']}.json", record["runtime"], scope
                )
                candidate = mark_managed(candidate, [record])
                if candidate["origin"] == "managed":
                    server = candidate
            finally:
                os.close(descriptor)
        except (OSError, Unsupported, ManagedProblem, ValueError):
            pass
    return {key: server[key] for key in ("id", "name", "state", "reason")}


def inventory_history(registry: Registry, offset: int) -> dict[str, Any]:
    """A page is an observation, not a stable cursor across concurrent renames."""
    page: dict[str, Any] = {"entries": [], "offset": offset, "next_offset": None, "complete": False}
    try:
        directory = _private_dir(os.path.join(registry.root, "archive"))
    except FileNotFoundError:
        page["complete"] = offset == 0
        return page
    try:
        with os.scandir(directory) as entries:
            for index, entry in enumerate(entries):
                if not _SID.fullmatch(entry.name):
                    raise ManagedProblem("corrupt_state")
                if index < offset:
                    continue
                if len(page["entries"]) == 64:
                    page["next_offset"] = offset + 64 if offset + 64 <= 4096 else None
                    return page
                path = os.path.join(registry.root, "archive", entry.name)
                descriptor = _private_dir(path)
                try:
                    record = validate_record(_load(descriptor, "record.json"), entry.name)
                    if (
                        record["runtime"]
                        != os.path.join(registry.root, "sessions", entry.name, "runtime")
                        or hashlib.sha256(_read(descriptor, "launch.py", 96 * 1024)).hexdigest()
                        != record["runner_sha256"]
                    ):
                        raise ManagedProblem("corrupt_state")
                    page["entries"].append(
                        {
                            "id": record["id"],
                            "name": record["name"],
                            "record_state": record["state"],
                        }
                    )
                finally:
                    os.close(descriptor)
        page["complete"] = offset == 0
        return page
    finally:
        os.close(directory)


def inventory_main(request: dict[str, Any]) -> None:
    scope = hashlib.sha256(
        json.dumps((boot_id(), os.getuid()), separators=(",", ":")).encode()
    ).hexdigest()[:24]
    data: dict[str, Any] = {
        "identity": {"uid": os.getuid(), "user": pwd.getpwuid(os.getuid()).pw_name, "scope": scope},
        "sessions": [],
        "complete": False,
        "history": None,
        "error": None,
        "history_error": None,
    }
    try:
        offset = request.get("history_offset")
        budget = request.get("budget")
        if (
            request.get("protocol") != {"major": 1, "minor": 5}
            or request.get("operation") != "inventory"
            or type(offset) is not int
            or not 0 <= offset <= 4096
            or not isinstance(budget, (int, float))
            or isinstance(budget, bool)
            or not 0.1 <= budget <= 10
        ):
            raise ManagedProblem("invalid_request")
        signal.signal(signal.SIGALRM, _deadline)
        signal.setitimer(signal.ITIMER_REAL, budget)
        try:
            with Registry() as registry:
                for record in registry.records():
                    data["sessions"].append(inventory_observe(record, scope))
                data["complete"] = True
                try:
                    data["history"] = inventory_history(registry, offset)
                except (ManagedProblem, OSError, ValueError):
                    data["history_error"] = "history_unavailable"
        except FileNotFoundError:
            if os.path.lexists(state_root()):
                raise ManagedProblem("corrupt_state") from None
            data["complete"] = True
            data["history"] = {
                "entries": [],
                "offset": offset,
                "next_offset": None,
                "complete": offset == 0,
            }
    except Deadline:
        if data["complete"]:
            data["history_error"] = "time_limit"
        else:
            data["error"] = "time_limit"
    except ManagedProblem as error:
        data["error"] = error.code
    except Exception:
        data["error"] = "inventory_unavailable"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    print(
        json.dumps({"protocol": {"major": 1, "minor": 5}, "operation": "inventory", "data": data})
    )
