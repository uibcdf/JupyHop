"""Disposable loopback OpenSSH servers. Never reads the user's SSH configuration."""

import getpass
import os
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import ExitStack
from pathlib import Path


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def stop(process):
    """Signal only a process group created by this fixture."""
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


class SSHLab:
    def __init__(self, *, allow_target_forwarding=True):
        self.allow_target_forwarding = allow_target_forwarding

    def __enter__(self):
        self.stack = ExitStack()
        try:
            self.root = Path(
                self.stack.enter_context(tempfile.TemporaryDirectory(prefix="jupyhop-lab-"))
            )
            self.root.chmod(0o700)
            self.home = self.root / "home"
            self.home.mkdir(mode=0o700)
            self.runtime = self.home / "runtime"
            self.runtime.mkdir(mode=0o700)
            self.run = self.root / "run"
            self.run.mkdir(mode=0o700)
            wrapper = self.root / "session.sh"
            wrapper.write_text(
                "#!/bin/sh\n"
                + "\n".join(
                    f"export {key}={shlex.quote(str(value))}"
                    for key, value in {
                        "HOME": self.home,
                        "JUPYTER_RUNTIME_DIR": self.runtime,
                        "JUPYTER_CONFIG_DIR": self.home / "config",
                        "JUPYTER_DATA_DIR": self.home / "data",
                        "XDG_STATE_HOME": self.home / "state",
                        "XDG_RUNTIME_DIR": self.run,
                        "PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin",
                    }.items()
                )
                + '\nexec /bin/sh -c "$SSH_ORIGINAL_COMMAND"\n'
            )
            wrapper.chmod(0o700)
            self.key = self.root / "identity"
            self.hostkey = self.root / "hostkey"
            for key in (self.key, self.hostkey):
                subprocess.run(
                    [
                        "ssh-keygen",
                        "-q",
                        "-t",
                        "ed25519",
                        "-N",
                        "",
                        "-C",
                        "fixture",
                        "-f",
                        str(key),
                    ],
                    check=True,
                )
            self.authorized = self.root / "authorized_keys"
            self.authorized.write_bytes(self.key.with_suffix(".pub").read_bytes())
            self.authorized.chmod(0o600)
            self.ports = [free_port(), free_port()]
            # Offline pinning from keys we generated, never ssh-keyscan/TOFU.
            known = self.root / "known_hosts"
            public = self.hostkey.with_suffix(".pub").read_text().strip()
            known.write_text("".join(f"[127.0.0.1]:{port} {public}\n" for port in self.ports))
            for index, port in enumerate(self.ports):
                cfg = self.root / f"sshd-{index}.conf"
                cfg.write_text(f"""Port {port}
ListenAddress 127.0.0.1
HostKey {self.hostkey}
PidFile {self.root}/sshd-{index}.pid
AuthorizedKeysFile {self.authorized}
# The sandbox may map /tmp to a non-root owner. Keys themselves are 0600 in
# a private 0700 directory. This setting affects only this disposable sshd.
StrictModes no
PasswordAuthentication no
KbdInteractiveAuthentication no
UsePAM no
PermitRootLogin no
AllowUsers {getpass.getuser()}
ForceCommand {wrapper}
AllowTcpForwarding {"local" if index == 0 or self.allow_target_forwarding else "no"}
X11Forwarding no
PrintMotd no
LogLevel ERROR
""")
                log = self.stack.enter_context(open(self.root / f"sshd-{index}.log", "w+"))
                process = subprocess.Popen(
                    [
                        shutil.which("sshd") or "/usr/sbin/sshd",
                        "-D",
                        "-e",
                        "-f",
                        str(cfg),
                    ],
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
                )
                self.stack.callback(stop, process)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError(
                            "Disposable sshd failed; check local sshd prerequisites (/run/sshd, non-root account)"
                        )
                    try:
                        with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                            break
                    except OSError:
                        time.sleep(0.05)
                else:
                    raise RuntimeError("Disposable sshd did not become ready")
            self.config = self.root / "ssh_config"
            # Include/Match are intentionally resolved by the real OpenSSH parser.
            included = self.root / "hosts.conf"
            included.write_text(f"""Host direct destination
    HostName 127.0.0.1
    Port {self.ports[1]}
Host destination
    ProxyJump gateway
Host gateway
    HostName 127.0.0.1
    Port {self.ports[0]}
""")
            self.config.write_text(f"""Include {included}
Host *
    User {getpass.getuser()}
    IdentityFile {self.key}
    IdentitiesOnly yes
    UserKnownHostsFile {known}
    GlobalKnownHostsFile /dev/null
    StrictHostKeyChecking yes
    BatchMode yes
    ConnectTimeout 5
Match host 127.0.0.1
    ServerAliveInterval 5
""")
            # A group-writable operator umask must not weaken fixture SSH config.
            # Newer OpenSSH also checks included files supplied through -F.
            for config in (self.config, included):
                config.chmod(0o600)
            return self
        except BaseException:
            self.stack.close()
            raise

    def __exit__(self, *args):
        self.stack.close()

    def ssh(self, host, argv, **kwargs):
        return subprocess.run(
            ["ssh", "-F", str(self.config), "-T", host, shlex.join(argv)],
            check=False,
            capture_output=True,
            timeout=15,
            **kwargs,
        )

    def tunnel(self, host, remote_port, local_port=None):
        port = local_port or free_port()
        control = self.root / ("ctl-" + uuid.uuid4().hex[:8])
        process = subprocess.Popen(
            [
                "ssh",
                "-F",
                str(self.config),
                "-T",
                "-N",
                "-M",
                "-S",
                str(control),
                "-o",
                "ControlPersist=no",
                "-o",
                "ExitOnForwardFailure=yes",
                "-L",
                f"127.0.0.1:{port}:127.0.0.1:{remote_port}",
                host,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.stack.callback(stop, process)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Fixture forward failed (possibly a bind collision)")
            try:
                if not control.exists():
                    time.sleep(0.05)
                    continue
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    return process, port
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("Fixture forward timed out")
