import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from jupyhop.doctor import diagnose
from jupyhop.errors import PrerequisiteError, SSHError
from jupyhop.ssh import SSHTransport, ssh_failure

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("host", ["direct", "destination"])
def test_doctor_direct_and_proxyjump(ssh_lab, host):
    report = diagnose(SSHTransport(host, config=ssh_lab.config), sys.executable)
    assert report["ok"]
    assert report["data"]["identity"]["uid"] == os.getuid()
    assert report["data"]["jupyter_server"]["version"]
    assert report["data"]["coverage"] == "selected-interpreter-only"
    assert "token" not in json.dumps(report)


def test_include_match_and_proxyjump_resolved_by_openssh(ssh_lab):
    result = subprocess.run(
        ["ssh", "-F", str(ssh_lab.config), "-G", "destination"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "proxyjump gateway" in result.stdout
    assert "serveraliveinterval 5" in result.stdout


def test_unknown_host_key_is_refused(ssh_lab, tmp_path):
    known = tmp_path / "empty_known_hosts"
    known.touch()
    config = tmp_path / "unknown.conf"
    config.write_text(f"Host *\n    UserKnownHostsFile {known}\n" + ssh_lab.config.read_text())
    result = SSHTransport("direct", config=config).run(["id", "-u"])
    assert result.returncode == 255
    assert "host-key" in str(ssh_failure(result.stderr))


def test_changed_host_key_is_refused(ssh_lab, tmp_path):
    other = tmp_path / "other"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "fixture", "-f", str(other)],
        check=True,
    )
    known = tmp_path / "wrong_known_hosts"
    known.write_text(f"[127.0.0.1]:{ssh_lab.ports[1]} {other.with_suffix('.pub').read_text()}")
    config = tmp_path / "wrong.conf"
    config.write_text(f"Host *\n    UserKnownHostsFile {known}\n" + ssh_lab.config.read_text())
    result = SSHTransport("direct", config=config).run(["id", "-u"])
    assert result.returncode == 255
    assert "host-key" in str(ssh_failure(result.stderr))


def test_remote_shell_injection_is_literal(ssh_lab):
    sentinel = ssh_lab.root / "must-not-exist"
    value = f"α whitespace '; $(touch {sentinel}) `touch {sentinel}`"
    result = SSHTransport("destination", config=ssh_lab.config).run(
        [sys.executable, "-c", "import sys; print(sys.argv[1])", value]
    )
    assert result.returncode == 0
    assert result.stdout.decode().strip() == value
    assert not sentinel.exists()


def test_absolute_interpreter_path_with_spaces_and_unicode(ssh_lab):
    directory = ssh_lab.root / "remote env α"
    directory.mkdir()
    python = directory / "python"
    python.symlink_to(sys.executable)
    report = diagnose(SSHTransport("direct", config=ssh_lab.config), str(python))
    assert report["ok"]


def test_missing_remote_python_is_actionable(ssh_lab):
    with pytest.raises(PrerequisiteError, match="--remote-python"):
        diagnose(SSHTransport("direct", config=ssh_lab.config), str(ssh_lab.root / "absent-python"))


def test_fresh_python_without_jupyter_is_reported(ssh_lab):
    venv = ssh_lab.root / "empty-environment"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
    report = diagnose(SSHTransport("destination", config=ssh_lab.config), str(venv / "bin/python"))
    assert not report["ok"]
    assert report["missing"] == ["jupyter_server", "jupyter_core"]


def test_unavailable_jump_does_not_claim_server_stopped(ssh_lab, tmp_path):
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))  # Bound, not listening: cannot race another service.
        port = reserved.getsockname()[1]
        config = tmp_path / "unreachable.conf"
        config.write_text(f"Host gateway\n    Port {port}\n" + ssh_lab.config.read_text())
        with pytest.raises(SSHError, match="unknown"):
            diagnose(SSHTransport("destination", config=config, timeout=5), sys.executable)


def test_cli_integration_stdout_is_json(ssh_lab):
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "jupyhop",
            "doctor",
            "destination",
            "--ssh-config",
            str(ssh_lab.config),
            "--remote-python",
            sys.executable,
            "--json",
        ],
        env=environment,
        capture_output=True,
        check=True,
    )
    assert json.loads(result.stdout)["ok"]
    assert result.stderr == b""
