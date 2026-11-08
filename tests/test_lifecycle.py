import copy
import ctypes
import hashlib
import json
import os
import signal
import subprocess
import sys
from unittest.mock import patch

import pytest

from jupyhop import _lifecycle_remote as remote
from jupyhop import _managed_remote as state
from jupyhop._discovery_probe import process_identity
from jupyhop.cli import main
from jupyhop.errors import LifecycleError, OwnershipError, ProtocolError, SSHError
from jupyhop.lifecycle import lifecycle, parse_lifecycle
from jupyhop.ssh import SSHTransport


@pytest.fixture
def lifecycle_wire():
    return {
        "protocol": {"major": 1, "minor": 3},
        "operation": "status",
        "data": {
            "identity": {"uid": 1000, "user": "researcher", "scope": "b" * 24},
            "complete": False,
            "paths": [],
            "servers": [],
            "issues": [],
            "error": None,
        },
    }


@pytest.mark.parametrize("identifier", ["a" * 24, "analysis", "../session", "123", "", "a" * 33])
def test_stop_never_resolves_names_pids_or_unmanaged_ids(identifier):
    with patch.object(SSHTransport, "run") as run:
        with pytest.raises(OwnershipError):
            lifecycle(SSHTransport("workstation"), "stop", identifier)
        run.assert_not_called()


def test_stop_requires_confirmation_before_any_ssh(capsys):
    with patch.object(SSHTransport, "run") as run, patch("sys.stdin.isatty", return_value=False):
        assert main(["stop", "workstation", "a" * 32]) == 11
        run.assert_not_called()
    assert "kernels" in capsys.readouterr().err


@pytest.mark.parametrize(
    "field,value",
    [
        ("protocol", {"major": 2, "minor": 3}),
        ("operation", "start"),
        ("protocol", {"major": 1, "minor": True}),
    ],
)
def test_lifecycle_protocol_negotiation(lifecycle_wire, field, value):
    lifecycle_wire[field] = value
    with pytest.raises(ProtocolError):
        parse_lifecycle(json.dumps(lifecycle_wire).encode(), "status")


def test_lifecycle_drops_unknown_secret_fields_and_accepts_future_minor(lifecycle_wire):
    lifecycle_wire["data"]["token"] = "PRIVATE_SENTINEL"
    lifecycle_wire["data"]["identity"]["password"] = "PRIVATE_SENTINEL"
    lifecycle_wire["protocol"]["minor"] = 25
    assert "PRIVATE_SENTINEL" not in json.dumps(
        parse_lifecycle(json.dumps(lifecycle_wire).encode(), "status")
    )


@pytest.mark.parametrize("raw", [b"", b"null", b"[]", b"{}", b"[" * 10000, b"x" * 65537])
def test_bad_lifecycle_output_is_bounded_and_suppressed(raw):
    with pytest.raises(ProtocolError):
        parse_lifecycle(raw, "stop")


def test_stop_transport_loss_never_claims_server_is_stopped():
    with patch.object(SSHTransport, "run", side_effect=SSHError("PRIVATE_SENTINEL")):
        with pytest.raises(LifecycleError, match="status") as exc:
            lifecycle(SSHTransport("workstation"), "stop", "a" * 32)
    assert "PRIVATE_SENTINEL" not in str(exc.value)


def test_pidfd_pins_one_fixture_process_even_after_exit():
    with subprocess.Popen(["/bin/sleep", "30"]) as child:
        pinned = remote.PinnedProcess(child.pid)
        try:
            assert not pinned.exited()
            pinned.send_term()
            assert pinned.exited(3)
            assert child.wait(timeout=3) == -signal.SIGTERM
            with pytest.raises(ProcessLookupError):
                pinned.send_term()
        finally:
            pinned.close()


def test_pidfd_missing_fails_closed_without_pid_signal(monkeypatch):
    monkeypatch.delattr(os, "pidfd_open", raising=False)
    monkeypatch.delattr(signal, "pidfd_send_signal", raising=False)
    with patch.object(ctypes, "CDLL", side_effect=AttributeError), patch.object(os, "kill") as kill:
        with pytest.raises(state.ManagedProblem, match="pidfd_unavailable"):
            remote.PinnedProcess(os.getpid())
        kill.assert_not_called()


@pytest.fixture
def registry(tmp_path):
    sid = "a" * 32
    with state.Registry(str(tmp_path / "registry"), create=True) as registry:
        with registry.lock():
            os.mkdir(sid, mode=0o700, dir_fd=registry.sessions)
        root = os.path.join(registry.root, "sessions", sid)
        record = {
            "schema": state.SCHEMA,
            "id": sid,
            "owner_uid": os.getuid(),
            "name": "analysis",
            "state": "ready",
            "manager": "tmux",
            "runtime": root + "/runtime",
            "workdir": str(tmp_path),
            "server_python": sys.executable,
            "socket": str(tmp_path / "tmux.sock"),
            "base_url": "/jupyhop/" + sid + "/",
            "boot_id": state.boot_id(),
            "pid": os.getpid(),
            "process_start": process_identity(os.getpid()),
            "port": 8888,
            "socket_inode": "123",
            "runner_sha256": hashlib.sha256(b"pass\n").hexdigest(),
            "error": None,
        }
        with registry.session(sid) as descriptor:
            state._write(descriptor, "launch.py", b"pass\n")
            state._save(descriptor, "record.json", record)
        yield registry, sid, record


def test_stop_intent_survives_interruption_before_signal_and_can_be_retried(registry):
    registry, sid, record = registry
    with (
        patch.object(remote, "runner_matches", return_value=True),
        patch.object(remote, "listener_inode", return_value="123"),
        patch.object(remote, "PinnedProcess") as pinned,
    ):
        instance = pinned.return_value
        instance.exited.return_value = False
        instance.send_term.side_effect = InterruptedError
        with pytest.raises(InterruptedError):
            remote._stop(registry, sid, 1)
        assert registry.records()[0]["stop_requested"] is True
        instance.send_term.side_effect = None
        instance.exited.side_effect = [False, True]
        remote._stop(registry, sid, 1)
        assert instance.send_term.call_count == 2
        assert instance.close.call_count == 2


def test_old_boot_and_reused_pid_never_authorize_a_signal(registry):
    registry, sid, original = registry
    for changed in ({"boot_id": "old-boot"}, {"process_start": "1"}):
        record = copy.deepcopy(original)
        record.update(changed)
        with registry.session(sid) as descriptor:
            state._save(descriptor, "record.json", record)
        with patch.object(remote, "PinnedProcess") as pinned:
            remote._stop(registry, sid, 0)
            pinned.assert_not_called()
        assert registry.records()[0] == record


def test_same_pid_without_launcher_provenance_is_not_stopped(registry):
    registry, sid, record = registry
    with patch.object(remote, "PinnedProcess") as pinned:
        pinned.return_value.exited.return_value = False
        with pytest.raises(state.ManagedProblem, match="unverified_owner"):
            remote._stop(registry, sid, 0)
        pinned.return_value.send_term.assert_not_called()
        assert registry.records()[0] == record
