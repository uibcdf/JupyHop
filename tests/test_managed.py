import io
import json
import os
import sys
from unittest.mock import patch

import pytest

from jupyhop import _managed_remote as remote
from jupyhop.errors import LaunchError, PrerequisiteError, ProtocolError, SSHError
from jupyhop.managed import parse_start, password_input, require_ready, start
from jupyhop.ssh import CommandResult, SSHTransport


@pytest.fixture
def start_wire():
    sid = "a" * 32
    runtime = "/state/sessions/" + sid + "/runtime"
    return {
        "protocol": {"major": 1, "minor": 2},
        "operation": "start",
        "data": {
            "id": sid,
            "state": "ready",
            "error": None,
            "record_path": "/state/sessions/" + sid + "/record.json",
            "identity": {"uid": 1000, "user": "researcher", "scope": "b" * 24},
            "server": {
                "id": sid,
                "observed_id": "c" * 24,
                "name": "analysis",
                "origin": "managed",
                "state": "ready",
                "reason": "verified",
                "pid": 123,
                "port": 8888,
                "address": "127.0.0.1",
                "base_url": "/jupyhop/" + sid + "/",
                "version": "2.21.1",
                "sources": [runtime],
            },
        },
    }


def test_start_password_is_stdin_only_and_extra_secret_fields_are_dropped(start_wire):
    start_wire["data"]["password"] = "PRIVATE_SENTINEL"
    start_wire["data"]["server"]["token"] = "PRIVATE_SENTINEL"
    result = CommandResult(0, json.dumps(start_wire).encode(), b"")
    with patch.object(SSHTransport, "run", return_value=result) as run:
        report = start(
            SSHTransport("workstation"),
            server_python="/env α/python",
            password="PRIVATE_SENTINEL",
            session_id="a" * 32,
        )
    assert "PRIVATE_SENTINEL" not in json.dumps(report)
    assert "PRIVATE_SENTINEL" not in repr(run.call_args.args)
    packet = json.loads(run.call_args.kwargs["stdin"])
    assert packet["request"]["password"] == "PRIVATE_SENTINEL"
    assert packet["request"]["server_python"] == "/env α/python"
    assert len(run.call_args.kwargs["stdin"]) < 65536


@pytest.mark.parametrize(
    "change,value",
    [
        ("state", "other"),
        ("id", "b" * 32),
        ("error", "PRIVATE_SENTINEL"),
        ("record_path", "http://outside.example/"),
    ],
)
def test_untrusted_start_response_fails_closed(start_wire, change, value):
    start_wire["data"][change] = value
    with pytest.raises(ProtocolError) as exc:
        parse_start(json.dumps(start_wire).encode(), "a" * 32)
    assert "PRIVATE_SENTINEL" not in str(exc.value)


@pytest.mark.parametrize(
    "error,kind",
    [
        ("readiness_timeout", LaunchError),
        ("launch_unknown", LaunchError),
        ("incompatible_registry", ProtocolError),
        ("missing_tmux", PrerequisiteError),
        ("invalid_workdir", PrerequisiteError),
    ],
)
def test_failed_launch_is_actionable_and_not_claimed_stopped(error, kind):
    with pytest.raises(kind):
        require_ready({"id": "a" * 32, "state": "starting", "error": error})


@pytest.mark.parametrize("name", ["../outside", "-option", "project;id", "a\nname", "", "x" * 65])
def test_start_name_validation_before_remote_execution(name):
    with patch.object(SSHTransport, "run") as run:
        with pytest.raises(ValueError):
            start(
                SSHTransport("workstation"),
                name=name,
                server_python="python3",
                password="fixture-password",
            )
        run.assert_not_called()


def test_password_stdin_and_noninteractive_prompt_policy(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"fixture-password\n")))
    assert password_input(True) == "fixture-password"
    monkeypatch.setattr(sys, "stdin", io.StringIO("fixture-password"))
    with pytest.raises(ValueError, match="--password-stdin"):
        password_input(False)


@pytest.mark.parametrize("data", [b"short\n", b"x\0password\n", b"\xffpassword\n", b"x" * 4097])
def test_invalid_password_input_is_not_reflected(monkeypatch, data):
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(data)))
    with pytest.raises(ValueError) as exc:
        password_input(True)
    assert "password\\n" not in str(exc.value)


@pytest.mark.parametrize("major,minor", [(2, 0), (1, 1), (True, 0)])
def test_incompatible_registry_is_rejected_before_writes(tmp_path, major, minor):
    root = tmp_path / "state"
    root.mkdir(mode=0o700)
    header = root / "registry.json"
    original = json.dumps({"producer": "jupyhop", "schema": {"major": major, "minor": minor}})
    header.write_text(original)
    header.chmod(0o600)
    with pytest.raises(remote.ManagedProblem, match="incompatible_registry"):
        with remote.Registry(str(root), create=True):
            pytest.fail("Incompatible state was opened for mutation")
    assert header.read_text() == original
    assert sorted(p.name for p in root.iterdir()) == ["registry.json"]


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo", "shared"])
def test_unsafe_lock_cannot_write_through_to_other_content(tmp_path, kind):
    root = tmp_path / "state"
    with remote.Registry(str(root), create=True) as registry:
        with registry.lock():
            pass
    lock = root / ".lock"
    lock.unlink()
    sentinel = tmp_path / "sentinel"
    sentinel.write_text("UNCHANGED")
    sentinel.chmod(0o600)
    if kind == "symlink":
        lock.symlink_to(sentinel)
    elif kind == "hardlink":
        lock.hardlink_to(sentinel)
    elif kind == "fifo":
        os.mkfifo(lock, 0o600)
    else:
        lock.write_bytes(b"")
        lock.chmod(0o644)
    with pytest.raises((OSError, remote.ManagedProblem)):
        with remote.Registry(str(root), create=True) as registry, registry.lock():
            pytest.fail("Unsafe state lock accepted")
    assert sentinel.read_text() == "UNCHANGED"


def test_atomic_write_failure_preserves_previous_record_and_cleans_temporary(tmp_path):
    descriptor = remote._private_dir(str(tmp_path))
    try:
        remote._save(descriptor, "record.json", {"state": "before"})
        with patch.object(os, "replace", side_effect=OSError):
            with pytest.raises(remote.ManagedProblem):
                remote._save(descriptor, "record.json", {"state": "after"})
        assert remote._load(descriptor, "record.json") == {"state": "before"}
        assert sorted(p.name for p in tmp_path.iterdir()) == ["record.json"]
        assert (tmp_path / "record.json").stat().st_mode & 0o777 == 0o600
    finally:
        os.close(descriptor)


def test_shared_home_uses_distinct_host_account_scopes(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    with patch("builtins.open", return_value=io.StringIO("a" * 32)):
        first = remote.state_root()
    with patch("builtins.open", return_value=io.StringIO("b" * 32)):
        second = remote.state_root()
    assert first != second
    assert "hosts" in first
    assert not list(tmp_path.iterdir())


def test_interrupted_transport_reports_request_id_without_credentials():
    with patch.object(SSHTransport, "run", side_effect=SSHError("SSH timed out")):
        with pytest.raises(LaunchError) as exc:
            start(
                SSHTransport("workstation"),
                server_python="python3",
                password="PRIVATE_SENTINEL",
                session_id="a" * 32,
            )
    assert "a" * 32 in str(exc.value)
    assert "PRIVATE_SENTINEL" not in str(exc.value)


def test_unreachable_managed_record_is_not_proof_of_server_death():
    record = {
        "id": "a" * 32,
        "name": "analysis",
        "state": "ready",
        "boot_id": remote.boot_id(),
        "pid": 123,
        "port": 8888,
        "base_url": "/",
        "runtime": "/runtime",
    }
    with patch.object(remote, "process_identity", side_effect=PermissionError):
        values = remote.missing_managed([record], set())
    assert values[0]["state"] == "unreachable"
