"""Read-only probe, sent as source to remote Python stdin. Stdlib at bootstrap."""

import importlib.metadata
import json
import os
import platform
import pwd
import shutil
import subprocess
import sys


def probe() -> dict[str, object]:
    def package_version(name: str) -> str | None:
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            return None

    server = package_version("jupyter_server")
    core = package_version("jupyter_core")
    dirs = []
    if core is not None:
        from jupyter_core.paths import jupyter_runtime_dir

        path = jupyter_runtime_dir()
        status = "missing"
        if os.path.isdir(path):
            status = "accessible" if os.access(path, os.R_OK | os.X_OK) else "inaccessible"
        dirs.append({"path": path, "source": "selected-python", "status": status})
    manager = "missing"
    if shutil.which("systemctl"):
        try:
            # Output goes to /dev/null: never read arbitrary journal/error output.
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "--quiet", "default.target"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=False,
            )
            manager = "available" if result.returncode == 0 else "unavailable"
        except (OSError, subprocess.TimeoutExpired):
            manager = "unavailable"
    return {
        "protocol": {"major": 1, "minor": 0},
        "operation": "doctor",
        "data": {
            "identity": {"uid": os.getuid(), "user": pwd.getpwuid(os.getuid()).pw_name},
            "python": {
                "version": platform.python_version(),
                "executable": sys.executable,
                "supported": sys.version_info >= (3, 11),
            },
            "jupyter_server": {"version": server},
            "jupyter_core": {"version": core},
            "runtime_dirs": dirs,
            "coverage": "selected-interpreter-only",
            "process_managers": {"systemd_user": manager, "tmux": bool(shutil.which("tmux"))},
        },
    }


if __name__ == "__main__":
    try:
        print(json.dumps(probe(), ensure_ascii=True))
    except Exception:
        print(
            "Read-only Python probe failed; verify interpreter and jupyter_core installation.",
            file=sys.stderr,
        )
        sys.exit(1)
