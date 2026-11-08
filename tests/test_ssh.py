import os
import shlex
import subprocess
import sys
import time

import pytest

from jupyhop.errors import ProtocolError, SSHError
from jupyhop.ssh import SSHTransport, _run_bounded, remote_command, ssh_failure


@pytest.mark.parametrize(
    "alias",
    [
        "-oProxyCommand=id",
        "user@host",
        "host;id",
        "host\nother",
        "$(id)",
        "",
        "host alias",
        "host\0",
        "ssh://host",
    ],
)
def test_reject_host_option_and_shell_injection(alias):
    with pytest.raises(ValueError):
        SSHTransport(alias)


@pytest.mark.parametrize("timeout", [0, -1, 301, float("nan"), float("inf")])
def test_bounded_timeout_configuration(timeout):
    with pytest.raises(ValueError):
        SSHTransport("workstation", timeout=timeout)


def test_remote_quoting_and_transport_contract(tmp_path):
    values = ["/remote path/α/python", "", "a'b", "$(touch sentinel); `id`", "~", "line\nline"]
    assert shlex.split(remote_command(values)) == values
    command = SSHTransport("workstation", config=tmp_path / "custom config").command(values)
    assert command[-2:] == ["workstation", shlex.join(values)]
    assert "StrictHostKeyChecking=yes" in command
    assert "BatchMode=yes" in command
    assert "ControlPath=none" in command
    assert "ClearAllForwardings=yes" in command
    assert "PermitLocalCommand=no" in command
    assert "ForwardAgent=no" in command
    assert "-J" not in command  # OpenSSH handles configured routes.


@pytest.mark.parametrize("argv", [[], [""], ["python3", "\0"]])
def test_remote_command_validation(argv):
    with pytest.raises(ValueError):
        remote_command(argv)


def test_stdin_round_trip_without_local_shell():
    payload = b"literal $(id); `id` and unicode \xce\xb1"
    result = _run_bounded(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"],
        payload,
        2,
    )
    assert result.returncode == 0
    assert result.stdout == payload


@pytest.mark.parametrize("stream,limit", [("stdout", 65536), ("stderr", 32768)])
def test_output_limits_terminate_owned_process(stream, limit, tmp_path):
    pidfile = tmp_path / "pid"
    program = f"import os,sys,time; open(sys.argv[1],'w').write(str(os.getpid())); sys.{stream}.write('x'*{limit + 8192}); sys.{stream}.flush(); time.sleep(20)"
    with pytest.raises(ProtocolError, match="size limit"):
        _run_bounded([sys.executable, "-c", program, str(pidfile)], b"", 2)
    with pytest.raises(ProcessLookupError):
        os.kill(int(pidfile.read_text()), 0)


def test_timeout_includes_blocked_stdin_and_kills_process(tmp_path):
    pidfile = tmp_path / "pid"
    program = "import os,sys,time; open(sys.argv[1],'w').write(str(os.getpid())); time.sleep(20)"
    started = time.monotonic()
    with pytest.raises(SSHError, match="timed out"):
        _run_bounded([sys.executable, "-c", program, str(pidfile)], b"x" * 65536, 0.2)
    assert time.monotonic() - started < 3
    with pytest.raises(ProcessLookupError):
        os.kill(int(pidfile.read_text()), 0)


def test_missing_openssh_diagnostic(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("private arbitrary error")

    monkeypatch.setattr(subprocess, "Popen", missing)
    with pytest.raises(SSHError, match="Install ssh") as exc:
        SSHTransport("workstation").run(["true"])
    assert "private" not in str(exc.value)


def test_error_messages_never_reflect_raw_output():
    for text in (b"host key verification failed", b"Permission denied", b"untrusted banner"):
        message = str(ssh_failure(text + b" ?token=PRIVATE_SENTINEL"))
        assert "PRIVATE_SENTINEL" not in message
        assert "?token=" not in message


def test_oversized_probe_is_rejected_before_spawn():
    with pytest.raises(ValueError, match="64 KiB"):
        SSHTransport("workstation").run(["python3"], stdin=b"x" * 65537)
