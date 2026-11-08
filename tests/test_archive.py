import hashlib
import io
import json
import os
import sys
from unittest.mock import patch

import pytest

from jupyhop import _archive_remote as remote
from jupyhop import _managed_remote as state
from jupyhop._discovery_probe import process_identity
from jupyhop.cli import main
from jupyhop.errors import ProtocolError
from jupyhop.lifecycle import parse_lifecycle
from jupyhop.ssh import SSHTransport


def test_archive_requires_explicit_authorization_before_ssh():
    with patch.object(SSHTransport, "run") as run, patch("sys.stdin.isatty", return_value=False):
        assert main(["archive", "workstation", "a" * 32]) == 11
        run.assert_not_called()


@pytest.fixture
def retired(tmp_path):
    root, sid = tmp_path / "registry", "a" * 32
    with state.Registry(str(root), create=True) as registry:
        with registry.lock():
            os.mkdir(sid, mode=0o700, dir_fd=registry.sessions)
        session = root / "sessions" / sid
        record = {
            "schema": state.SCHEMA,
            "id": sid,
            "name": "analysis",
            "owner_uid": os.getuid(),
            "state": "exited",
            "manager": "tmux",
            "runtime": str(session / "runtime"),
            "workdir": str(tmp_path),
            "server_python": sys.executable,
            "socket": str(tmp_path / "missing.sock"),
            "base_url": "/jupyhop/" + sid + "/",
            "boot_id": state.boot_id(),
            "pid": 2147483647,
            "port": 8888,
            "process_start": "1",
            "socket_inode": "123",
            "runner_sha256": hashlib.sha256(b"pass\n").hexdigest(),
            "error": None,
        }
        with registry.session(sid) as descriptor:
            state._write(descriptor, "launch.py", b"pass\n")
            state._save(descriptor, "record.json", record)
        (session / "runtime").mkdir(mode=0o700)
        (session / "runtime/kernel-recovery.json").write_text("PRIVATE_SENTINEL")
    yield root, sid, record


def test_archive_is_atomic_idempotent_and_preserves_recovery_evidence(retired):
    root, sid, record = retired
    with patch.object(remote, "Registry", side_effect=lambda: state.Registry(str(root))):
        result = remote.archive_record(sid)
        assert remote.archive_record(sid) == result
    archived = root / "archive" / sid
    assert not (root / "sessions" / sid).exists()
    assert json.loads((archived / "record.json").read_text()) == record
    assert (archived / "runtime/kernel-recovery.json").read_text() == "PRIVATE_SENTINEL"
    assert "PRIVATE_SENTINEL" not in json.dumps(result)
    with state.Registry(str(root)) as registry:
        assert registry.records() == []


@pytest.mark.parametrize(
    "change",
    [
        {"pid": os.getpid(), "process_start": process_identity(os.getpid())},
        {"pid": os.getpid(), "process_start": process_identity(os.getpid()), "boot_id": "old-boot"},
        {"pid": None, "process_start": None, "state": "requested"},
    ],
)
def test_live_or_unconfirmed_session_cannot_be_retired(retired, change):
    root, sid, record = retired
    record.update(change)
    path = root / "sessions" / sid / "record.json"
    path.write_text(json.dumps(record))
    before = path.read_bytes()
    with patch.object(remote, "Registry", side_effect=lambda: state.Registry(str(root))):
        with pytest.raises(state.ManagedProblem):
            remote.archive_record(sid)
    assert path.read_bytes() == before and not (root / "archive").exists()


def test_archive_refuses_incompatible_schema_before_changes(retired):
    root, sid, _ = retired
    header = root / "registry.json"
    raw = b'{"producer":"jupyhop","schema":{"major":1,"minor":1}}'
    header.write_bytes(raw)
    with patch.object(remote, "Registry", side_effect=lambda: state.Registry(str(root))):
        with pytest.raises(state.ManagedProblem, match="incompatible_registry"):
            remote.archive_record(sid)
    assert header.read_bytes() == raw and not (root / "archive").exists()


def test_damaged_start_time_and_missing_socket_cannot_hide_live_launcher(retired):
    root, sid, _ = retired
    launcher = root / "sessions" / sid / "launch.py"
    cmdline = b"/usr/bin/python\0-I\0-B\0" + os.fsencode(launcher) + b"\0"
    with (
        patch.object(remote, "Registry", side_effect=lambda: state.Registry(str(root))),
        patch.object(remote, "process_identity", return_value="different-start"),
        patch("builtins.open", return_value=io.BytesIO(cmdline)),
    ):
        with pytest.raises(state.ManagedProblem, match="session_active"):
            remote.archive_record(sid)
    assert (root / "sessions" / sid).is_dir() and not (root / "archive").exists()


def test_archive_never_follows_an_archive_symlink(retired, tmp_path):
    root, sid, _ = retired
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "archive").symlink_to(outside, target_is_directory=True)
    with patch.object(remote, "Registry", side_effect=lambda: state.Registry(str(root))):
        with pytest.raises((OSError, state.ManagedProblem)):
            remote.archive_record(sid)
    assert list(outside.iterdir()) == [] and (root / "sessions" / sid).is_dir()


def test_archive_wire_drops_unknown_secrets_and_rejects_unexpected_path():
    sid = "a" * 32
    wire = {
        "protocol": {"major": 1, "minor": 4},
        "operation": "archive",
        "data": {
            "identity": {"uid": 1000, "user": "researcher", "scope": "b" * 24},
            "complete": False,
            "paths": [],
            "servers": [],
            "issues": [],
            "error": None,
            "archived": {
                "id": sid,
                "path": "/state/archive/" + sid,
                "password": "PRIVATE_SENTINEL",
            },
        },
    }
    assert "PRIVATE_SENTINEL" not in json.dumps(
        parse_lifecycle(json.dumps(wire).encode(), "archive")
    )
    wire["data"]["archived"]["path"] = "/state/other"
    with pytest.raises(ProtocolError):
        parse_lifecycle(json.dumps(wire).encode(), "archive")
