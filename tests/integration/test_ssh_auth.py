"""Native controlling-terminal authentication, including cancellation/cleanup."""

import getpass
import json
import os
import pty
import select
import signal
import subprocess
import sys
import termios
import time
from pathlib import Path

import pytest

from jupyhop.connection import ConnectionPool, SSHConnection
from jupyhop.discovery import discover
from jupyhop.errors import SSHError
from jupyhop.ssh import SSHTransport
from jupyhop.tunnel import Tunnel

pytestmark = pytest.mark.integration
PASSPHRASE = b"fixture-passphrase"


@pytest.fixture(scope="module")
def protected_identity(ssh_lab):
    key = ssh_lab.root / "protected-key"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-f", str(key)],
        input=PASSPHRASE + b"\n" + PASSPHRASE + b"\n",
        capture_output=True,
        start_new_session=True,
        timeout=10,
        check=True,
    )
    with ssh_lab.authorized.open("ab") as stream:
        stream.write(key.with_suffix(".pub").read_bytes())
    config = ssh_lab.root / "protected-key.conf"
    config.write_text(f"""Host remote gateway
    HostName 127.0.0.1
Host remote
    Port {ssh_lab.ports[1]}
Host gateway
    Port {ssh_lab.ports[0]}
Host *
    User {getpass.getuser()}
    IdentityFile {key}
    IdentityAgent none
    IdentitiesOnly yes
    BatchMode no
    StrictHostKeyChecking yes
    UserKnownHostsFile {ssh_lab.root / "known_hosts"}
    GlobalKnownHostsFile /dev/null
""")
    return config


def descendants(pid):
    result = []
    try:
        children = Path(f"/proc/{pid}/task/{pid}/children").read_text().split()
    except FileNotFoundError:
        return result
    for value in children:
        child = int(value)
        result.append(child)
        result.extend(descendants(child))
    return result


@pytest.mark.parametrize("mode", ["direct", "jump", "interrupt", "terminate", "timeout"])
def test_native_tty_passphrase_rpc_and_owned_proxy_cleanup(ssh_lab, protected_identity, mode):
    config = protected_identity
    if mode == "jump":
        config = ssh_lab.root / "protected-jump.conf"
        config.write_text("Host remote\n    ProxyJump gateway\n" + protected_identity.read_text())
    pid, terminal = pty.fork()
    if pid == 0:

        def interrupted(number, frame):
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, interrupted)
        os.environ["LC_ALL"] = "C"
        exit_code = 0
        try:
            with SSHConnection(
                SSHTransport("remote", config=config, timeout=5),
                interactive=True,
                auth_timeout=1 if mode == "timeout" else 10,
            ) as connection:
                assert connection.run(["id", "-u"]).stdout.strip() == str(os.getuid()).encode()
                assert (
                    connection.run(
                        [
                            sys.executable,
                            "-c",
                            "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())",
                        ],
                        stdin=b"PRIVATE_JUPYTER_SENTINEL",
                    ).stdout
                    == b"PRIVATE_JUPYTER_SENTINEL"
                )
                os.write(1, b"RPC_OK\n")
        except KeyboardInterrupt:
            exit_code = 130
        except BaseException:
            exit_code = 3
        os._exit(exit_code)
    transcript = bytearray()
    prompts = 0
    owned = []
    reaped = False
    try:
        deadline = time.monotonic() + 20
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
            count = transcript.count(b"Enter passphrase")
            if count > prompts:
                owned.extend(descendants(pid))
                assert not termios.tcgetattr(terminal)[3] & termios.ECHO
                prompts = count
                if mode == "interrupt":
                    os.write(terminal, b"\x03")
                elif mode == "terminate":
                    os.kill(pid, signal.SIGTERM)
                elif mode != "timeout":
                    os.write(terminal, PASSPHRASE + b"\n")
        else:
            pytest.fail("Native terminal authentication/cleanup did not finish")
        _, status = os.waitpid(pid, 0)
        reaped = True
        expected = 0 if mode in {"direct", "jump"} else 3 if mode == "timeout" else 130
        assert os.waitstatus_to_exitcode(status) == expected
        assert prompts == (2 if mode == "jump" else 1)
        assert PASSPHRASE not in transcript and b"PRIVATE_JUPYTER_SENTINEL" not in transcript
        assert bool(termios.tcgetattr(terminal)[3] & termios.ECHO)
        assert (b"RPC_OK" in transcript) == (expected == 0)
        assert owned
        for child in set(owned):
            path = Path(f"/proc/{child}/stat")
            assert not path.exists() or path.read_text().rsplit(")", 1)[1].split()[0] == "Z"
    finally:
        if not reaped:
            os.killpg(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        os.close(terminal)


@pytest.mark.parametrize("jump", [False, True])
def test_cli_open_authenticates_once_per_hop_and_reuses_only_its_private_master(
    ssh_lab, protected_identity, jump
):
    from experiments.jupyter_fixture import JupyterFixture

    config = protected_identity
    if jump:
        config = ssh_lab.root / "cli-protected-jump.conf"
        config.write_text("Host remote\n    ProxyJump gateway\n" + protected_identity.read_text())
    with JupyterFixture(ssh_lab.root / f"tty-open-{jump}", runtime=ssh_lab.runtime) as fixture:
        report = discover(SSHTransport("direct", config=ssh_lab.config))
        server = next(item for item in report["servers"] if item["pid"] == fixture.process.pid)
        pid, terminal = pty.fork()
        if pid == 0:
            environment = dict(
                os.environ, LC_ALL="C", PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src")
            )
            os.execve(
                sys.executable,
                [
                    sys.executable,
                    "-m",
                    "jupyhop",
                    "open",
                    "remote",
                    server["id"],
                    "--ssh-config",
                    str(config),
                    "--json",
                    "--no-browser",
                    "--timeout",
                    "5",
                ],
                environment,
            )
        transcript = bytearray()
        prompts = 0
        opened = False
        reaped = False
        owned = []
        try:
            deadline = time.monotonic() + 30
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
                count = transcript.count(b"Enter passphrase")
                if count > prompts:
                    owned.extend(descendants(pid))
                    assert not termios.tcgetattr(terminal)[3] & termios.ECHO
                    prompts = count
                    os.write(terminal, PASSPHRASE + b"\n")
                if not opened:
                    for line in transcript.decode(errors="replace").splitlines():
                        if not line.startswith('{"host":'):
                            continue
                        try:
                            connection = json.loads(line)
                        except json.JSONDecodeError:
                            continue  # A PTY may split a JSON line across reads.
                        base = connection["url"].split("login?", 1)[0]
                        with fixture.client(base) as client:
                            assert client.get(base + "api/status", timeout=5).status_code == 200
                        for child in descendants(pid):
                            try:
                                arguments = Path(f"/proc/{child}/cmdline").read_bytes()
                            except FileNotFoundError:
                                continue
                            assert PASSPHRASE not in arguments
                            assert fixture.info["token"].encode() not in arguments
                        opened = True
                        os.write(terminal, b"\x03")
                        break
            else:
                pytest.fail("Interactive CLI did not open/close its owned forward")
            _, status = os.waitpid(pid, 0)
            reaped = True
            assert os.waitstatus_to_exitcode(status) == 130
            assert opened and prompts == (2 if jump else 1)
            assert PASSPHRASE not in transcript and fixture.info["token"].encode() not in transcript
            assert fixture.process.poll() is None
            assert termios.tcgetattr(terminal)[3] & termios.ECHO
            for child in set(owned):
                path = Path(f"/proc/{child}/stat")
                assert not path.exists() or path.read_text().rsplit(")", 1)[1].split()[0] == "Z"
        finally:
            if not reaped:
                os.killpg(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            os.close(terminal)


def test_missing_private_control_socket_never_falls_back_to_network_authentication(ssh_lab):
    with SSHConnection(
        SSHTransport("direct", config=ssh_lab.config), interactive=False, auth_timeout=5
    ) as connection:
        connection.control.unlink()
        with pytest.raises(SSHError, match="verify"):
            connection.run(["id", "-u"])


def test_headless_encrypted_key_authentication_fails_without_prompting(protected_identity):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "jupyhop",
            "doctor",
            "remote",
            "--ssh-config",
            str(protected_identity),
            "--batch",
            "--json",
            "--timeout",
            "5",
        ],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 3
    assert b"Enter passphrase" not in result.stderr and not result.stdout
    assert b"--batch" in result.stderr


def test_borrowed_tunnels_cancel_only_their_own_forward(ssh_lab):
    import requests

    from experiments.jupyter_fixture import JupyterFixture

    pool = ConnectionPool(batch=True)
    transport = SSHTransport("destination", config=ssh_lab.config, connections=pool)
    try:
        with JupyterFixture(ssh_lab.root / "borrowed-forwards") as fixture:
            with Tunnel(transport, fixture.port) as first:
                with Tunnel(transport, fixture.port) as second:
                    assert first.connection is second.connection
                    assert first.local_port != second.local_port
                    assert (
                        requests.get(
                            f"http://127.0.0.1:{second.local_port}/science/api", timeout=3
                        ).status_code
                        == 200
                    )
                assert (
                    requests.get(
                        f"http://127.0.0.1:{first.local_port}/science/api", timeout=3
                    ).status_code
                    == 200
                )
            assert transport.run(["id", "-u"]).stdout.strip() == str(os.getuid()).encode()
            assert fixture.process.poll() is None
    finally:
        pool.close()
