"""Allowlisted support reports. Never collect identities, paths or scientific data."""

import re
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from jupyhop import __version__
from jupyhop.doctor import diagnose
from jupyhop.errors import JupyHopError
from jupyhop.ssh import SSHTransport, _run_bounded


def _numeric_version(value: str | None) -> str | None:
    match = re.match(r"[0-9]+(?:\.[0-9]+){1,3}", (value or "")[:64])
    return match[0] if match else None


def _package_version(name: str) -> str | None:
    try:
        return _numeric_version(version(name))
    except (PackageNotFoundError, ValueError, OSError):
        return None


def _platform() -> str:
    return sys.platform if sys.platform in {"linux", "darwin", "win32"} else "other"


def client_report() -> dict[str, Any]:
    """Local prerequisites only; ssh -V does not connect or inspect SSH config."""
    openssh = None
    try:
        result = _run_bounded(["ssh", "-V"], b"", 2)
        match = re.search(rb"OpenSSH_([0-9]+(?:\.[0-9]+){1,3})", result.stderr[:4096])
        if match is not None:
            openssh = match[1].decode("ascii")
    except (OSError, JupyHopError):
        pass
    return {
        "jupyhop": _numeric_version(__version__),
        "python": ".".join(str(part) for part in sys.version_info[:3]),
        "platform": _platform(),
        "openssh": openssh,
    }


def kernel_report() -> dict[str, Any]:
    """Optional notebook API: runs in this kernel, never via SSH.

    Importing this API needs JupyHop in the kernel environment. Ordinary remote
    discovery/management never requires that installation. Package metadata is
    observed without importing Jupyter, starting kernels or reading user config.
    """
    return {
        "report_version": 1,
        "context": "notebook-kernel",
        "python": ".".join(str(part) for part in sys.version_info[:3]),
        "platform": _platform(),
        "packages": {
            name: _package_version(name)
            for name in ("jupyhop", "ipykernel", "jupyter_client", "jupyter_server", "jupyterlab")
        },
        "coverage": "current-interpreter-package-metadata-only",
    }


def support_report(transport: SSHTransport, remote_python: str) -> tuple[dict[str, Any], int]:
    report: dict[str, Any] = {
        "report_version": 1,
        "context": "ssh-client-and-selected-remote-interpreter",
        "client": client_report(),
        "remote": None,
        "outcome": None,
        "privacy": "Identities, addresses, paths, credentials and scientific data are excluded. Review before sharing; nothing is uploaded.",
    }
    try:
        diagnosis = diagnose(transport, remote_python)
    except JupyHopError as error:
        code = error.exit_code
        stages = {
            3: (
                "ssh",
                "Check ordinary SSH access, host trust, configuration permissions and native authentication. Remote state is unknown.",
            ),
            4: (
                "remote-prerequisites",
                "Check the selected Linux Python >=3.11 and required Jupyter packages; no remote installation was attempted.",
            ),
            5: (
                "remote-protocol",
                "Check helper compatibility and clean remote shell startup output; raw output was suppressed.",
            ),
        }
        stage, advice = stages.get(
            code,
            (
                "remote-probe",
                "The selected probe did not complete; inspect the private command feedback.",
            ),
        )
        report["outcome"] = {"ok": False, "code": code, "stage": stage, "advice": advice}
        return report, code
    data = diagnosis["data"]
    report["remote"] = {
        "python": _numeric_version(data["python"]["version"]),
        "python_supported": data["python"]["supported"],
        "jupyter_server": _numeric_version(data["jupyter_server"]["version"]),
        "jupyter_core": _numeric_version(data["jupyter_core"]["version"]),
        "runtime_statuses": [entry["status"] for entry in data["runtime_dirs"]],
        "process_managers": {
            "systemd_user": data["process_managers"]["systemd_user"],
            "tmux": data["process_managers"]["tmux"],
        },
        "coverage": "selected-interpreter-only; no kernel executed or discovered",
    }
    code = 0 if diagnosis["ok"] else 4
    report["outcome"] = {
        "ok": diagnosis["ok"],
        "code": code,
        "stage": "remote-prerequisites",
        "advice": "Prerequisites checked; this does not prove server/kernel health or persistence."
        if code == 0
        else "Select an existing environment providing the required Jupyter packages. Nothing was installed remotely.",
    }
    return report, code
