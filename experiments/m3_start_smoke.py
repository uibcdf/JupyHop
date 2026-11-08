"""M3 managed start/open experiment against disposable loopback SSH only."""

import json
import subprocess
import sys

import requests

from experiments.lab import SSHLab
from jupyhop.discovery import discover, select_server
from jupyhop.managed import require_ready, start
from jupyhop.opening import open_connection
from jupyhop.ssh import SSHTransport


def main():
    with SSHLab() as lab:
        project = lab.home / "project α ; $(touch forbidden)"
        project.mkdir()
        transport = SSHTransport("destination", config=lab.config, timeout=35)
        try:
            launched = start(
                transport,
                server_python=sys.executable,
                workdir=str(project),
                name="experiment",
                password="fixture-password",
            )
            print("Observed launch:", launched["state"], launched["error"])
            require_ready(launched)
            report = discover(transport)
            server = select_server(report, launched["id"], interactive=False)
            assert server["origin"] == "managed"
            with open_connection(transport, report, server) as (tunnel, url):
                base = f"http://127.0.0.1:{tunnel.local_port}{server['base_url']}"
                with requests.Session() as client:
                    client.trust_env = False
                    client.get(url, timeout=3)
                    client.post(
                        url,
                        data={"_xsrf": client.cookies.get("_xsrf"), "password": "fixture-password"},
                        timeout=3,
                    )
                    assert client.get(base + "api/status", timeout=3).status_code == 200
            print(
                "PASS: managed registry, verified loopback listener, private tmux, normal password login and ProxyJump"
            )
        finally:
            for record_path in (lab.home / "state/jupyhop").glob("hosts/*/sessions/*/record.json"):
                record = json.loads(record_path.read_text())
                subprocess.run(
                    ["tmux", "-S", record["socket"], "kill-server"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            for settings_path in (lab.home / "state/jupyhop").glob(
                "hosts/*/sessions/*/settings.json"
            ):
                assert "fixture-password" not in settings_path.read_text()


if __name__ == "__main__":
    main()
