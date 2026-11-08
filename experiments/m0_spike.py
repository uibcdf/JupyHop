"""Run with python -m experiments.m0_spike --second-python /absolute/python.

Only generated loopback SSH servers and private temporary Jupyter/tmux instances
are touched. Output contains assertions and versions, never runtime records.
"""

import argparse
import importlib.metadata
import json
import os
import shlex
import socket
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager

import requests
import websocket
from jupyter_client.session import Session

from experiments.lab import SSHLab, stop


def check(condition, label):
    if not condition:
        raise RuntimeError(f"FAIL: {label}")
    print(f"PASS: {label}", flush=True)


@contextmanager
def server(lab, python, label, password=False):
    root = lab.root / label
    root.mkdir(mode=0o700)
    runtime = root / "runtime"
    config = root / "config"
    data = root / "data"
    for directory in (runtime, config, data):
        directory.mkdir(mode=0o700)
    kernel = data / "kernels" / "python3"
    kernel.mkdir(parents=True)
    (kernel / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [python, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                "display_name": "fixture",
                "language": "python",
            }
        )
    )
    cfg = config / "jupyter_server_config.py"
    text = """c.ServerApp.ip = '127.0.0.1'
c.ServerApp.port = 0
c.ServerApp.port_retries = 0
c.ServerApp.open_browser = False
c.ServerApp.base_url = '/science/'
c.ServerApp.jpserver_extensions = {}
c.ServerApp.shutdown_no_activity_timeout = 180
c.MappingKernelManager.cull_idle_timeout = 120
c.ServerApp.log_level = 'CRITICAL'
"""
    if password:
        from jupyter_server.auth import passwd

        text += f"c.PasswordIdentityProvider.hashed_password = {passwd('fixture-password')!r}\n"
    cfg.write_text(text)
    cfg.chmod(0o600)
    sock = root / "tmux.sock"
    command = [
        "env",
        f"HOME={root}",
        f"JUPYTER_CONFIG_DIR={config}",
        f"JUPYTER_DATA_DIR={data}",
        f"JUPYTER_RUNTIME_DIR={runtime}",
        python,
        "-m",
        "jupyter_server",
        f"--config={cfg}",
        f"--ServerApp.root_dir={root}",
    ]
    # Logs remain private and are never copied into result output.
    shell_command = shlex.join(command) + " >" + shlex.quote(str(root / "server.log")) + " 2>&1"
    launched = lab.ssh(
        "destination",
        ["tmux", "-S", str(sock), "new-session", "-d", "-s", "fixture", shell_command],
    )
    check(launched.returncode == 0, f"{label}: start private tmux over ProxyJump")
    try:
        deadline = time.monotonic() + 45
        info = None
        while time.monotonic() < deadline:
            files = list(runtime.glob("jpserver-*.json"))
            if files:
                try:
                    info = json.loads(files[0].read_text())
                    r = requests.get(
                        f"http://127.0.0.1:{info['port']}/science/api/status",
                        headers={"Authorization": f"token {info['token']}"},
                        timeout=2,
                    )
                    if r.status_code in (200, 403):
                        break
                except (ValueError, requests.RequestException):
                    pass
            time.sleep(0.1)
        else:
            raise RuntimeError(f"{label}: Jupyter readiness timeout; no secret logs emitted")
        check(
            info["hostname"] == "127.0.0.1" and info["port"] > 0,
            f"{label}: Jupyter allocates loopback ephemeral port",
        )
        check(
            files[0].stat().st_mode & 0o777 == 0o600,
            f"{label}: runtime record is mode 0600",
        )
        check(
            runtime.stat().st_mode & 0o777 == 0o700,
            f"{label}: runtime directory is mode 0700",
        )
        yield info, runtime
    finally:
        lab.ssh("direct", ["tmux", "-S", str(sock), "kill-server"])


def execute(base, token, kernel_id, code):
    url = (
        base.replace("http:", "ws:") + f"api/kernels/{kernel_id}/channels?session_id={uuid.uuid4()}"
    )
    ws = websocket.create_connection(
        url,
        header=[f"Authorization: token {token}"],
        origin=base.rstrip("/"),
        timeout=15,
    )
    try:
        message = Session().msg(
            "execute_request",
            {
                "code": code,
                "silent": False,
                "store_history": True,
                "user_expressions": {},
                "allow_stdin": False,
                "stop_on_error": True,
            },
        )
        ws.send(json.dumps(message, default=lambda value: value.isoformat()))
        observed = []
        while True:
            response = json.loads(ws.recv())
            if response.get("parent_header", {}).get("msg_id") != message["header"]["msg_id"]:
                continue
            if response["msg_type"] == "stream":
                observed.append(response["content"]["text"])
            if response["msg_type"] == "error":
                raise RuntimeError("Fixture kernel execution failed")
            if (
                response["msg_type"] == "status"
                and response["content"]["execution_state"] == "idle"
            ):
                return "".join(observed)
    finally:
        ws.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--second-python", required=True)
    args = parser.parse_args()
    print("Python", sys.version.split()[0])
    for dependency in (
        "jupyter_server",
        "jupyter_core",
        "ipykernel",
        "websocket-client",
    ):
        print(dependency, importlib.metadata.version(dependency))
    with SSHLab() as lab:
        for host in ("direct", "destination"):
            r = lab.ssh(host, ["id", "-u"])
            check(
                r.returncode == 0 and int(r.stdout) == os.getuid(),
                f"{host}: real OpenSSH and selected OS account",
            )
        payload = "spaces / Unicode α ; $(touch SHOULD_NOT_EXIST) `id` ' quotes"
        r = lab.ssh(
            "destination",
            [sys.executable, "-c", "import sys; print(sys.argv[1])", payload],
        )
        check(
            r.stdout.decode().strip() == payload,
            "remote shell quoting treats metacharacters as data",
        )
        with server(lab, sys.executable, "environment-a") as (info, runtime):
            token = info["token"]
            check(bool(token), "generated token present only in private runtime metadata")
            # Different executable environments do not imply different runtime dirs.
            values = []
            for python in (sys.executable, args.second_python):
                r = lab.ssh(
                    "direct",
                    [
                        "env",
                        f"HOME={lab.root}",
                        "JUPYTER_RUNTIME_DIR=",
                        python,
                        "-c",
                        "from jupyter_core.paths import jupyter_runtime_dir; print(jupyter_runtime_dir())",
                    ],
                )
                check(
                    r.returncode == 0,
                    "environment: jupyter_core available without shell activation",
                )
                values.append(r.stdout)
            check(
                values[0] == values[1],
                "two Conda interpreters share default runtime with same HOME",
            )
            check(
                str(runtime).encode() not in values[0],
                "custom runtime is invisible to another environment without explicit path",
            )
            # Jupyter's list API is unsuitable for read-only stale inspection.
            stale = runtime / "jpserver-stale.json"
            stale.write_text(json.dumps({"pid": 2147483647, "port": info["port"]}))
            stale.chmod(0o600)
            from jupyter_server.serverapp import list_running_servers

            list(list_running_servers(str(runtime)))
            check(
                not stale.exists(),
                "Jupyter list_running_servers deletes stale metadata (do not use for read-only discovery)",
            )
            tunnel, port = lab.tunnel("destination", info["port"])
            base = f"http://127.0.0.1:{port}/science/"
            check(
                requests.get(base + "api/status", timeout=3).status_code == 403,
                "unauthenticated API denied through jump",
            )
            check(
                requests.get(
                    base + "api/status",
                    headers={"Authorization": "token invalid"},
                    timeout=3,
                ).status_code
                == 403,
                "invalid token denied",
            )
            auth = {"Authorization": f"token {token}"}
            r = requests.post(
                base + "api/kernels", headers=auth, json={"name": "python3"}, timeout=15
            )
            check(
                r.status_code == 201,
                "authenticated kernel creation through ProxyJump and custom base URL",
            )
            kernel_id = r.json()["id"]
            try:
                check(
                    "12345"
                    in execute(
                        base,
                        token,
                        kernel_id,
                        "continuity_marker = 12345\nprint(continuity_marker)",
                    ),
                    "client A executes kernel over WebSocket",
                )
                # Login cookies can be established with a POST: no token URL needed.
                client = requests.Session()
                client.get(base + "login", timeout=3)
                xsrf = client.cookies.get("_xsrf")
                r = client.post(base + "login", data={"_xsrf": xsrf, "password": token}, timeout=3)
                check(
                    r.status_code == 200
                    and client.get(base + "api/status", timeout=3).status_code == 200,
                    "token POST establishes cookie without token in URL",
                )
                client.close()
                stop(tunnel)
                _, port_b = lab.tunnel("direct", info["port"])
                base_b = f"http://127.0.0.1:{port_b}/science/"
                check(
                    "12345" in execute(base_b, token, kernel_id, "print(continuity_marker)"),
                    "independent client B transport retains same kernel ID and memory",
                )
                with socket.socket() as occupied:
                    occupied.bind(("127.0.0.1", 0))
                    occupied.listen()
                    try:
                        lab.tunnel("direct", info["port"], occupied.getsockname()[1])
                    except RuntimeError:
                        check(True, "ExitOnForwardFailure rejects occupied local port")
                    else:
                        raise RuntimeError("Collision was not rejected")
                _, port_c = lab.tunnel("destination", info["port"])
                check(port_b != port_c, "concurrent forwards use independent ports")
                requests.delete(
                    base_b + f"api/kernels/{kernel_id}", headers=auth, timeout=10
                ).raise_for_status()
            finally:
                # Fixture-only cleanup if assertion failed before explicit deletion.
                requests.delete(
                    f"http://127.0.0.1:{info['port']}/science/api/kernels/{kernel_id}",
                    headers=auth,
                    timeout=10,
                )
            with server(lab, args.second_python, "environment-b", password=True) as (
                other,
                _,
            ):
                check(
                    other["port"] != info["port"],
                    "concurrent Jupyter servers allocate distinct remote ports",
                )
                check(
                    other["token"] == "",
                    "password server has no retrievable token; login fallback required",
                )
                print(
                    "OBSERVED: legacy runtime password flag",
                    bool(other["password"]),
                    "(not an authentication authority)",
                )
                login = requests.Session()
                url = f"http://127.0.0.1:{other['port']}/science/"
                login.get(url + "login", timeout=3)
                login.post(
                    url + "login",
                    data={
                        "_xsrf": login.cookies.get("_xsrf"),
                        "password": "fixture-password",
                    },
                    timeout=3,
                )
                check(
                    login.get(url + "api/status", timeout=3).status_code == 200,
                    "password login preserves normal Jupyter authentication",
                )
                login.close()
        # Probe only: do not modify linger, user services, or reboot this machine.
        r = subprocess.run(
            ["systemctl", "--user", "is-active", "default.target"],
            check=False,
            capture_output=True,
            timeout=5,
        )
        print(
            "OBSERVED: systemd user manager",
            "available" if r.returncode == 0 else "unavailable",
        )
        if r.returncode == 0:
            unit = "jupyhop-spike-" + uuid.uuid4().hex
            try:
                run = lab.ssh(
                    "direct",
                    [
                        "systemd-run",
                        "--user",
                        f"--unit={unit}",
                        "--collect",
                        "--property=Restart=no",
                        "/bin/sleep",
                        "60",
                    ],
                )
                if run.returncode == 0:
                    check(
                        True,
                        "disposable systemd user unit starts via SSH without linger changes",
                    )
                    state = subprocess.run(
                        ["systemctl", "--user", "is-active", unit],
                        check=False,
                        capture_output=True,
                        timeout=5,
                    )
                    check(
                        state.returncode == 0,
                        "systemd unit survives launching SSH command exit",
                    )
                else:
                    print(
                        "OBSERVED: systemd user service unavailable through disposable no-PAM SSH; local availability is insufficient"
                    )
            finally:
                subprocess.run(
                    ["systemctl", "--user", "stop", unit],
                    check=False,
                    capture_output=True,
                    timeout=5,
                )
        print("NOT TESTED: final OS logout/linger, real reboot, cross-user isolation, GUI browser")
    print("M0 isolated spike complete; all fixture processes cleaned up")


if __name__ == "__main__":
    main()
