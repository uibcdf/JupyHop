"""Invocation-owned OpenSSH masters; authentication belongs to OpenSSH's TTY.

Private multiplex clients cannot fall back to another network connection. No
SSH password enters Python, subprocess arguments, RPC stdin or a credential file.
"""

import math
import os
import re
import signal
import subprocess
import tempfile
import time
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from typing import Self

from jupyhop.errors import SSHError
from jupyhop.ssh import (
    STDERR_LIMIT,
    STDIN_LIMIT,
    CommandResult,
    SSHTransport,
    _run_bounded,
    remote_command,
    ssh_failure,
)


def terminal_available() -> bool:
    try:
        descriptor = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
    except OSError:
        return False
    try:
        return os.isatty(descriptor)
    finally:
        os.close(descriptor)


class SSHConnection:
    def __init__(self, transport: SSHTransport, *, interactive: bool, auth_timeout: float):
        self.transport = transport
        self.interactive = interactive
        self.auth_timeout = auth_timeout
        self.process: subprocess.Popen[bytes] | None = None
        self.directory: tempfile.TemporaryDirectory[str] | None = None
        self.stderr = bytearray()

    def __enter__(self) -> Self:
        try:
            self.directory = tempfile.TemporaryDirectory(prefix="jupyhop-", dir="/tmp")
            self.control = Path(self.directory.name) / "control"
            command = [
                *self.transport.options(control_path=self.control, interactive=self.interactive),
                "-o",
                "LogLevel=ERROR",
                "-N",
                self.transport.host,
            ]
            # The interactive child retains the caller's controlling terminal.
            # Its stdin is never the Jupyter password/RPC pipe. OpenSSH reads
            # passwords/passphrases privately from /dev/tty and owns echo modes.
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=None if self.interactive else subprocess.PIPE,
                start_new_session=not self.interactive,
            )
            if self.process.stderr is not None:
                os.set_blocking(self.process.stderr.fileno(), False)
            deadline = time.monotonic() + (
                self.auth_timeout if self.interactive else self.transport.timeout
            )
            while not self.control.is_socket():
                self.alive()
                if time.monotonic() >= deadline:
                    raise SSHError(
                        "SSH authentication/startup timed out; remote session state is unknown."
                    )
                time.sleep(0.05)
            self.check_owner()
            return self
        except OSError:
            self.close()
            raise SSHError(
                "Could not create an owned SSH connection. Check OpenSSH and local permissions."
            ) from None
        except BaseException:
            self.close()
            raise

    def client(self) -> list[str]:
        return [
            "ssh",
            "-F",
            "/dev/null",
            "-S",
            str(self.control),
            "-o",
            "ProxyCommand=false",
            "-o",
            "BatchMode=yes",
            "-o",
            "ControlMaster=no",
            "-o",
            "ControlPersist=no",
            "-o",
            "ForkAfterAuthentication=no",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "PermitLocalCommand=no",
            "-o",
            "ForwardAgent=no",
            "-o",
            "ForwardX11=no",
        ]

    def command(self, operation: str, arguments: list[str]) -> CommandResult:
        return _run_bounded(
            [
                *self.client(),
                "-o",
                "ClearAllForwardings=no",
                "-O",
                operation,
                *arguments,
                self.transport.host,
            ],
            b"",
            min(self.transport.timeout, 3),
        )

    def alive(self) -> None:
        if self.process is None:
            raise SSHError(
                "Owned SSH connection is closed; remote session state is unknown. Run the command again to authenticate."
            )
        if self.process.stderr is not None:
            while True:
                try:
                    chunk = os.read(self.process.stderr.fileno(), 4096)
                except BlockingIOError:
                    break
                if not chunk:
                    break
                self.stderr.extend(chunk)
                if len(self.stderr) > STDERR_LIMIT:
                    raise SSHError(
                        "SSH diagnostics exceeded their size limit; raw output suppressed."
                    )
        if self.process.poll() is not None:
            raise ssh_failure(bytes(self.stderr))

    def check_owner(self) -> None:
        self.alive()
        assert self.process is not None
        result = self.command("check", [])
        match = re.search(rb"Master running \(pid=(\d+)\)", result.stderr)
        if result.returncode != 0 or match is None or int(match[1]) != self.process.pid:
            raise SSHError(
                "Could not verify the owned SSH connection; no shared connection was adopted."
            )

    def run(self, argv: list[str], *, stdin: bytes = b"") -> CommandResult:
        if len(stdin) > STDIN_LIMIT:
            raise ValueError("Remote probe input exceeds 64 KiB.")
        command = remote_command(argv)
        self.check_owner()
        return _run_bounded(
            [*self.client(), "-T", "-o", "ClearAllForwardings=yes", self.transport.host, command],
            stdin,
            self.transport.timeout,
        )

    def close(self) -> None:
        if self.process is not None:
            if self.process.poll() is None:
                try:
                    if self.interactive:
                        self.process.terminate()
                    else:
                        os.killpg(self.process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    if self.interactive:
                        self.process.kill()
                    else:
                        os.killpg(self.process.pid, signal.SIGKILL)
                    self.process.wait()
            if self.process.stderr is not None:
                self.process.stderr.close()
            self.process = None
        if self.directory is not None:
            self.directory.cleanup()
            self.directory = None

    def __exit__(self, *args: object) -> None:
        self.close()


class ConnectionPool:
    """Lazy, bounded masters scoped to one CLI invocation, never persisted."""

    def __init__(self, *, batch: bool = False, auth_timeout: float = 120):
        if not math.isfinite(auth_timeout) or not 1 <= auth_timeout <= 600:
            raise ValueError("SSH authentication timeout must be between 1 and 600 seconds.")
        self.interactive = not batch and terminal_available()
        self.auth_timeout = auth_timeout
        self.connections: dict[SSHTransport, SSHConnection] = {}

    def get(self, transport: SSHTransport) -> SSHConnection:
        raw = replace(transport, connections=None)
        if raw not in self.connections:
            if len(self.connections) >= 16:
                raise ValueError("At most 16 SSH routes may be opened in one invocation.")
            connection = SSHConnection(
                raw, interactive=self.interactive, auth_timeout=self.auth_timeout
            )
            self.connections[raw] = connection.__enter__()
        return self.connections[raw]

    def close(self) -> None:
        connections = list(self.connections.values())
        self.connections.clear()
        with ExitStack() as cleanup:
            for connection in connections:
                cleanup.callback(connection.close)
