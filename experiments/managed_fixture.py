"""Lifecycle of sessions created only inside a disposable SSHLab."""

import json
import subprocess
import sys
from pathlib import Path

import requests

from jupyhop._discovery_probe import process_identity
from jupyhop.managed import new_id, require_ready, start
from jupyhop.ssh import SSHTransport


class ManagedFixture:
    def __init__(
        self,
        lab,
        *,
        name=None,
        workdir="~",
        server_python=None,
        helper_python="python3",
        timeout=40,
    ):
        self.lab = lab
        self.sid = new_id()
        self.password = "fixture-password"
        self.transport = SSHTransport("destination", config=lab.config, timeout=timeout)
        self.parameters = dict(
            name=name,
            workdir=workdir,
            server_python=server_python or sys.executable,
            helper_python=helper_python,
            password=self.password,
            session_id=self.sid,
        )
        self.record = None

    def launch(self):
        try:
            self.report = start(self.transport, **self.parameters)
            return self.report
        finally:
            paths = list(
                (self.lab.home / "state/jupyhop").glob(f"hosts/*/sessions/{self.sid}/record.json")
            )
            if paths:
                self.record_path = paths[0]
                self.record = json.loads(paths[0].read_text())
                if self.record.get("port"):
                    self.base = self.record["base_url"]
                    self.url = f"http://127.0.0.1:{self.record['port']}{self.base}"

    def __enter__(self):
        try:
            require_ready(self.launch())
            return self
        except BaseException:
            self.close()
            raise

    def client(self, base=None, *, password=None):
        base = base or self.url
        client = requests.Session()
        client.trust_env = False
        client.get(base + "login", timeout=3)
        client.post(
            base + "login",
            data={
                "_xsrf": client.cookies.get("_xsrf"),
                "password": self.password if password is None else password,
            },
            timeout=3,
        )
        client.headers["X-XSRFToken"] = client.cookies.get("_xsrf") or ""
        return client

    def close(self):
        if self.record is None:
            return
        if self.record.get("pid") and self.record.get("port"):
            try:
                if process_identity(self.record["pid"]) == self.record["process_start"]:
                    with self.client() as client:
                        result = client.get(self.url + "api/kernels", timeout=2)
                        if result.status_code == 200:
                            for kernel in result.json():
                                client.delete(self.url + "api/kernels/" + kernel["id"], timeout=5)
            except (OSError, ValueError, requests.RequestException):
                pass
        socket = Path(self.record["socket"])
        if socket.parent == self.lab.run / "jupyhop" and socket.name == self.sid + ".sock":
            subprocess.run(
                ["tmux", "-S", str(socket), "kill-server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )

    def __exit__(self, *args):
        self.close()
