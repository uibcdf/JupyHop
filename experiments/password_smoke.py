"""Native Unix-password acceptance on the explicitly provisioned M5 accounts.

Requires provision --password-auth. Only the test actor reads the generated
fixture password; the JupyHop process delegates all password input to OpenSSH.
Never use this actor or its fixture password against a real scientific account.
"""

import argparse
import json
import os
import pty
import re
import secrets
import select
import signal
import subprocess
import sys
import termios
import time
from pathlib import Path

from experiments.m5_account_acceptance import login
from experiments.m5_accounts import _prepared, _read
from jupyhop.lifecycle import lifecycle, require_lifecycle_ok
from jupyhop.managed import new_id, require_ready, start
from jupyhop.ssh import SSHTransport


def children(pid):
    try:
        return [
            int(value) for value in Path(f"/proc/{pid}/task/{pid}/children").read_text().split()
        ]
    except FileNotFoundError:
        return []


def terminal_case(argv, password, *, jupyter_password=None, action="open"):
    pid, terminal = pty.fork()
    if pid == 0:
        environment = dict(
            os.environ, LC_ALL="C", PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src")
        )
        os.execve(sys.executable, [sys.executable, "-m", "jupyhop", *argv], environment)
    transcript = bytearray()
    prompts = 0
    connected = reaped = False
    owned = []
    wrong = b"incorrect-fixture-password"
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if not select.select([terminal], [], [], 0.1)[0]:
                continue
            try:
                chunk = os.read(terminal, 4096)
            except OSError:
                break
            if not chunk:
                break
            transcript.extend(chunk)
            assert len(transcript) < 32768
            count = transcript.count(b"password:")
            if count > prompts:
                direct = children(pid)
                owned.extend(direct)
                for child in direct:
                    owned.extend(children(child))
                assert not termios.tcgetattr(terminal)[3] & termios.ECHO
                prompts = count
                if action == "cancel":
                    os.write(terminal, b"\x03")
                elif action != "timeout":
                    os.write(
                        terminal, (wrong if action == "retry" and count == 1 else password) + b"\n"
                    )
            if not connected and jupyter_password is not None:
                for line in transcript.decode(errors="replace").splitlines():
                    if not line.startswith('{"host":'):
                        continue
                    try:
                        connection = json.loads(line)
                    except json.JSONDecodeError:
                        continue  # A PTY may split a JSON line across reads.
                    base = connection["url"].split("login?", 1)[0]
                    with login(base, jupyter_password) as client:
                        assert client.get(base + "api/status", timeout=5).status_code == 200
                    connected = True
                    os.write(terminal, b"\x03")
                    break
        else:
            raise RuntimeError("Native password terminal case timed out; raw output suppressed")
        _, status = os.waitpid(pid, 0)
        reaped = True
        assert os.waitstatus_to_exitcode(status) == (3 if action == "timeout" else 130)
        assert prompts == (2 if action == "retry" else 1)
        assert connected == (jupyter_password is not None)
        assert password not in transcript and wrong not in transcript
        if jupyter_password:
            assert jupyter_password.encode() not in transcript
        assert termios.tcgetattr(terminal)[3] & termios.ECHO
        for child in set(owned):
            path = Path(f"/proc/{child}/stat")
            assert not path.exists() or path.read_text().rsplit(")", 1)[1].split()[0] == "Z"
    finally:
        if not reaped:
            os.killpg(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        os.close(terminal)


def run(root, server_python):
    root, _, owner, _ = _prepared(root)
    assert owner == os.getuid() and os.getuid() != 0
    ready = json.loads(_read(root / "ready.json", owner))
    assert ready.get("password_auth") is True
    password = _read(root / "ssh-password", owner, limit=64)
    assert re.fullmatch(rb"[A-Za-z0-9_-]{43}", password)
    config = root / "password.conf"
    prefix = f"""Host password-target
    HostName 127.0.0.1
    Port {ready["port"]}
    User {ready["users"][0]["name"]}
    PubkeyAuthentication no
    BatchMode no
Host *
    Include {root / "ssh_config"}
"""
    config.write_text(prefix)
    config.chmod(0o600)
    transport = SSHTransport("account-a", config=root / "ssh_config", timeout=45)
    sid = new_id()
    jupyter_password = secrets.token_urlsafe(32)
    try:
        launched = start(
            transport,
            server_python=server_python,
            helper_python="/usr/bin/python3",
            workdir="~/project",
            name="password-acceptance",
            password=jupyter_password,
            session_id=sid,
        )
        require_ready(launched)
        common = ["--ssh-config", str(config), "--json", "--timeout", "15"]
        for jump in (False, True):
            config.write_text(
                ("Host password-target\n    ProxyJump account-b\n" if jump else "") + prefix
            )
            terminal_case(
                ["open", "password-target", sid, "--no-browser", *common],
                password,
                jupyter_password=jupyter_password,
            )
            status = lifecycle(transport, "status", sid, python="/usr/bin/python3")
            require_lifecycle_ok(status)
            assert status["servers"][0]["state"] == "ready"
            assert status["servers"][0]["pid"] == launched["server"]["pid"]
        print(
            "PASS: native Unix SSH password opens the same live Jupyter directly and through ProxyJump, once per invocation, without password echo/caching",
            flush=True,
        )
        config.write_text(prefix)
        terminal_case(
            ["open", "password-target", sid, "--no-browser", *common],
            password,
            jupyter_password=jupyter_password,
            action="retry",
        )
        terminal_case(["doctor", "password-target", *common], password, action="cancel")
        terminal_case(
            ["doctor", "password-target", "--ssh-auth-timeout", "1", *common],
            password,
            action="timeout",
        )
        headless = subprocess.run(
            [sys.executable, "-m", "jupyhop", "doctor", "password-target", "--batch", *common],
            capture_output=True,
            timeout=20,
        )
        assert headless.returncode == 3 and not headless.stdout
        assert password not in headless.stderr and b"password:" not in headless.stderr
        print(
            "PASS: native password retry, cancellation, authentication timeout, terminal restoration and noninteractive refusal",
            flush=True,
        )
    finally:
        stopped = lifecycle(transport, "stop", sid, python="/usr/bin/python3")
        require_lifecycle_ok(stopped)
        assert stopped["servers"][0]["state"] == "stopped"
        require_lifecycle_ok(lifecycle(transport, "archive", sid, python="/usr/bin/python3"))
    print(
        "PASS: password experiment managed UUID stopped/archived; privileged account cleanup remains mandatory",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--server-python", required=True)
    args = parser.parse_args()
    run(args.root, args.server_python)


if __name__ == "__main__":
    main()
