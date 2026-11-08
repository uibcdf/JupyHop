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
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
        environment["XDG_CONFIG_HOME"] = str(lab.root / "isolated-client-config")
        venv = lab.root / "clean-client"
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv)],
            check=True,
            capture_output=True,
            env=environment,
        )
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
            env=environment,
        )
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
        client_config = lab.root / "jupyhop-config.toml"
        client_config.write_text(
            f'version = 1\n[profiles.research]\nserver_python = {json.dumps(sys.executable)}\nworkdir = "~"\n[hosts.destination]\nprofile = "research"\n'
        )
        client_config.chmod(0o600)
        listed = subprocess.run(
            [
                cli,
                "list",
                "direct",
                "destination",
                "--config",
                str(client_config),
                "--ssh-config",
                str(lab.config),
                "--json",
            ],
            cwd=lab.root,
            env=environment,
            check=True,
            capture_output=True,
        )
        fleet = json.loads(listed.stdout)
        if (
            fleet["version"] != 1
            or len(fleet["hosts"]) != 2
            or not all(h["ok"] for h in fleet["hosts"])
        ):
            raise RuntimeError("Installed wheel fleet inventory failed")
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
        managed_snapshot = None
        try:
            created = subprocess.run(
                [
                    cli,
                    "start",
                    "destination",
                    "--config",
                    str(client_config),
                    "--env",
                    "research",
                    "--ssh-config",
                    str(lab.config),
                    "--password-stdin",
                    "--no-open",
                    "--json",
                    "--timeout",
                    "40",
                    "--name",
                    "wheel-managed",
                ],
                input=b"fixture-password\n",
                cwd=lab.root,
                env=environment,
                check=True,
                capture_output=True,
                timeout=45,
            )
            launched = json.loads(created.stdout)
            if launched["state"] != "ready" or launched["server"]["origin"] != "managed":
                raise RuntimeError("Installed wheel managed start failed")
            managed_snapshot = json.loads(Path(launched["record_path"]).read_text())
            managed_open = subprocess.Popen(
                [
                    cli,
                    "open",
                    "destination",
                    launched["id"],
                    "--ssh-config",
                    str(lab.config),
                    "--no-browser",
                    "--json",
                ],
                cwd=lab.root,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(managed_open.stdout, selectors.EVENT_READ)
                    if not selector.select(20):
                        raise RuntimeError("Installed wheel managed open timed out")
                connection = json.loads(managed_open.stdout.readline())
                if connection["origin"] != "managed" or "token=" in connection["url"]:
                    raise RuntimeError("Installed wheel managed ownership check failed")
                managed_open.send_signal(signal.SIGINT)
                managed_open.communicate(timeout=10)
                if managed_open.returncode != 130:
                    raise RuntimeError("Installed wheel managed tunnel cleanup failed")
            finally:
                if managed_open.poll() is None:
                    os.killpg(managed_open.pid, signal.SIGKILL)
                    managed_open.communicate(timeout=5)
            for operation, extra, expected in (
                ("status", [], "ready"),
                ("stop", ["--yes"], "stopped"),
                ("stop", ["--yes"], "stopped"),
            ):
                result = subprocess.run(
                    [
                        cli,
                        operation,
                        "destination",
                        launched["id"],
                        "--ssh-config",
                        str(lab.config),
                        "--json",
                    ]
                    + extra,
                    cwd=lab.root,
                    env=environment,
                    capture_output=True,
                    check=True,
                    timeout=30,
                )
                report = json.loads(result.stdout)
                if report["error"] is not None or report["servers"][0]["state"] != expected:
                    raise RuntimeError("Installed wheel managed lifecycle failed")
            for _ in range(2):
                result = subprocess.run(
                    [
                        cli,
                        "archive",
                        "destination",
                        launched["id"],
                        "--yes",
                        "--ssh-config",
                        str(lab.config),
                        "--json",
                    ],
                    cwd=lab.root,
                    env=environment,
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
                report = json.loads(result.stdout)
                if report["archived"]["id"] != launched["id"]:
                    raise RuntimeError("Installed wheel archive failed")
        finally:
            if managed_snapshot is not None:
                subprocess.run(
                    ["tmux", "-S", managed_snapshot["socket"], "kill-server"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=5,
                )
    print(
        "PASS: clean wheel without local Jupyter, profiles/fleet inventory, existing-server access, start/open/status/stop/archive via ProxyJump and owned tunnel cleanup"
    )


if __name__ == "__main__":
    main()
