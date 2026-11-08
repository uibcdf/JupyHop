"""One foreground-owned OpenSSH connection; no persisted or shared forward.

A private control socket allows adding only our explicit forward after SSH has
ignored configured forwards. Every multiplex client disables fallback to a new
network connection. OpenSSH owns binding and reports collisions atomically.
"""

import os
import re
import signal
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Self

from jupyhop.errors import TunnelError
from jupyhop.ssh import (
    STDERR_LIMIT,
    STDIN_LIMIT,
    CommandResult,
    SSHTransport,
    _run_bounded,
    remote_command,
)


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


class Tunnel:
    def __init__(self, transport: SSHTransport, remote_port: int):
        if type(remote_port) is not int or not 1 <= remote_port <= 65535:
            raise ValueError("Remote port must be between 1 and 65535.")
        self.transport = transport
        self.remote_port = remote_port
        self.local_port = 0
        self.process: subprocess.Popen[bytes] | None = None
        self.directory: tempfile.TemporaryDirectory[str] | None = None
        self.stderr = bytearray()

    def __enter__(self) -> Self:
        try:
            self.directory = tempfile.TemporaryDirectory(prefix="jupyhop-", dir="/tmp")
            self.control = Path(self.directory.name) / "control"
            command = [
                *self.transport.options(control_path=self.control),
                "-o",
                "LogLevel=ERROR",
                "-o",
                "ExitOnForwardFailure=yes",
                "-N",
                self.transport.host,
            ]
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            assert self.process.stderr is not None
            os.set_blocking(self.process.stderr.fileno(), False)
            deadline = time.monotonic() + self.transport.timeout
            while not self.control.is_socket():
                self._alive()
                if time.monotonic() >= deadline:
                    raise TunnelError(
                        "SSH tunnel startup timed out; remote session state is unknown."
                    )
                time.sleep(0.05)
            self._check_owner()
            for _ in range(5):
                self.local_port = _free_port()
                result = self._control(
                    "forward", ["-L", f"127.0.0.1:{self.local_port}:127.0.0.1:{self.remote_port}"]
                )
                if result.returncode == 0:
                    self._check_owner()
                    return self
                self._alive()
            raise TunnelError(
                "Could not bind an owned loopback forward after five attempts. Check local port availability and SSH forwarding policy."
            )
        except OSError:
            self.close()
            raise TunnelError(
                "Could not create the private SSH tunnel. Check OpenSSH, local permissions and loopback availability."
            ) from None
        except BaseException:
            self.close()
            raise

    def _client(self) -> list[str]:
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
            "StrictHostKeyChecking=yes",
            "-o",
            "PermitLocalCommand=no",
            "-o",
            "ForwardAgent=no",
            "-o",
            "ForwardX11=no",
        ]

    def _control(self, operation: str, arguments: list[str]) -> CommandResult:
        return _run_bounded(
            [
                *self._client(),
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

    def _alive(self) -> None:
        assert self.process is not None and self.process.stderr is not None
        while True:
            try:
                chunk = os.read(self.process.stderr.fileno(), 4096)
            except BlockingIOError:
                break
            if not chunk:
                break
            self.stderr.extend(chunk)
            if len(self.stderr) > STDERR_LIMIT:
                raise TunnelError(
                    "SSH tunnel diagnostic output exceeded its limit; raw output was suppressed."
                )
        if self.process.poll() is not None:
            raise TunnelError(
                "SSH tunnel closed or forwarding was denied. Verify access and forwarding policy with ssh; remote session state is unknown."
            )

    def _check_owner(self) -> None:
        self._alive()
        assert self.process is not None
        result = self._control("check", [])
        match = re.search(rb"Master running \(pid=(\d+)\)", result.stderr)
        if result.returncode != 0 or match is None or int(match[1]) != self.process.pid:
            raise TunnelError(
                "Could not verify the owned SSH connection. No existing listener was adopted."
            )

    def run(self, argv: list[str], *, stdin: bytes = b"") -> CommandResult:
        if len(stdin) > STDIN_LIMIT:
            raise ValueError("Remote probe input exceeds 64 KiB.")
        self._check_owner()
        return _run_bounded(
            [
                *self._client(),
                "-T",
                "-o",
                "ClearAllForwardings=yes",
                self.transport.host,
                remote_command(argv),
            ],
            stdin,
            self.transport.timeout,
        )

    def wait(self) -> None:
        while True:
            self._alive()
            time.sleep(0.2)

    def close(self) -> None:
        if self.process is not None:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
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
