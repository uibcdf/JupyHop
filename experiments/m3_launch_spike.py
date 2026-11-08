"""Disposable M3 spike: isolated config, hashed password and direct tmux argv."""

import json
import sys
import time
from pathlib import Path

import requests
from jupyter_server.auth import passwd

from experiments.lab import SSHLab

RUNNER = """import json, os, sys
root=sys.argv[1]
os.environ['JUPYTER_RUNTIME_DIR']=root+'/runtime'
os.environ['JUPYTER_CONFIG_DIR']=root+'/config'
from jupyter_server.serverapp import ServerApp
from traitlets.config import Config
class ManagedServer(ServerApp):
    @property
    def config_file_paths(self):
        return [root + '/config']
with open(root + '/settings.json') as f:
    settings=json.load(f)
os.chdir(settings['workdir'])
app=ManagedServer.instance(config=Config(settings['config']))
app.initialize([], find_extensions=False)
app.start()
"""


def main():
    with SSHLab() as lab:
        root = lab.root / "managed"
        root.mkdir(mode=0o700)
        for name in ("runtime", "config"):
            (root / name).mkdir(mode=0o700)
        workdir = root / "project α #{{literal}} ; $(touch forbidden)"
        workdir.mkdir()
        runner = root / "launch.py"
        runner.write_text(RUNNER)
        config = {
            "ServerApp": {
                "ip": "127.0.0.1",
                "port": 0,
                "port_retries": 0,
                "open_browser": False,
                "root_dir": str(workdir),
                "base_url": "/spike/",
                "identity_provider_class": "jupyter_server.auth.identity.PasswordIdentityProvider",
                "jpserver_extensions": {"jupyterlab": True},
                "log_level": "CRITICAL",
            },
            "PasswordIdentityProvider": {
                "hashed_password": passwd("fixture-password"),
                "password_required": True,
                "token": "",
            },
        }
        settings = root / "settings.json"
        settings.write_text(json.dumps({"workdir": str(workdir), "config": config}))
        settings.chmod(0o600)
        sock = lab.root / "private.sock"
        tmux_config = root / "tmux.conf"
        tmux_config.write_text("setw -g remain-on-exit on\n")
        launched = lab.ssh(
            "destination",
            [
                "tmux",
                "-f",
                str(tmux_config),
                "-S",
                str(sock),
                "new-session",
                "-d",
                "-s",
                "fixture",
                "-c",
                "/",
                sys.executable,
                "-I",
                "-B",
                str(runner),
                str(root),
            ],
        )
        if launched.returncode:
            raise RuntimeError("Private tmux launch failed")
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                records = list((root / "runtime").glob("jpserver-*.json"))
                if records:
                    info = json.loads(records[0].read_text())
                    url = f"http://127.0.0.1:{info['port']}/spike/"
                    try:
                        if requests.get(url + "api", timeout=1).status_code == 200:
                            break
                    except requests.RequestException:
                        pass
                time.sleep(0.1)
            else:
                pane = lab.ssh(
                    "direct",
                    ["tmux", "-S", str(sock), "capture-pane", "-p", "-t", "fixture", "-S", "-80"],
                ).stdout.decode(errors="replace")
                pane = pane.replace(
                    config["PasswordIdentityProvider"]["hashed_password"], "<hash>"
                ).replace("fixture-password", "<credential>")
                raise RuntimeError(
                    "Private server readiness failed; sanitized fixture pane: " + pane[-2000:]
                )
            assert not info["token"] and info["hostname"] == "127.0.0.1"
            assert requests.get(url + "api/status", timeout=2).status_code == 403
            client = requests.Session()
            client.trust_env = False
            client.get(url + "login", timeout=2)
            client.post(
                url + "login",
                data={"_xsrf": client.cookies.get("_xsrf"), "password": "fixture-password"},
                timeout=2,
            )
            assert client.get(url + "api/status", timeout=2).status_code == 200
            assert Path(f"/proc/{info['pid']}/cwd").resolve() == workdir
            assert not (workdir / "forbidden").exists()
            assert client.get(url + "lab", timeout=3).status_code == 200
            client.close()
            print(
                "PASS: independent private tmux; literal remote workdir; isolated Jupyter config; password auth; no token; Lab available"
            )
        finally:
            lab.ssh("direct", ["tmux", "-S", str(sock), "kill-server"])


if __name__ == "__main__":
    main()
