"""Bounded OpenSSH subprocess transport for Linux, with no config parser."""

import math
import os
import pwd
import re
import selectors
import shlex
import signal
import stat
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from jupyhop.errors import ProtocolError, SSHError

if TYPE_CHECKING:
    from jupyhop.connection import ConnectionPool

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
    connections: "ConnectionPool | None" = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        validate_alias(self.host)
        if not math.isfinite(self.timeout) or not 1 <= self.timeout <= 300:
            raise ValueError("Timeout must be between 1 and 300 seconds.")

    def options(self, *, control_path: Path | None = None, interactive: bool = False) -> list[str]:
        options = [
            "ssh",
            "-T",
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
            "ForkAfterAuthentication=no",
            "-o",
            f"ConnectTimeout={math.ceil(self.timeout)}",
            "-o",
            "ServerAliveInterval=5",
            "-o",
            "ServerAliveCountMax=2",
        ]
        if not interactive:
            options.extend(["-o", "BatchMode=yes"])
        if self.config is not None:
            options.extend(["-F", str(self.config.expanduser().resolve())])
        return options

    def command(self, argv: Sequence[str]) -> list[str]:
        return [*self.options(), self.host, remote_command(argv)]

    def run(self, argv: Sequence[str], *, stdin: bytes = b"") -> CommandResult:
        if len(stdin) > STDIN_LIMIT:
            raise ValueError("Remote probe input exceeds 64 KiB.")
        if self.connections is not None:
            remote_command(argv)
            return self.connections.get(self).run(list(argv), stdin=stdin)
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


def _configuration_failure(stderr: bytes, config: Path | None) -> SSHError:
    # The default comes from passwd, not an overridden HOME. Explicit -F uses
    # different OpenSSH checks; its errors must not be guessed to be local.
    try:
        path = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".ssh/config"
    except (KeyError, OSError):
        path = None
    label = "local ~/.ssh/config"
    local = False
    for line in stderr.splitlines():
        if line.startswith(b"ssh: "):
            line = line[5:]
        prefix = b"bad owner or permissions on "
        if (
            path is not None
            and line.lower().startswith(prefix)
            and line[len(prefix) :].strip() == os.fsencode(path)
        ):
            local = config is None
    if local and path is not None:
        try:
            info = path.stat()
            if stat.S_ISREG(info.st_mode):
                if info.st_uid not in {os.getuid(), 0}:
                    return SSHError(
                        f"OpenSSH rejected ownership of {label}. chmod alone cannot fix ownership; ask the intended owner/administrator to correct it, then retry ordinary ssh. No permissions were changed."
                    )
                if info.st_mode & 0o022:
                    remedy = "chmod 600 ~/.ssh/config"
                    return SSHError(
                        f"OpenSSH rejected {label} because it permits group/other writes. If this file belongs to you, run {remedy}, then retry ordinary ssh and JupyHop. A 0700 .ssh directory does not replace the file check. No permissions were changed."
                    )
        except OSError:
            pass
    return SSHError(
        "OpenSSH rejected ownership or write permissions of an SSH configuration file. Inspect the exact file and machine using ordinary ssh privately, including any gateway/include. For your own regular file, chmod 600 restricts access; incorrect ownership needs the intended owner/administrator. JupyHop did not change permissions or guess that the file is local."
    )


def ssh_failure(stderr: bytes, *, config: Path | None = None) -> SSHError:
    """Classify known messages without reflecting any untrusted output."""
    lowered = stderr.lower()
    if b"bad owner or permissions" in lowered:
        return _configuration_failure(stderr, config)
    if (
        b"host key verification failed" in lowered
        or b"remote host identification has changed" in lowered
    ):
        return SSHError(
            "SSH host-key verification failed. Verify the host fingerprint through a trusted channel and use ssh to manage known_hosts; JupyHop never bypasses verification."
        )
    if b"timed out" in lowered or b"timeout during banner" in lowered:
        return SSHError(
            "SSH connection/handshake timed out, possibly along the ProxyJump route. Verify ordinary ssh access. --timeout bounds connection/handshake and probes; --ssh-auth-timeout separately bounds terminal authentication. Remote Jupyter state is unknown; inspect status/discover before retrying a start."
        )
    if b"permission denied" in lowered:
        return SSHError(
            "SSH authentication denied. Check the configured User, key/agent or password access with ssh. For password/passphrase prompts run jupyhop from a terminal without --batch; scripts require noninteractive OpenSSH authentication."
        )
    return SSHError(
        "SSH connection failed. Check the alias, ProxyJump, known_hosts and authentication with ssh. Remote Jupyter session state is unknown."
    )
