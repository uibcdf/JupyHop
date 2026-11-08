import io
import json
import os
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from jupyhop import _discovery_probe as remote
from jupyhop.cli import main
from jupyhop.discovery import discover, select_server, validate_paths, validate_python
from jupyhop.errors import DiscoveryError, ProtocolError, SelectionError
from jupyhop.protocol import parse_discovery
from jupyhop.ssh import CommandResult, SSHTransport


@pytest.fixture
def discovery_wire():
    return {
        "protocol": {"major": 1, "minor": 1},
        "operation": "discover",
        "data": {
            "identity": {"uid": 1000, "user": "researcher", "scope": "a" * 24},
            "complete": False,
            "paths": [{"path": "/runtime", "source": "explicit", "status": "ok"}],
            "issues": [],
            "servers": [
                {
                    "id": "b" * 24,
                    "origin": "unmanaged",
                    "state": "ready",
                    "reason": "verified",
                    "pid": 123,
                    "port": 8888,
                    "address": "127.0.0.1",
                    "base_url": "/science/",
                    "version": "2.21.1",
                    "sources": ["/runtime"],
                }
            ],
        },
    }


def test_discovery_protocol_excludes_all_credential_fields(discovery_wire):
    discovery_wire["data"]["token"] = "PRIVATE_SENTINEL"
    discovery_wire["data"]["servers"][0]["url"] = "http://localhost/?token=PRIVATE_SENTINEL"
    discovery_wire["data"]["servers"][0]["password"] = "PRIVATE_SENTINEL"
    result = parse_discovery(json.dumps(discovery_wire).encode())
    assert "PRIVATE_SENTINEL" not in json.dumps(result)
    assert not result["data"]["complete"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("port", True),
        ("port", 0),
        ("port", 65536),
        ("address", "0.0.0.0"),
        ("origin", "managed"),
        ("base_url", "//evil.example/"),
        ("base_url", "/?token=PRIVATE_SENTINEL"),
        ("version", "PRIVATE_SENTINEL"),
        ("sources", ["/not-searched"]),
        ("id", "name;id"),
    ],
)
def test_untrusted_discovery_fields_rejected(discovery_wire, field, value):
    discovery_wire["data"]["servers"][0][field] = value
    with pytest.raises(ProtocolError) as exc:
        parse_discovery(json.dumps(discovery_wire).encode())
    assert "PRIVATE_SENTINEL" not in str(exc.value)


def test_major_mismatch_is_non_destructive(discovery_wire):
    discovery_wire["protocol"]["major"] = 2
    with pytest.raises(ProtocolError, match="major"):
        parse_discovery(json.dumps(discovery_wire).encode())


def test_explicit_environments_deduplicate_and_preserve_coverage(discovery_wire):
    result = CommandResult(0, json.dumps(discovery_wire).encode(), b"")
    with patch.object(SSHTransport, "run", return_value=result) as run:
        report = discover(
            SSHTransport("workstation"), ["/env one/python", "/env two/python"], ["~/custom"]
        )
    assert len(report["servers"]) == 1
    assert len(report["coverage"]["paths"]) == 1
    assert not report["coverage"]["complete"]
    assert run.call_count == 2
    assert json.loads(run.call_args.args[0][-1])["runtime_dirs"] == ["~/custom"]


def test_changing_alias_identity_fails_closed(discovery_wire):
    first = json.dumps(discovery_wire).encode()
    discovery_wire["data"]["identity"]["scope"] = "c" * 24
    with patch.object(
        SSHTransport,
        "run",
        side_effect=[
            CommandResult(0, first, b""),
            CommandResult(0, json.dumps(discovery_wire).encode(), b""),
        ],
    ):
        with pytest.raises(ProtocolError, match="different remote"):
            discover(SSHTransport("workstation"), ["/env/a", "/env/b"])


@pytest.mark.parametrize(
    "base",
    [
        "//evil.example/",
        "/../",
        "/x/./",
        "/x\\y/",
        "/x/?token=x",
        "/%2f/",
        "relative/",
        "/x\n/",
        "/no-trailing-slash",
    ],
)
def test_unsupported_base_paths_are_not_browser_urls(base):
    assert not remote.valid_base(base)


@pytest.mark.parametrize(
    "path", ["relative", "~other/runtime", "/x/../y", "/bad\npath", "x" * 1025]
)
def test_runtime_path_policy(path):
    with pytest.raises(ValueError):
        validate_paths([path])


def test_runtime_paths_and_explicit_python_preserve_literal_unicode():
    assert validate_paths(["~/runtime α", "/absolute with spaces"]) == [
        "~/runtime α",
        "/absolute with spaces",
    ]
    assert validate_python("/env α/python") == "/env α/python"


def test_read_only_metadata_does_not_delete_stale_or_expose_token(tmp_path):
    path = tmp_path / "jpserver-2147483647.json"
    raw = json.dumps(
        {
            "pid": 2147483647,
            "port": 8888,
            "base_url": "/",
            "hostname": "127.0.0.1",
            "secure": False,
            "token": "PRIVATE_SENTINEL",
        }
    )
    path.write_text(raw)
    path.chmod(0o600)
    directory = remote._directory(str(tmp_path))
    try:
        record = remote._candidate(directory, path.name, str(tmp_path), "a" * 24)
    finally:
        os.close(directory)
    assert record["state"] == "stale"
    assert path.read_text() == raw
    assert "PRIVATE_SENTINEL" not in json.dumps(record)


@pytest.mark.parametrize(
    "kind", ["symlink", "hardlink", "fifo", "oversized", "world-readable", "malformed"]
)
def test_unsafe_metadata_is_rejected_without_modification(tmp_path, kind):
    path = tmp_path / "jpserver-123.json"
    if kind == "symlink":
        target = tmp_path / "secret"
        target.write_text("PRIVATE_SENTINEL")
        path.symlink_to(target)
    elif kind == "hardlink":
        target = tmp_path / "secret"
        target.write_text("PRIVATE_SENTINEL")
        target.chmod(0o600)
        path.hardlink_to(target)
    elif kind == "fifo":
        os.mkfifo(path, mode=0o600)
    else:
        path.write_text("x" * 16385 if kind == "oversized" else "not json")
        path.chmod(0o644 if kind == "world-readable" else 0o600)
    directory = remote._directory(str(tmp_path))
    try:
        record = remote._candidate(directory, path.name, str(tmp_path), "a" * 24)
    finally:
        os.close(directory)
    assert record["state"] == "unsupported"
    assert "PRIVATE_SENTINEL" not in json.dumps(record)
    assert path.lstat()


def test_directory_symlinks_and_shared_permissions_are_rejected(tmp_path):
    target = tmp_path / "runtime"
    target.mkdir(mode=0o700)
    link = tmp_path / "linked"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(OSError):
        remote._directory(str(link))
    target.chmod(0o750)
    with pytest.raises(remote.Unsupported):
        remote._directory(str(target))


def test_selection_never_guesses_and_excludes_stale():
    first = {"id": "a" * 24, "state": "ready", "port": 8888, "base_url": "/"}
    second = dict(first, id="b" * 24)
    stale = dict(first, id="c" * 24, state="stale")
    with pytest.raises(DiscoveryError, match="partial"):
        select_server({"servers": [stale]}, None, interactive=False)
    assert select_server({"servers": [first, stale]}, None, interactive=False) == first
    with pytest.raises(SelectionError):
        select_server({"servers": [first, second]}, None, interactive=False)
    with patch("sys.stdin", io.StringIO("2\n")):
        assert select_server({"servers": [first, second]}, None, interactive=True) == second
    assert select_server({"servers": [first, second]}, second["id"], interactive=False) == second


def test_stop_is_refused_without_any_remote_action(capsys):
    with patch.object(SSHTransport, "run") as run:
        assert main(["stop", "workstation", "a" * 24]) == 11
        run.assert_not_called()
    assert "unmanaged" in capsys.readouterr().err


def test_empty_json_discovery_is_partial_and_has_stable_exit(discovery_wire, capsys):
    discovery_wire["data"]["servers"] = []
    with patch.object(
        SSHTransport, "run", return_value=CommandResult(0, json.dumps(discovery_wire).encode(), b"")
    ):
        assert main(["discover", "workstation", "--json"]) == 6
    output = capsys.readouterr()
    assert not json.loads(output.out)["coverage"]["complete"]
    assert "partial" in output.err
    assert "--runtime-dir" in output.err


@pytest.mark.parametrize("available,no_browser", [(True, False), (False, False), (False, True)])
def test_browser_and_headless_open_print_only_verified_login_url(
    discovery_wire, capsys, available, no_browser
):
    report = {
        "identity": discovery_wire["data"]["identity"],
        "servers": discovery_wire["data"]["servers"],
        "coverage": {"paths": [], "issues": []},
    }
    closed = []

    class Attached:
        def wait(self):
            raise KeyboardInterrupt

    @contextmanager
    def connection(*args):
        try:
            yield Attached(), "http://127.0.0.1:12345/science/login?next=%2Fscience%2F"
        finally:
            closed.append(True)

    with (
        patch("jupyhop.cli.discover", return_value=report),
        patch("jupyhop.cli.open_connection", connection),
        patch("webbrowser.open", return_value=available) as browser,
    ):
        assert (
            main(["open", "workstation", "--json", *(["--no-browser"] if no_browser else [])])
            == 130
        )
    output = capsys.readouterr()
    opened = json.loads(output.out)
    assert opened["authentication"] == "jupyter-login"
    assert "token=" not in opened["url"]
    assert closed == [True]
    if no_browser:
        browser.assert_not_called()
    else:
        browser.assert_called_once_with(opened["url"], new=2)
        if not available:
            assert "Browser unavailable" in output.err


def test_another_process_owner_cannot_be_verified(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(remote.os, "stat", lambda path: SimpleNamespace(st_uid=os.getuid() + 1))
    with pytest.raises(remote.Unsupported):
        remote.process_identity(123)


@pytest.mark.parametrize(
    "address,inode,accepted",
    [("0100007F", "99", True), ("00000000", "99", False), ("0100007F", "98", False)],
)
def test_kernel_socket_ownership_and_loopback_are_both_required(
    monkeypatch, address, inode, accepted
):
    from contextlib import contextmanager
    from types import SimpleNamespace

    @contextmanager
    def descriptors(path):
        yield iter([SimpleNamespace(path="fixture-descriptor")])

    def table(path, limit):
        if path.endswith("tcp6"):
            raise FileNotFoundError
        return f"header\n 0: {address}:22B8 00000000:0000 0A 0:0 00:0 0 1000 0 {inode}\n".encode()

    monkeypatch.setattr(remote.os, "scandir", descriptors)
    monkeypatch.setattr(remote.os, "readlink", lambda path: "socket:[99]")
    monkeypatch.setattr(remote, "_small", table)
    if accepted:
        assert remote.listener_inode(123, 8888) == "99"
    else:
        with pytest.raises(remote.Unsupported):
            remote.listener_inode(123, 8888)
