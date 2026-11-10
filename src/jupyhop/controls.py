"""Shared inventory/select/confirm/dispatch for CLI and terminal management."""

import argparse
import json
import sys
from typing import Any

from jupyhop.errors import JupyHopError, LifecycleError, OwnershipError, ProtocolError
from jupyhop.lifecycle import lifecycle, require_lifecycle_ok, validate_managed_id
from jupyhop.selection import choose, describe_session, resolve_name, validate_name
from jupyhop.session_inventory import inspect_sessions, summary
from jupyhop.ssh import SSHTransport


def show_inventory(report: dict[str, Any], *, history: bool = False) -> None:
    counts = summary(report)
    display = {key: "unknown" if value is None else str(value) for key, value in counts.items()}
    archived = display["archived"]
    if counts["archived"] is not None and not counts["archive_count_exact"]:
        archived = f">={archived} (partial history)"
    print(
        f"{report['host']}: ready={display['ready']}  stopped awaiting archive={display['stopped']}  "
        f"review={display['review']}  unarchived={display['unarchived']}/128  archived={archived}"
    )
    for session in report["sessions"]:
        print(describe_session(session) + f"  {session['reason']}")
    if counts["stopped"]:
        print(
            "Stopped records still reserve names/slots. Use archive HOST, or manage HOST to select them."
        )
    if history and report["history"] is not None:
        for entry in report["history"]["entries"]:
            print(f"{entry['name']}  archived evidence  {entry['id']}  (not resumable)")
    if report["history"] is not None and report["history"]["next_offset"] is not None:
        print(
            f"More history: status {report['host']} --history --history-offset {report['history']['next_offset']}"
        )
    for key in ("error", "history_error"):
        if report[key] is not None:
            print(
                f"Session inventory: {report[key]}; affected counts are unavailable or partial.",
                file=sys.stderr,
            )


def show_lifecycle(report: dict[str, Any]) -> None:
    for session in report["servers"]:
        print(
            f"{session['id']}  managed  {session['name']}  {session['state']}  {session['reason']}"
        )
    if report.get("archived") is not None:
        print(f"Archived {report['archived']['id']} -> {report['archived']['path']}")
    elif not report["servers"]:
        print("No managed session records found in this host/account registry.")


def select_managed(
    report: dict[str, Any], operation: str, *, name: str | None, interactive: bool
) -> dict[str, Any]:
    if not report["complete"] or report["error"] is not None:
        raise ProtocolError(
            "Managed inventory is incomplete/unavailable; no lifecycle target was selected."
        )
    if name is not None:
        return resolve_name(report["sessions"], name)
    eligible = [
        s
        for s in report["sessions"]
        if (
            s["state"] in {"stopped", "stale", "failed"}
            if operation == "archive"
            else s["state"] not in {"stopped", "stale"}
        )
    ]
    return choose(eligible, describe_session, interactive=interactive)


def confirm(operation: str, sid: str, name: str | None, *, archive_after: bool) -> None:
    target = f"{name} ({sid})" if name else sid
    if operation == "stop":
        text = f"Stop {'and archive ' if archive_after else ''}managed session {target}? This terminates all its kernels and computations. "
        if archive_after:
            text += "After confirmed stop, retain evidence in the archive and release its name. "
    else:
        text = f"Archive inactive session {target}? Evidence is retained; orphaned kernels are not stopped. "
    print(text + f"Type {operation} to confirm: ", end="", file=sys.stderr, flush=True)
    if sys.stdin.readline().strip() != operation:
        raise OwnershipError("Lifecycle action cancelled; no stop or archive was authorized.")


def control(
    args: argparse.Namespace, transport: SSHTransport, *, operation: str | None = None
) -> int:
    operation = operation or args.command
    identifier = args.session
    name = args.selector_name
    interactive = not args.json and sys.stdin.isatty()
    if identifier is not None:
        validate_managed_id(identifier)
    if name is not None:
        validate_name(name)
    if operation == "status":
        if (
            args.history
            or args.history_offset
            or identifier is None
            and name is None
            and not args.json
        ):
            if identifier is not None or name is not None:
                raise ValueError("Choose a single session or --history, not both.")
            report = inspect_sessions(
                transport, python=args.remote_python, history_offset=args.history_offset
            )
            report["summary"] = summary(report)
            if args.json:
                print(json.dumps(report, ensure_ascii=True))
            else:
                show_inventory(report, history=args.history)
            if report["error"] is not None or report["history_error"] is not None:
                raise ProtocolError(
                    "Session inventory is unavailable or incomplete; inspect its diagnostics."
                )
            return 0
        if name is not None:
            observed = inspect_sessions(transport, python=args.remote_python)
            identifier = select_managed(observed, "status", name=name, interactive=False)["id"]
        report = lifecycle(transport, "status", identifier, python=args.remote_python)
        if args.json:
            print(json.dumps(report, ensure_ascii=True))
        else:
            show_lifecycle(report)
        require_lifecycle_ok(report)
        return 0
    if not interactive and not (args.yes and identifier is not None):
        raise OwnershipError(
            "Stopping terminates kernels/computations; archiving retains evidence. Supply an exact UUID and --yes, or use a terminal. No SSH command was sent."
        )
    if args.yes and identifier is None:
        raise OwnershipError(
            "Automated lifecycle actions require an exact managed UUID and --yes. No SSH command was sent."
        )
    if identifier is None:
        observed = inspect_sessions(transport, python=args.remote_python)
        selected = select_managed(observed, operation, name=name, interactive=interactive)
        identifier, name = selected["id"], selected["name"]
    archive_after = operation == "stop" and (
        args.archive_after or interactive and not args.yes and not args.keep_record
    )
    if not args.yes:
        confirm(operation, identifier, name, archive_after=archive_after)
    args.lifecycle_phase = operation
    result = lifecycle(transport, operation, identifier, python=args.remote_python)
    if not args.json:
        show_lifecycle(result)
    if not archive_after:
        if args.json:
            print(json.dumps(result, ensure_ascii=True))
        require_lifecycle_ok(result)
        return 0
    combined: dict[str, Any] = {
        "version": 1,
        "host": transport.host,
        "id": identifier,
        "stop": result,
        "archive": None,
    }
    try:
        require_lifecycle_ok(result)
        if not result["servers"] or any(s["state"] != "stopped" for s in result["servers"]):
            raise LifecycleError(
                "Stop is not confirmed stopped; no automatic archive was attempted. Inspect status."
            )
        args.lifecycle_phase = "archive"
        archived = lifecycle(transport, "archive", identifier, python=args.remote_python)
        combined["archive"] = archived
        require_lifecycle_ok(archived)
        if not args.json:
            show_lifecycle(archived)
    except JupyHopError as error:
        if args.json:
            combined["error"] = {"code": error.exit_code, "message": str(error)}
            print(json.dumps(combined, ensure_ascii=True))
        if args.lifecycle_phase == "archive":
            raise LifecycleError(
                f"Session {identifier} was stopped; archival could not be confirmed. Retry archive on the same UUID; the archive may already exist. {error}"
            ) from None
        raise
    if args.json:
        print(json.dumps(combined, ensure_ascii=True))
    return 0
