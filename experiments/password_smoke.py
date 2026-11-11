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
from urllib.parse import unquote, urlsplit

from experiments.browser_handoff import chrome
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


def terminal_case(argv, password, *, jupyter_password=None, action="open", stdin=None):
    input_read, input_write = os.pipe() if stdin is not None else (-1, -1)
    pid, terminal = pty.fork()
    if pid == 0:
        if input_read != -1:
            os.dup2(input_read, 0)
            os.close(input_read)
            os.close(input_write)
        environment = dict(
            os.environ,
            LC_ALL="C",
            PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
            XDG_CONFIG_HOME=str(
                Path(argv[argv.index("--ssh-config") + 1]).parent / "isolated-client-config"
            ),
        )
        os.execve(sys.executable, [sys.executable, "-m", "jupyhop", *argv], environment)
    transcript = bytearray()
    prompts = 0
    connected = reaped = False
    owned = []
    wrong = b"incorrect-fixture-password"
    result = None
    try:
        if input_read != -1:
            os.close(input_read)
            input_read = -1
            try:
                os.write(input_write, stdin)
            finally:
                os.close(input_write)
                input_write = -1
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
            if action == "start":
                for line in transcript.decode(errors="replace").splitlines():
                    if line.startswith('{"id":'):
                        try:
                            result = json.loads(line)
                        except json.JSONDecodeError:
                            pass
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
            if not connected and action == "browser":
                match = re.search(rb"file://[^\r\n ]+\.html", transcript)
                if match:
                    launch = Path(unquote(urlsplit(match[0].decode()).path))
                    assert (
                        launch.stat().st_uid == os.getuid()
                        and launch.stat().st_mode & 0o777 == 0o600
                    )
                    config = Path(argv[argv.index("--ssh-config") + 1])
                    with chrome(config.parent, launch) as browser:
                        browser.until("!!document.querySelector('.jp-LabShell')")
                        assert not launch.exists() and "token=" not in browser.evaluate(
                            "location.href"
                        )
                    connected = True
                    os.write(terminal, b"\x03")
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
        assert os.waitstatus_to_exitcode(status) == (
            0 if action == "start" else 3 if action == "timeout" else 130
        )
        assert prompts == (2 if action == "retry" else 1)
        assert connected == (jupyter_password is not None or action == "browser")
        assert password not in transcript and wrong not in transcript
        if stdin:
            assert stdin.rstrip(b"\n") not in transcript
        if jupyter_password:
            assert jupyter_password.encode() not in transcript
        assert termios.tcgetattr(terminal)[3] & termios.ECHO
        for child in set(owned):
            path = Path(f"/proc/{child}/stat")
            assert not path.exists() or path.read_text().rsplit(")", 1)[1].split()[0] == "Z"
        if action == "start":
            assert result is not None
        return result
    finally:
        if not reaped:
            os.killpg(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        os.close(terminal)
        for descriptor in (input_read, input_write):
            if descriptor != -1:
                os.close(descriptor)


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
    active = [sid]
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
        token_id = new_id()
        active.append(token_id)
        require_ready(
            start(
                transport,
                server_python=server_python,
                helper_python="/usr/bin/python3",
                workdir="~/project",
                name="token-password-acceptance",
                auth_mode="token",
                session_id=token_id,
            )
        )
        for jump in (False, True):
            config.write_text(
                ("Host password-target\n    ProxyJump account-b\n" if jump else "") + prefix
            )
            terminal_case(
                [
                    "resume",
                    "password-target",
                    "--name",
                    "token-password-acceptance",
                    "--no-browser",
                    "--ssh-config",
                    str(config),
                    "--timeout",
                    "15",
                ],
                password,
                action="browser",
            )
        print(
            "PASS: native SSH password and automatic Jupyter browser access compose on direct and jump routes",
            flush=True,
        )
        config.write_text(prefix)
        cli_password = secrets.token_urlsafe(32)
        created = terminal_case(
            [
                "start",
                "password-target",
                "--server-python",
                server_python,
                "--remote-python",
                "/usr/bin/python3",
                "--workdir",
                "~/project",
                "--name",
                "password-cli-start",
                "--password-stdin",
                "--no-open",
                *common,
            ],
            password,
            action="start",
            stdin=(cli_password + "\n").encode(),
        )
        require_ready(created)
        active.append(created["id"])
        print(
            "PASS: managed CLI start keeps piped Jupyter password separate from native terminal SSH password",
            flush=True,
        )
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
            env=dict(os.environ, XDG_CONFIG_HOME=str(root / "isolated-client-config")),
        )
        assert headless.returncode == 3 and not headless.stdout
        assert password not in headless.stderr and b"password:" not in headless.stderr
        print(
            "PASS: native password retry, cancellation, authentication timeout, terminal restoration and noninteractive refusal",
            flush=True,
        )
    finally:
        for identifier in reversed(active):
            stopped = lifecycle(transport, "stop", identifier, python="/usr/bin/python3")
            require_lifecycle_ok(stopped)
            assert stopped["servers"][0]["state"] == "stopped"
            require_lifecycle_ok(
                lifecycle(transport, "archive", identifier, python="/usr/bin/python3")
            )
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
