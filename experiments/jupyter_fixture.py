"""Manually launched Jupyter confined to private fixture paths and loopback."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

from experiments.lab import stop


class JupyterFixture:
    def __init__(
        self,
        root: Path,
        *,
        runtime: Path | None = None,
        base="/science/",
        password=False,
        address="127.0.0.1",
        auth=True,
        python=None,
        lab=False,
    ):
        self.root = root
        root.mkdir(mode=0o700)
        self.runtime = runtime or root / "runtime"
        self.runtime.mkdir(mode=0o700, exist_ok=True)
        self.python = python or sys.executable
        self.base = base
        self.password = password
        self.address = address
        self.auth = auth
        self.lab = lab
        self.process = None

    def __enter__(self):
        config = self.root / "config.py"
        lines = [
            f"c.ServerApp.ip = {self.address!r}",
            "c.ServerApp.port = 0",
            "c.ServerApp.port_retries = 0",
            "c.ServerApp.open_browser = False",
            f"c.ServerApp.base_url = {self.base!r}",
            "c.ServerApp.log_level = 'CRITICAL'",
            "c.ServerApp.shutdown_no_activity_timeout = 180",
            f"c.ServerApp.root_dir = {str(self.root)!r}",
            "c.ServerApp.jpserver_extensions = " + ("{'jupyterlab': True}" if self.lab else "{}"),
        ]
        if self.password:
            from jupyter_server.auth import passwd

            lines.append(
                f"c.PasswordIdentityProvider.hashed_password = {passwd('fixture-password')!r}"
            )
        if not self.auth:
            lines.append("c.IdentityProvider.token = ''")
        if self.lab:
            lines.append("c.ServerApp.default_url = '/lab'")
        config.write_text("\n".join(lines) + "\n")
        config.chmod(0o600)
        self.data = self.root / "data"
        kernel = self.data / "kernels" / "python3"
        kernel.mkdir(parents=True)
        (kernel / "kernel.json").write_text(
            json.dumps(
                {
                    "argv": [self.python, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                    "display_name": "Fixture",
                    "language": "python",
                }
            )
        )
        environment = dict(
            os.environ,
            HOME=str(self.root),
            JUPYTER_RUNTIME_DIR=str(self.runtime),
            JUPYTER_DATA_DIR=str(self.data),
            JUPYTER_CONFIG_DIR=str(self.root / "config"),
        )
        self.log = open(self.root / "server.log", "wb")
        os.chmod(self.root / "server.log", 0o600)
        self.process = subprocess.Popen(
            [self.python, "-I", "-B", "-m", "jupyter_server", f"--config={config}"],
            env=environment,
            stdout=self.log,
            stderr=self.log,
            start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise RuntimeError(
                        "Fixture Jupyter exited; secret-bearing server logs are suppressed"
                    )
                files = list(self.runtime.glob(f"jpserver-{self.process.pid}.json"))
                if files:
                    try:
                        self.info = json.loads(files[0].read_text())
                        self.record = files[0]
                        self.port = self.info["port"]
                        self.url = f"http://127.0.0.1:{self.port}{self.base}"
                        if requests.get(self.url + "api/", timeout=1).status_code == 200:
                            return self
                    except (ValueError, requests.RequestException):
                        pass
                time.sleep(0.1)
            raise RuntimeError("Fixture Jupyter readiness timeout")
        except BaseException:
            self.close()
            raise

    def client(self, base=None):
        client = requests.Session()
        client.trust_env = False
        if self.password:
            url = base or self.url
            client.get(url + "login", timeout=3)
            client.post(
                url + "login",
                data={"_xsrf": client.cookies.get("_xsrf"), "password": "fixture-password"},
                timeout=3,
            )
        elif self.info["token"]:
            client.headers["Authorization"] = "token " + self.info["token"]
        return client

    def close(self):
        if self.process is not None and self.process.poll() is None and hasattr(self, "url"):
            try:
                with self.client() as client:
                    for kernel in client.get(self.url + "api/kernels", timeout=2).json():
                        client.delete(self.url + "api/kernels/" + kernel["id"], timeout=5)
            except (ValueError, requests.RequestException, TypeError, KeyError):
                pass
        if self.process is not None:
            stop(self.process)
        self.log.close()

    def __exit__(self, *args):
        self.close()
