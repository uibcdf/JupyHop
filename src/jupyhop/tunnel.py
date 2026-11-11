"""An owned loopback forward on a verified invocation-private SSH connection."""

import socket
import time
from typing import Self

from jupyhop.connection import SSHConnection
from jupyhop.errors import SSHError, TunnelError
from jupyhop.ssh import CommandResult, SSHTransport


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
        self.connection: SSHConnection | None = None
        self.owns_connection = transport.connections is None
        self.forwarded = False

    def _forward(self) -> list[str]:
        return ["-L", f"127.0.0.1:{self.local_port}:127.0.0.1:{self.remote_port}"]

    def __enter__(self) -> Self:
        try:
            if self.transport.connections is not None:
                self.connection = self.transport.connections.get(self.transport)
            else:
                self.connection = SSHConnection(
                    self.transport, interactive=False, auth_timeout=self.transport.timeout
                )
                self.connection.__enter__()
            for _ in range(5):
                self.local_port = _free_port()
                result = self.connection.command("forward", self._forward())
                if result.returncode == 0:
                    self.forwarded = True
                    self.connection.check_owner()
                    return self
                self.connection.alive()
            raise TunnelError(
                "Could not bind an owned loopback forward after five attempts. Check local port availability and SSH forwarding policy."
            )
        except SSHError as error:
            self.close()
            raise TunnelError(str(error)) from None
        except BaseException:
            self.close()
            raise

    def run(self, argv: list[str], *, stdin: bytes = b"") -> CommandResult:
        assert self.connection is not None
        try:
            return self.connection.run(argv, stdin=stdin)
        except SSHError as error:
            raise TunnelError(str(error)) from None

    def check_alive(self) -> None:
        assert self.connection is not None
        try:
            self.connection.alive()
        except SSHError as error:
            raise TunnelError(str(error)) from None

    def wait(self) -> None:
        while True:
            self.check_alive()
            time.sleep(0.2)

    def close(self) -> None:
        if self.connection is not None:
            try:
                if self.forwarded and not self.owns_connection:
                    self.connection.check_owner()
                    self.connection.command("cancel", self._forward())
            except (SSHError, OSError):
                pass
            finally:
                if self.owns_connection:
                    self.connection.close()
                self.connection = None
                self.forwarded = False

    def __exit__(self, *args: object) -> None:
        self.close()
