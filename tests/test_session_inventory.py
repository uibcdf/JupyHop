import copy
import hashlib
import json
import os
import sys
from unittest.mock import patch

import pytest

from jupyhop import _inventory_remote as remote
from jupyhop import _managed_remote as state
from jupyhop.errors import ProtocolError
from jupyhop.session_inventory import inspect_sessions, parse_inventory, summary
from jupyhop.ssh import STDIN_LIMIT, CommandResult, SSHTransport


@pytest.fixture
def wire():
    return {
        "protocol": {"major": 1, "minor": 5},
        "operation": "inventory",
        "data": {
            "identity": {"uid": 1000, "user": "researcher", "scope": "b" * 24},
            "sessions": [
                {
                    "id": "a" * 32,
                    "name": "analysis",
                    "state": "stopped",
                    "reason": "managed_stopped",
                }
            ],
            "complete": True,
            "history": {"entries": [], "offset": 0, "next_offset": None, "complete": True},
            "error": None,
            "history_error": None,
        },
    }


def archive_entry(registry, sid, name="analysis"):
    path = os.path.join(registry.root, "archive", sid)
    descriptor = state._private_dir(path, True)
    try:
        state._write(descriptor, "launch.py", b"pass\n")
        record = {
            "schema": state.SCHEMA,
            "id": sid,
            "owner_uid": os.getuid(),
            "name": name,
            "state": "failed",
            "manager": "tmux",
            "runtime": os.path.join(registry.root, "sessions", sid, "runtime"),
            "workdir": registry.root,
            "server_python": sys.executable,
            "socket": os.path.join(registry.root, "missing.sock"),
            "base_url": "/jupyhop/" + sid + "/",
            "boot_id": state.boot_id(),
            "pid": None,
            "port": None,
            "process_start": None,
            "socket_inode": None,
            "runner_sha256": hashlib.sha256(b"pass\n").hexdigest(),
            "error": "launch_failed",
        }
        state._save(descriptor, "record.json", record)
        state._write(descriptor, "settings.json", b"PRIVATE_SENTINEL")
    finally:
        os.close(descriptor)


def test_history_is_read_only_allowlisted_and_reports_a_bounded_page(tmp_path):
    with state.Registry(str(tmp_path / "registry"), create=True) as registry:
        with registry.lock():
            pass
        for index in range(65):
            archive_entry(registry, f"{index:032x}")
        before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
        page = remote.inventory_history(registry, 0)
        assert len(page["entries"]) == 64 and page["next_offset"] == 64
        assert page["complete"] is False
        later = remote.inventory_history(registry, 64)
        assert len(later["entries"]) == 1 and later["next_offset"] is None
        assert later["complete"] is False  # A page is not an exact total.
        assert not ({e["id"] for e in page["entries"]} & {e["id"] for e in later["entries"]})
        assert "PRIVATE_SENTINEL" not in json.dumps(page)
        assert {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("kind", ["archive", "entry", "record", "runner"])
def test_history_refuses_symlinks_at_every_private_boundary(tmp_path, kind):
    root = tmp_path / "registry"
    with state.Registry(str(root), create=True) as registry:
        with registry.lock():
            pass
        archive_entry(registry, "a" * 32)
        target = root / "archive"
        if kind != "archive":
            target = target / ("a" * 32)
        if kind in {"record", "runner"}:
            target = target / ("record.json" if kind == "record" else "launch.py")
        external = tmp_path / "outside"
        target.rename(external)
        target.symlink_to(external, target_is_directory=external.is_dir())
        with pytest.raises((OSError, state.ManagedProblem)):
            remote.inventory_history(registry, 0)
        assert target.is_symlink()


def test_missing_history_is_zero_only_for_the_first_complete_page(tmp_path):
    with state.Registry(str(tmp_path / "registry"), create=True) as registry:
        assert remote.inventory_history(registry, 0)["complete"]
        assert not remote.inventory_history(registry, 64)["complete"]


def test_inventory_parser_excludes_secrets_and_unknown_fields(wire):
    wire["data"]["identity"]["password"] = "PRIVATE_SENTINEL"
    wire["data"]["sessions"][0]["token"] = "PRIVATE_SENTINEL"
    wire["data"]["history"]["entries"] = [
        {
            "id": "c" * 32,
            "name": "analysis",
            "record_state": "exited",
            "settings": "PRIVATE_SENTINEL",
        }
    ]
    result = parse_inventory(json.dumps(wire).encode())
    assert "PRIVATE_SENTINEL" not in json.dumps(result)
    assert summary(result) == {
        "ready": 0,
        "stopped": 1,
        "review": 0,
        "unarchived": 1,
        "archived": 1,
        "archive_count_exact": True,
    }


def test_unknown_active_or_archive_counts_are_never_presented_as_zero(wire):
    wire["data"].update(
        complete=False, error="time_limit", history=None, history_error="time_limit"
    )
    result = summary(parse_inventory(json.dumps(wire).encode()))
    assert all(
        result[key] is None for key in ("ready", "stopped", "review", "unarchived", "archived")
    )
    assert result["archive_count_exact"] is False


@pytest.mark.parametrize(
    "change",
    [
        {"protocol": {"major": 2, "minor": 5}},
        {"protocol": {"major": 1, "minor": True}},
        {"operation": "stop"},
    ],
)
def test_inventory_protocol_negotiation_is_strict(wire, change):
    wire.update(change)
    with pytest.raises(ProtocolError):
        parse_inventory(json.dumps(wire).encode())


@pytest.mark.parametrize(
    "mutation", ["duplicate", "bad_name", "bad_offset", "false_complete", "unknown_error"]
)
def test_malformed_inventory_does_not_reach_user_output(wire, mutation):
    data = wire["data"]
    if mutation == "duplicate":
        data["sessions"].append(copy.deepcopy(data["sessions"][0]))
    elif mutation == "bad_name":
        data["sessions"][0]["name"] = "PRIVATE_SENTINEL\x1b"
    elif mutation == "bad_offset":
        data["history"]["next_offset"] = True
    elif mutation == "false_complete":
        data["error"] = "corrupt_state"
    else:
        data["error"] = "PRIVATE_SENTINEL"
    with pytest.raises(ProtocolError) as error:
        parse_inventory(json.dumps(wire).encode())
    assert "PRIVATE_SENTINEL" not in str(error.value)


def test_inventory_bootstrap_fits_existing_stdin_limit_and_keeps_remote_package_optional(wire):
    def run(self, argv, *, stdin=b""):
        assert len(stdin) <= STDIN_LIMIT
        namespace = {"__name__": "jupyhop_remote"}
        payload = json.loads(stdin)
        for source in payload["sources"]:
            exec(compile(source, "<fixture-remote>", "exec"), namespace)
        assert callable(namespace["inventory_main"])
        return CommandResult(0, json.dumps(wire).encode(), b"")

    with patch.object(SSHTransport, "run", run):
        report = inspect_sessions(SSHTransport("workstation"))
    assert report["host"] == "workstation" and report["sessions"][0]["name"] == "analysis"


@pytest.mark.parametrize("offset", [True, -1, 4097, 1.0])
def test_history_offset_is_validated_before_ssh(offset):
    with patch.object(SSHTransport, "run") as run:
        with pytest.raises(ValueError):
            inspect_sessions(SSHTransport("workstation"), history_offset=offset)
        run.assert_not_called()
