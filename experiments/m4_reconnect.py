"""Independent client-process/key/HOME reconnection on disposable loopback SSH.

Run as a module. The private worker accepts synthetic credentials only on stdin.
No prior cookies, ports, SSH control sockets or local JupyHop state are copied.
"""

import argparse
import getpass
import json
import os
import subprocess
import sys
from pathlib import Path

from experiments.lab import SSHLab
from experiments.m0_spike import execute
from experiments.managed_fixture import ManagedFixture
from jupyhop.discovery import discover, select_server
from jupyhop.lifecycle import lifecycle, require_lifecycle_ok
from jupyhop.opening import open_connection
from jupyhop.ssh import SSHTransport


def independent_client(lab, label, *, jump):
    root = lab.root / label
    root.mkdir(mode=0o700)
    key = root / "identity"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "fixture", "-f", str(key)], check=True
    )
    with lab.authorized.open("ab") as stream:
        stream.write(key.with_suffix(".pub").read_bytes())
    known = root / "known_hosts"
    known.write_bytes((lab.root / "known_hosts").read_bytes())
    config = root / "ssh_config"
    config.write_text(f"""Host remote
    HostName 127.0.0.1
    Port {lab.ports[1]}
    {"ProxyJump gateway" if jump else ""}
Host gateway
    HostName 127.0.0.1
    Port {lab.ports[0]}
Host *
    User {getpass.getuser()}
    IdentityFile {key}
    IdentitiesOnly yes
    UserKnownHostsFile {known}
    GlobalKnownHostsFile /dev/null
    StrictHostKeyChecking yes
    BatchMode yes
    ConnectTimeout 5
""")
    return config


def worker_client(config, sid, password, *, create=False, kernel=None):
    environment = dict(
        os.environ,
        HOME=str(config.parent),
        PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src")
        + os.pathsep
        + str(Path(__file__).resolve().parents[1]),
    )
    result = subprocess.run(
        [sys.executable, "-m", "experiments.m4_reconnect", "--worker", str(config), sid],
        input=json.dumps({"password": password, "create": create, "kernel": kernel}).encode(),
        capture_output=True,
        timeout=45,
        env=environment,
    )
    if result.returncode:
        raise RuntimeError("Independent client failed; raw output suppressed")
    return json.loads(result.stdout)


def worker(config, sid, request):
    import requests

    transport = SSHTransport("remote", config=config, timeout=30)
    report = discover(transport)
    server = select_server(report, sid, interactive=False)
    with open_connection(transport, report, server) as (tunnel, _):
        base = f"http://127.0.0.1:{tunnel.local_port}{server['base_url']}"
        with requests.Session() as client:
            client.trust_env = False
            client.get(base + "login", timeout=3)
            client.post(
                base + "login",
                data={"_xsrf": client.cookies.get("_xsrf"), "password": request["password"]},
                timeout=3,
            )
            client.headers["X-XSRFToken"] = client.cookies.get("_xsrf") or ""
            if request["create"]:
                response = client.post(
                    base + "api/sessions",
                    json={
                        "path": "continuity.ipynb",
                        "type": "notebook",
                        "name": "continuity",
                        "kernel": {"name": "python3"},
                    },
                    timeout=15,
                )
                response.raise_for_status()
                session = response.json()
                kernel = session["kernel"]["id"]
                code = """import threading, os
continuity_marker = 42
progress = []
compute_started = threading.Event()
continue_compute = threading.Event()
compute_done = threading.Event()
def compute():
    compute_started.set()
    if continue_compute.wait(60):
        progress.append(continuity_marker)
        compute_done.set()
threading.Thread(target=compute, daemon=True).start()
assert compute_started.wait(5) and not compute_done.is_set()
print(os.getpid())
"""
            else:
                sessions = client.get(base + "api/sessions", timeout=5)
                sessions.raise_for_status()
                session = next(
                    (s for s in sessions.json() if s["path"] == "continuity.ipynb"), None
                )
                kernel = request.get("kernel") or session["kernel"]["id"]
                code = (
                    "print(continuity_marker)"
                    if request.get("kernel")
                    # The first worker has exited with every connection closed.
                    # Release its surviving background computation from this
                    # independent client; no fixed reconnect duration is assumed.
                    else "continue_compute.set()\nassert compute_done.wait(5)\nprint(continuity_marker, progress)"
                )
            cookie = "; ".join(f"{c.name}={c.value}" for c in client.cookies)
            output = execute(base, "", kernel, code, cookie=cookie).strip()
            return {
                "kernel": kernel,
                "session": session["id"] if session else None,
                "output": output,
                "pid": server["pid"],
            }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("sid", nargs="?")
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker, args.sid, json.load(sys.stdin))))
        return
    with SSHLab() as lab, ManagedFixture(lab, name="continuity") as fixture:
        manager = lab.ssh("direct", ["systemctl", "--user", "is-active", "default.target"])
        print(
            "OBSERVED: remote systemd user manager "
            + (
                "available"
                if manager.returncode == 0
                else "unavailable in no-PAM fixture; tmux fallback tested"
            )
        )
        a = independent_client(lab, "client-a", jump=True)
        b = independent_client(lab, "client-b", jump=False)
        first = worker_client(a, fixture.sid, fixture.password, create=True)
        second = worker_client(b, fixture.sid, fixture.password)
        assert first["kernel"] == second["kernel"] and first["session"] == second["session"]
        assert first["pid"] == second["pid"] == fixture.record["pid"]
        assert second["output"] == "42 [42]"
        print(
            "PASS: independent processes/keys/HOMEs/routes retain notebook session, kernel and memory/computation after all first-client connections close"
        )
        result = lifecycle(SSHTransport("remote", config=b), "stop", fixture.sid)
        require_lifecycle_ok(result)
        assert result["servers"][0]["state"] == "stopped"
        print("PASS: independent client safely stops the same managed server")


if __name__ == "__main__":
    main()
