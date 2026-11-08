"""Install the built wheel in a fresh venv and diagnose a disposable SSH target.

Run `python -m build --no-isolation` first, then
`python -m experiments.package_smoke`. Requires ssh/sshd and loopback access.
The new local client has no Jupyter dependency; remote Python is this interpreter.
"""

import json
import os
import selectors
import signal
import subprocess
import sys
from pathlib import Path

from experiments.jupyter_fixture import JupyterFixture
from experiments.lab import SSHLab


def main():
    wheels = list(Path("dist").glob("jupyhop-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("Expected exactly one built JupyHop wheel in dist")
    with SSHLab() as lab, JupyterFixture(lab.root / "manual", runtime=lab.runtime) as fixture:
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
        discovered = subprocess.run(
            [cli, "discover", "destination", "--ssh-config", str(lab.config), "--json"],
            cwd=lab.root,
            env=environment,
            check=True,
            capture_output=True,
        )
        if len([s for s in json.loads(discovered.stdout)["servers"] if s["state"] == "ready"]) != 1:
            raise RuntimeError("Installed wheel discovery failed")
        opened = subprocess.Popen(
            [cli, "open", "destination", "--ssh-config", str(lab.config), "--no-browser", "--json"],
            cwd=lab.root,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(opened.stdout, selectors.EVENT_READ)
                if not selector.select(20):
                    raise RuntimeError("Installed wheel open timed out")
            connection = json.loads(opened.stdout.readline())
            if connection["origin"] != "unmanaged" or "token=" in connection["url"]:
                raise RuntimeError("Installed wheel open result failed validation")
            opened.send_signal(signal.SIGINT)
            opened.communicate(timeout=10)
            if opened.returncode != 130 or fixture.process.poll() is not None:
                raise RuntimeError("Installed wheel tunnel cleanup failed")
        finally:
            if opened.poll() is None:
                os.killpg(opened.pid, signal.SIGKILL)
                opened.communicate(timeout=5)
    print(
        "PASS: clean wheel client without local Jupyter, doctor/discover/open via ProxyJump, packaged probes and owned tunnel cleanup"
    )


if __name__ == "__main__":
    main()
