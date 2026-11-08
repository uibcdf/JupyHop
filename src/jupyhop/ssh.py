"""Bounded OpenSSH subprocess transport for Linux, with no config parser."""

import math
import os
import re
import selectors
import shlex
import signal
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from jupyhop.errors import ProtocolError, SSHError

STDOUT_LIMIT = 64 * 1024
STDERR_LIMIT = 32 * 1024
STDIN_LIMIT = 64 * 1024
_ALIAS = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,252}\Z")


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: bytes
    stderr: bytes


def validate_alias(host: str) -> str:
    if not _ALIAS.fullmatch(host):
        raise ValueError(
            "Use an SSH host alias (letters, digits, dot, underscore, hyphen); set User in SSH config."
        )
    return host


def remote_command(argv: Sequence[str]) -> str:
    if not argv or not argv[0] or any("\0" in arg for arg in argv):
        raise ValueError("Remote command must contain nonempty executable and no NUL characters.")
    # OpenSSH sends one command string to the remote login shell. A local argv
    # prevents local injection; POSIX quoting separately prevents remote injection.
    return shlex.join(argv)


@dataclass(frozen=True)
class SSHTransport:
    host: str
    config: Path | None = None
    timeout: float = 20

    def __post_init__(self) -> None:
        validate_alias(self.host)
        if not math.isfinite(self.timeout) or not 1 <= self.timeout <= 300:
            raise ValueError("Timeout must be between 1 and 300 seconds.")

    def options(self, *, control_path: Path | None = None) -> list[str]:
        options = [
            "ssh",
            "-T",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "ClearAllForwardings=yes",
            "-o",
            "ForwardAgent=no",
            "-o",
            "ForwardX11=no",
            "-o",
            "PermitLocalCommand=no",
            "-o",
            "RemoteCommand=none",
            "-o",
            "ControlMaster=no" if control_path is None else "ControlMaster=yes",
            "-o",
            "ControlPath=none" if control_path is None else f"ControlPath={control_path}",
            "-o",
            "ControlPersist=no",
            "-o",
            f"ConnectTimeout={math.ceil(self.timeout)}",
            "-o",
            "ServerAliveInterval=5",
            "-o",
            "ServerAliveCountMax=2",
        ]
        if self.config is not None:
            options.extend(["-F", str(self.config.expanduser().resolve())])
        return options

    def command(self, argv: Sequence[str]) -> list[str]:
        return [*self.options(), self.host, remote_command(argv)]

    def run(self, argv: Sequence[str], *, stdin: bytes = b"") -> CommandResult:
        if len(stdin) > STDIN_LIMIT:
            raise ValueError("Remote probe input exceeds 64 KiB.")
        return _run_bounded(self.command(argv), stdin, self.timeout)


def _run_bounded(command: list[str], data: bytes, timeout: float) -> CommandResult:
    """Bound memory and wall time, including writes if remote stdin is not read."""
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except FileNotFoundError:
        raise SSHError("OpenSSH client not found. Install ssh and verify it is on PATH.") from None
    except OSError:
        raise SSHError("Could not start OpenSSH. Check executable and local permissions.") from None
    assert process.stdin is not None and process.stdout is not None and process.stderr is not None
    output = {"stdout": bytearray(), "stderr": bytearray()}
    offset = 0
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            for stream, name in ((process.stdout, "stdout"), (process.stderr, "stderr")):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            if data:
                os.set_blocking(process.stdin.fileno(), False)
                selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
            else:
                process.stdin.close()
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise SSHError(
                        "SSH probe timed out. Verify the alias, jump route, and access with ssh; remote session state is unknown."
                    )
                for key, _ in selector.select(min(remaining, 0.1)):
                    if key.data == "stdin":
                        try:
                            offset += os.write(key.fd, data[offset : offset + 4096])
                        except BrokenPipeError:
                            offset = len(data)
                        if offset == len(data):
                            selector.unregister(key.fileobj)
                            process.stdin.close()
                        continue
                    chunk = os.read(key.fd, 4096)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    output[key.data].extend(chunk)
                    limit = STDOUT_LIMIT if key.data == "stdout" else STDERR_LIMIT
                    if len(output[key.data]) > limit:
                        raise ProtocolError(
                            "SSH probe output exceeds its size limit. Check remote shell startup output."
                        )
            try:
                code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                raise SSHError(
                    "SSH probe timed out. Verify access with ssh; remote session state is unknown."
                ) from None
        return CommandResult(code, bytes(output["stdout"]), bytes(output["stderr"]))
    finally:
        # This group belongs exclusively to this invocation, including ProxyJump.
        # No shared ControlMaster is used; never terminate arbitrary SSH processes.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()


def ssh_failure(stderr: bytes) -> SSHError:
    """Classify known messages without reflecting any untrusted output."""
    lowered = stderr.lower()
    if (
        b"host key verification failed" in lowered
        or b"remote host identification has changed" in lowered
    ):
        return SSHError(
            "SSH host-key verification failed. Verify the host fingerprint through a trusted channel and use ssh to manage known_hosts; JupyHop never bypasses verification."
        )
    if b"permission denied" in lowered:
        return SSHError(
            "SSH authentication denied. Check the configured remote User, key and agent with ssh. Doctor uses BatchMode and cannot prompt for credentials."
        )
    return SSHError(
        "SSH connection failed. Check the alias, ProxyJump, known_hosts and authentication with ssh. Remote Jupyter session state is unknown."
    )
