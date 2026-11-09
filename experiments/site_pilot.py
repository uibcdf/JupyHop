"""Explicitly authorized Linux site pilot with exclusively owned toy resources.

The host and existing Python paths are operator inputs, never repository data.
No reboot/logout/network-policy operation is performed. SSH authentication and
host trust remain native. Synthetic passwords travel through encrypted stdin.
"""

import argparse
import json
import math
import os
import secrets
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

from experiments.client_upgrade import check_continuity, kernel_observation
from jupyhop.discovery import discover, select_server
from jupyhop.lifecycle import lifecycle, require_lifecycle_ok
from jupyhop.managed import new_id, require_ready, start
from jupyhop.opening import open_connection
from jupyhop.ssh import SSHTransport

MANUAL_SETUP = r"""
import json, os, re, shlex, socket, subprocess, sys
from pathlib import Path
from jupyter_server.auth import passwd
request = json.load(sys.stdin)
root = Path(request['root'])
assert root.parent == Path('/tmp') and re.fullmatch(r'jupyhop-site-[0-9a-f]{32}', root.name)
os.umask(0o077)
root.mkdir(mode=0o700)
(root / '.fixture').write_text(root.name)
for name in ('config', 'data', 'project'):
    (root / name).mkdir(mode=0o700)
with socket.socket() as channel:
    channel.bind(('127.0.0.1', 0))
    port = channel.getsockname()[1]
# This is an externally launched manual fixture, including older Jupyter whose
# native port=0 metadata is incorrect. It is not a product port allocator.
configuration = root / 'config/jupyter_server_config.py'
configuration.write_text("\n".join([
    "c.ServerApp.ip = '127.0.0.1'",
    f"c.ServerApp.port = {port}",
    "c.ServerApp.port_retries = 0",
    "c.ServerApp.open_browser = False",
    "c.ServerApp.base_url = '/pilot/'",
    "c.ServerApp.jpserver_extensions = {}",
    f"c.ServerApp.root_dir = {str(root / 'project')!r}",
    "c.ServerApp.log_level = 'CRITICAL'",
    "c.IdentityProvider.token = ''",
    f"c.PasswordIdentityProvider.hashed_password = {passwd(request['password'])!r}",
]) + "\n")
environment = {key: value for key, value in os.environ.items() if not key.startswith('JUPYTER_')}
environment.update(JUPYTER_CONFIG_DIR=str(root / 'config'), JUPYTER_DATA_DIR=str(root / 'data'))
data = os.environ.get('JUPYTER_DATA_DIR') or str(Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share') / 'jupyter')
environment['JUPYTER_RUNTIME_DIR'] = os.environ.get('JUPYTER_RUNTIME_DIR') or str(Path(data) / 'runtime')
command = 'exec ' + shlex.join([sys.executable, '-m', 'jupyter_server', '--config=' + str(configuration)])
command += ' >' + shlex.quote(str(root / 'server.log')) + ' 2>&1'
subprocess.run(['tmux', '-S', str(root / 'manual.sock'), 'new-session', '-d', '-s', 'pilot', command], env=environment, check=True, capture_output=True)
pid = int(subprocess.run(['tmux', '-S', str(root / 'manual.sock'), 'display-message', '-p', '#{pane_pid}'], check=True, capture_output=True).stdout)
(root / 'pid').write_text(str(pid))
print(json.dumps({'pid': pid}))
"""

MANUAL_CLEANUP = r"""
import json, os, re, shutil, stat, subprocess, sys, time
from pathlib import Path
request = json.load(sys.stdin)
root = Path(request['root'])
assert root.parent == Path('/tmp') and re.fullmatch(r'jupyhop-site-[0-9a-f]{32}', root.name)
try:
    info = root.lstat()
except FileNotFoundError:
    print(json.dumps({'removed': True}))
    raise SystemExit(0)
assert stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077
assert (root / '.fixture').read_text() == root.name
sock = root / 'manual.sock'
if sock.exists():
    info = sock.lstat()
    assert stat.S_ISSOCK(info.st_mode) and info.st_uid == os.getuid()
    subprocess.run(['tmux', '-S', str(sock), 'kill-server'], check=False, capture_output=True, timeout=5)
pid_file = root / 'pid'
if pid_file.is_file():
    pid = int(pid_file.read_text())
    deadline = time.monotonic() + 5
    while True:
        try:
            # A live process is never signalled by PID. Retain evidence if the
            # owned tmux shutdown did not finish; no forced-kill fallback.
            state = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0]
            if state == 'Z':
                break
        except FileNotFoundError:
            break
        assert time.monotonic() < deadline, 'Manual fixture remains alive; evidence retained'
        time.sleep(0.1)
if request['remove']:
    shutil.rmtree(root)
print(json.dumps({'removed': request['remove']}))
"""


def remote_fixture(transport, python, source, request):
    result = transport.run([python, "-I", "-c", source], stdin=json.dumps(request).encode())
    if result.returncode:
        raise RuntimeError("Site fixture command failed; raw output suppressed")
    return json.loads(result.stdout)


def worker(host, sid, request):
    transport = SSHTransport(
        host, config=Path(request["ssh_config"]) if request.get("ssh_config") else None, timeout=40
    )
    report = discover(transport, [request["helper_python"]])
    server = select_server(report, sid, interactive=False)
    with open_connection(transport, report, server, [request["helper_python"]]) as (tunnel, _):
        base = f"http://127.0.0.1:{tunnel.local_port}{server['base_url']}"
        observed = kernel_observation(
            base,
            create=request["create"],
            duration=request["duration"],
            password=request["password"],
        )
        observed["server_pid"] = server["pid"]
        return observed


def independent_observation(
    host, sid, password, helper_python, *, create=False, duration=0, ssh_config=None
):
    # A fresh process creates its own SSH forward, HTTP cookie jar and WebSocket.
    # Existing authorized OpenSSH credentials are reused; no key/config is copied
    # or installed. This is not evidence of a second physical client or Unix UID.
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(Path(__file__).resolve().parents[1] / "src"), str(Path(__file__).resolve().parents[1])]
    )
    result = subprocess.run(
        [sys.executable, "-m", "experiments.site_pilot", "--worker", host, sid],
        input=json.dumps(
            {
                "password": password,
                "helper_python": helper_python,
                "create": create,
                "duration": duration,
                "ssh_config": str(ssh_config) if ssh_config else None,
            }
        ).encode(),
        env=environment,
        capture_output=True,
        timeout=90,
    )
    if result.returncode:
        raise RuntimeError("Independent site client failed; raw output suppressed")
    return json.loads(result.stdout)


def run_pilot(
    host,
    server_python,
    manual_pythons,
    *,
    helper_python="python3",
    hold_seconds=2,
    evidence=None,
    ssh_config=None,
):
    import requests

    transport = SSHTransport(host, config=ssh_config, timeout=40)
    password = secrets.token_urlsafe(32)
    manual = []
    sid = new_id()
    managed_attempted = stopped = accepted = False
    launched = None
    observations = {}

    def save(state, failures=None):
        if evidence is not None:
            evidence.seek(0)
            json.dump(
                {
                    "host": host,
                    "managed_id": sid,
                    "manual": manual,
                    "state": state,
                    "hold_seconds": hold_seconds,
                    "cleanup_errors": failures or [],
                    "observations": observations,
                },
                evidence,
            )
            evidence.truncate()
            evidence.flush()
            os.fsync(evidence.fileno())

    save("preparing")
    try:
        for python in manual_pythons:
            root = "/tmp/jupyhop-site-" + uuid.uuid4().hex
            manual.append((root, python))  # Also recover a lost setup reply.
            save("preparing")
            created = remote_fixture(
                transport, python, MANUAL_SETUP, {"root": root, "password": password}
            )
            deadline = time.monotonic() + 50
            while True:
                report = discover(transport, [helper_python])
                candidate = next(
                    (
                        s
                        for s in report["servers"]
                        if s["pid"] == created["pid"] and s["state"] == "ready"
                    ),
                    None,
                )
                if candidate:
                    break
                assert time.monotonic() < deadline, (
                    "Manual server not discovered; evidence retained until cleanup"
                )
                time.sleep(0.2)
            assert candidate["origin"] == "unmanaged"
            with open_connection(transport, report, candidate, [helper_python]) as (tunnel, _):
                base = f"http://127.0.0.1:{tunnel.local_port}{candidate['base_url']}"
                with requests.Session() as client:
                    client.trust_env = False
                    assert client.get(base + "api/status", timeout=5).status_code == 403
                    client.get(base + "login", timeout=5).raise_for_status()
                    client.post(
                        base + "login",
                        data={"_xsrf": client.cookies.get("_xsrf"), "password": password},
                        timeout=5,
                    ).raise_for_status()
                    assert client.get(base + "api/status", timeout=5).status_code == 200
            print(
                "PASS: externally launched server discovered/opened with normal private login; version "
                + candidate["version"],
                flush=True,
            )
        assert manual, "Select at least one existing manual-server interpreter"
        managed_attempted = True
        save("managed_start_attempted")
        launched = start(
            transport,
            name="pilot-" + uuid.uuid4().hex[:12],
            workdir=manual[0][0] + "/project",
            server_python=server_python,
            helper_python=helper_python,
            password=password,
            session_id=sid,
        )
        require_ready(launched)
        first = independent_observation(
            host,
            sid,
            password,
            helper_python,
            create=True,
            duration=hold_seconds,
            ssh_config=ssh_config,
        )
        observations["first"] = first
        print(
            "PASS: real-site managed kernel started; all first-worker connections closed",
            flush=True,
        )
        save("disconnected_workload")
        disconnected = time.monotonic()
        deadline = disconnected + hold_seconds
        while time.monotonic() < deadline:
            time.sleep(min(30, max(0, deadline - time.monotonic())))
            if time.monotonic() < deadline:
                print(
                    f"OBSERVED: real-site toy workload disconnected for {time.monotonic() - disconnected:.0f}s",
                    flush=True,
                )
        observations["disconnected_seconds"] = time.monotonic() - disconnected
        second = independent_observation(host, sid, password, helper_python, ssh_config=ssh_config)
        observations["second"] = second
        check_continuity(first, second)
        assert first["server_pid"] == second["server_pid"]
        print(
            "PASS: fresh process/login/forward retains real server PID, notebook/kernel/PID/memory and background progress",
            flush=True,
        )
        for _ in range(2):
            report = lifecycle(transport, "stop", sid, python=helper_python)
            require_lifecycle_ok(report)
            assert report["servers"][0]["state"] == "stopped"
        stopped = True
        archived = lifecycle(transport, "archive", sid, python=helper_python)
        require_lifecycle_ok(archived)
        assert archived["archived"]["id"] == sid
        print(
            "PASS: only the pilot managed UUID stopped/archived; inactive recovery evidence preserved",
            flush=True,
        )
        accepted = True
        save("acceptance_passed")
    finally:
        failures = []
        preflight_refused = (
            launched is not None
            and launched.get("record_path") is None
            and launched.get("error")
            in {
                "missing_tmux",
                "missing_python",
                "invalid_workdir",
                "server_prerequisites",
                "unsupported_server_version",
            }
        )
        if managed_attempted and not stopped and not preflight_refused:
            try:
                report = lifecycle(transport, "stop", sid, python=helper_python)
                require_lifecycle_ok(report)
                stopped = report["servers"][0]["state"] == "stopped"
                if stopped:
                    require_lifecycle_ok(lifecycle(transport, "archive", sid, python=helper_python))
            except Exception:
                failures.append(
                    "Managed fixture stop unconfirmed; workdir and recovery evidence retained"
                )
        for root, python in reversed(manual):
            try:
                remote_fixture(
                    transport,
                    python,
                    MANUAL_CLEANUP,
                    {"root": root, "remove": not managed_attempted or stopped or preflight_refused},
                )
            except Exception:
                failures.append("Manual fixture cleanup unconfirmed; private evidence retained")
        if failures:
            save("cleanup_unconfirmed", failures)
            raise RuntimeError("; ".join(failures))
        save("cleaned_after_pass" if accepted else "cleaned_after_failure")
        print("PASS: owned manual fixtures and temporary projects cleaned up", flush=True)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        print(json.dumps(worker(sys.argv[2], sys.argv[3], json.load(sys.stdin))))
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host")
    parser.add_argument("--server-python", required=True)
    parser.add_argument("--manual-python", action="append", required=True)
    parser.add_argument("--helper-python", default="python3")
    parser.add_argument("--ssh-config", type=Path)
    parser.add_argument("--hold-seconds", type=float, default=2)
    parser.add_argument("--evidence-file", type=Path, required=True)
    args = parser.parse_args()
    if not math.isfinite(args.hold_seconds) or not 0 <= args.hold_seconds <= 14400:
        parser.error("Hold duration must be between 0 and 14400 seconds")

    def interrupted(number, frame):
        raise KeyboardInterrupt

    for number in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, interrupted)
    descriptor = os.open(
        args.evidence_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w") as evidence:
        run_pilot(
            args.host,
            args.server_python,
            args.manual_python,
            helper_python=args.helper_python,
            hold_seconds=args.hold_seconds,
            evidence=evidence,
            ssh_config=args.ssh_config,
        )


if __name__ == "__main__":
    main()
