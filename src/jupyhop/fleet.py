"""Bounded multi-alias inventory; failures remain explicit per SSH route."""

from pathlib import Path
from typing import Any

from jupyhop.config import Config
from jupyhop.discovery import discover
from jupyhop.errors import JupyHopError, SelectionError
from jupyhop.ssh import SSHTransport, validate_alias


def inventory(
    config: Config,
    hosts: list[str] | None = None,
    *,
    ssh_config: Path | None = None,
    timeout: float = 20,
    pythons: list[str] | None = None,
    paths: list[str] | None = None,
) -> dict[str, Any]:
    names = list(dict.fromkeys(hosts or config.hosts))
    if not 1 <= len(names) <= 16:
        raise ValueError("Supply 1–16 explicit SSH aliases or configure [hosts.ALIAS] entries.")
    for host in names:
        validate_alias(host)
    # Validate all local arguments before sending any SSH request.
    prepared = [
        (
            SSHTransport(host, config=ssh_config, timeout=timeout),
            config.discovery_options(host, pythons, paths),
        )
        for host in names
    ]
    reports = []
    for transport, (interpreters, directories) in prepared:
        try:
            report = discover(transport, interpreters, directories)
            reports.append({"host": transport.host, "ok": True, "report": report, "error": None})
        except JupyHopError as error:
            reports.append(
                {
                    "host": transport.host,
                    "ok": False,
                    "report": None,
                    "error": {"code": error.exit_code, "message": str(error)},
                }
            )
    return {"version": 1, "complete": False, "hosts": reports}


def select_inventory(
    data: dict[str, Any], *, interactive: bool
) -> tuple[dict[str, Any], dict[str, Any]]:
    import sys

    candidates = [
        (entry["report"], server)
        for entry in data["hosts"]
        if entry["ok"]
        for server in entry["report"]["servers"]
        if server["state"] == "ready"
    ]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise SelectionError(
            "No verified candidate found across the selected aliases; inspect list --json. Failed or partial discovery does not prove no servers exist."
        )
    if not interactive:
        raise SelectionError(
            "Multiple servers/SSH routes found. Use list --json, then open HOST ID; no route was selected."
        )
    for index, (report, server) in enumerate(candidates, 1):
        print(
            f"{index}: {report['host']}  {server['id']}  {server['origin']}  {server.get('name') or ''}",
            file=sys.stderr,
        )
    print("Select a server number: ", end="", file=sys.stderr, flush=True)
    value = sys.stdin.readline().strip()
    if not value.isascii() or not value.isdigit() or not 1 <= int(value) <= len(candidates):
        raise SelectionError("Invalid selection; use open HOST ID.")
    return candidates[int(value) - 1]
