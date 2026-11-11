"""Bounded multi-alias inventory; failures remain explicit per SSH route."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from jupyhop.config import Config
from jupyhop.discovery import discover
from jupyhop.errors import JupyHopError, SelectionError
from jupyhop.selection import choose, describe_session, validate_name
from jupyhop.ssh import SSHTransport, validate_alias

if TYPE_CHECKING:
    from jupyhop.connection import ConnectionPool


def inventory(
    config: Config,
    hosts: list[str] | None = None,
    *,
    ssh_config: Path | None = None,
    timeout: float = 20,
    pythons: list[str] | None = None,
    paths: list[str] | None = None,
    connections: "ConnectionPool | None" = None,
) -> dict[str, Any]:
    names = list(dict.fromkeys(hosts or config.hosts))
    if not 1 <= len(names) <= 16:
        raise ValueError("Supply 1–16 explicit SSH aliases or configure [hosts.ALIAS] entries.")
    for host in names:
        validate_alias(host)
    # Validate all local arguments before sending any SSH request.
    prepared = [
        (
            SSHTransport(host, config=ssh_config, timeout=timeout, connections=connections),
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
    data: dict[str, Any], *, interactive: bool, name: str | None = None, verbose: bool = False
) -> tuple[dict[str, Any], dict[str, Any]]:
    if name is not None:
        validate_name(name)
    candidates = [
        (entry["report"], server)
        for entry in data["hosts"]
        if entry["ok"]
        for server in entry["report"]["servers"]
        if server["state"] == "ready"
        and (name is None or server.get("name") == name and server["origin"] == "managed")
    ]
    if not candidates:
        raise SelectionError(
            "No verified candidate found across the selected aliases; inspect list --json. Failed or partial discovery does not prove no servers exist."
        )
    return choose(
        candidates,
        lambda item: f"{item[0]['host']}  {describe_session(item[1], verbose=verbose)}",
        interactive=interactive,
        explicit=name is not None and len(candidates) == 1,
    )
