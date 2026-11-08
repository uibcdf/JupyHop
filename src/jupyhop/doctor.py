"""Diagnostics only: no server discovery, forward, install, or registry mutation."""

from importlib.resources import files
from pathlib import PurePosixPath
from typing import Any

from jupyhop.errors import PrerequisiteError
from jupyhop.protocol import parse_doctor
from jupyhop.ssh import SSHTransport, ssh_failure


def diagnose(transport: SSHTransport, remote_python: str = "python3") -> dict[str, Any]:
    if remote_python != "python3" and (
        not PurePosixPath(remote_python).is_absolute() or "\0" in remote_python
    ):
        raise ValueError("Remote Python must be python3 or an absolute remote executable path.")
    source = files("jupyhop").joinpath("_probe.py").read_bytes()
    result = transport.run([remote_python, "-I", "-B", "-"], stdin=source)
    if result.returncode == 255:
        raise ssh_failure(result.stderr)
    if result.returncode != 0:
        raise PrerequisiteError(
            "Remote Python probe could not run. Check python3 or pass --remote-python /absolute/environment/bin/python; a POSIX login shell and Python >=3.11 are required."
        )
    report = parse_doctor(result.stdout)
    report["host"] = transport.host
    data = report["data"]
    missing = []
    if not data["python"]["supported"]:
        missing.append("Python >=3.11")
    for name in ("jupyter_server", "jupyter_core"):
        if data[name]["version"] is None:
            missing.append(name)
    report["ok"] = not missing
    report["missing"] = missing
    return report
