"""Install the built wheel in a fresh venv and diagnose a disposable SSH target.

Run `python -m build --no-isolation` first, then
`python -m experiments.package_smoke`. Requires ssh/sshd and loopback access.
The new local client has no Jupyter dependency; remote Python is this interpreter.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from experiments.lab import SSHLab


def main():
    wheels = list(Path("dist").glob("jupyhop-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("Expected exactly one built JupyHop wheel in dist")
    with SSHLab() as lab:
        venv = lab.root / "clean-client"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, capture_output=True)
        python = venv / "bin" / "python"
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                str(wheels[0].resolve()),
            ],
            check=True,
            capture_output=True,
        )
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        cli = str(venv / "bin" / "jupyhop")
        for argv in ([cli, "--help"], [cli, "--version"]):
            subprocess.run(argv, cwd=lab.root, env=environment, check=True, capture_output=True)
        subprocess.run(
            [
                str(python),
                "-I",
                "-c",
                "import importlib.util; assert importlib.util.find_spec('jupyter_server') is None",
            ],
            cwd=lab.root,
            check=True,
            capture_output=True,
        )
        result = subprocess.run(
            [
                cli,
                "doctor",
                "destination",
                "--ssh-config",
                str(lab.config),
                "--remote-python",
                sys.executable,
                "--json",
            ],
            cwd=lab.root,
            env=environment,
            check=True,
            capture_output=True,
        )
        report = json.loads(result.stdout)
        if not report["ok"] or report["data"]["identity"]["uid"] != os.getuid():
            raise RuntimeError("Installed wheel diagnostic failed")
    print("PASS: clean wheel client, no local Jupyter, console script, packaged probe, ProxyJump")


if __name__ == "__main__":
    main()
