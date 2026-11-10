"""Read-only current-account discovery and explicit server selection."""

import json
from importlib.resources import files
from pathlib import PurePosixPath
from typing import Any, Protocol

from jupyhop.errors import DiscoveryError, PrerequisiteError, ProtocolError, SelectionError
from jupyhop.protocol import parse_discovery
from jupyhop.selection import choose, describe_session, resolve_name
from jupyhop.ssh import CommandResult, SSHTransport, ssh_failure


class ProbeConnection(Protocol):
    """A normal SSH command or a command on the owned forwarding connection."""

    def run(self, argv: list[str], *, stdin: bytes = b"") -> CommandResult: ...


def validate_python(path: str) -> str:
    if path != "python3" and (not PurePosixPath(path).is_absolute() or "\0" in path):
        raise ValueError("Remote Python must be python3 or an absolute remote executable path.")
    return path


def validate_paths(paths: list[str]) -> list[str]:
    if len(paths) > 16:
        raise ValueError("At most 16 additional runtime directories may be supplied.")
    for path in paths:
        if (
            len(path) > 1024
            or any(ord(c) < 32 for c in path)
            or not (path.startswith("/") or path.startswith("~/"))
            or ".." in PurePosixPath(path).parts
        ):
            raise ValueError(
                "Runtime directories must be absolute remote paths or ~/ paths, without parent traversal or control characters."
            )
    return list(dict.fromkeys(paths))


def probe(
    connection: ProbeConnection, python: str, paths: list[str], timeout: float
) -> dict[str, Any]:
    request = json.dumps({"runtime_dirs": paths, "budget": min(10, max(0.5, timeout - 1))})
    result = connection.run(
        [validate_python(python), "-I", "-B", "-", request],
        stdin=files("jupyhop").joinpath("_managed_remote.py").read_bytes()
        + b"\n"
        + files("jupyhop").joinpath("_discovery_probe.py").read_bytes(),
    )
    if result.returncode == 255:
        raise ssh_failure(result.stderr)
    if result.returncode != 0:
        raise PrerequisiteError(
            "Discovery probe could not run. Select an existing Linux Python >=3.11 with --remote-python /absolute/path/to/python. No remote installation was attempted."
        )
    report = parse_discovery(result.stdout)
    if "probe_failed" in report["data"]["issues"]:
        raise PrerequisiteError(
            "Remote discovery prerequisites could not be verified. Linux /proc and Python >=3.11 are required; check doctor and the selected runtime paths."
        )
    data: dict[str, Any] = report["data"]
    return data


def discover(
    transport: SSHTransport, pythons: list[str] | None = None, runtime_dirs: list[str] | None = None
) -> dict[str, Any]:
    pythons = list(dict.fromkeys(pythons or ["python3"]))
    if len(pythons) > 8:
        raise ValueError("At most eight explicit remote interpreters may be probed.")
    for python in pythons:
        validate_python(python)
    paths = validate_paths(runtime_dirs or [])
    identity = None
    known_paths: list[dict[str, str]] = []
    servers: dict[str, dict[str, Any]] = {}
    issues = []
    for python in pythons:
        try:
            data = probe(transport, python, paths, transport.timeout)
        except PrerequisiteError:
            if len(pythons) == 1:
                raise
            issues.append("interpreter_unavailable")
            continue
        if identity is not None and identity != data["identity"]:
            raise ProtocolError(
                "SSH alias resolved to different remote account/host identities across probes. No servers were opened."
            )
        identity = data["identity"]
        for path in data["paths"]:
            if path not in known_paths:
                known_paths.append(path)
        issues.extend(data["issues"])
        for server in data["servers"]:
            previous = servers.get(server["id"])
            if previous is None:
                servers[server["id"]] = server
            else:
                previous["sources"] = list(dict.fromkeys(previous["sources"] + server["sources"]))
    if identity is None:
        raise PrerequisiteError(
            "None of the selected remote interpreters could run discovery. Use doctor with an existing Python >=3.11."
        )
    return {
        "host": transport.host,
        "identity": identity,
        "coverage": {
            "complete": False,
            "paths": known_paths,
            "issues": list(dict.fromkeys(issues)),
        },
        "servers": sorted(servers.values(), key=lambda item: item["id"]),
    }


def select_server(
    report: dict[str, Any], identifier: str | None, *, interactive: bool, name: str | None = None
) -> dict[str, Any]:
    if identifier is not None and name is not None:
        raise ValueError("Choose an exact ID or --name, not both.")
    candidates: list[dict[str, Any]] = [s for s in report["servers"] if s["state"] == "ready"]
    if name is not None:
        return resolve_name(candidates, name)
    if identifier is not None:
        candidates = [s for s in candidates if s["id"] == identifier]
        if not candidates:
            raise DiscoveryError(
                "Selected ID is absent or no longer verified. Run discover again; remote state was not changed."
            )
    if not candidates:
        raise DiscoveryError(
            "No verified server found in the searched paths. Discovery is partial: select a known environment with --remote-python or add --runtime-dir. This does not prove no servers are running."
        )
    if len(candidates) > 1 and not interactive:
        raise SelectionError(
            "Multiple verified servers found. Use discover --json, then open HOST ID; no server was selected."
        )
    return choose(
        candidates, describe_session, interactive=interactive, explicit=identifier is not None
    )
