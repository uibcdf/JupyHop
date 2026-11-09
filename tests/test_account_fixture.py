import os
import re
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from experiments import m5_accounts as fixture


@pytest.mark.parametrize("missing", [True, False])
def test_fixture_password_never_changes_missing_or_replaced_account(tmp_path, missing):
    with (
        patch.object(
            fixture,
            "_account",
            return_value=None,
            side_effect=None if missing else RuntimeError("identity changed"),
        ),
        patch.object(fixture, "_run") as run,
        patch.object(fixture, "_write") as write,
        pytest.raises(RuntimeError),
    ):
        fixture._enable_fixture_password(
            tmp_path, {"name": "fixture"}, "a" * 12, (os.getuid(), os.getgid())
        )
    run.assert_not_called()
    write.assert_not_called()


def test_fixture_password_is_generated_private_and_never_a_command_argument(tmp_path):
    with (
        patch.object(fixture, "_account", return_value=object()),
        patch.object(fixture, "_run") as run,
    ):
        fixture._enable_fixture_password(
            tmp_path, {"name": "fixture"}, "a" * 12, (os.getuid(), os.getgid())
        )
    secret = (tmp_path / "ssh-password").read_bytes()
    assert re.fullmatch(rb"[A-Za-z0-9_-]{43}", secret)
    assert (tmp_path / "ssh-password").stat().st_mode & 0o777 == 0o600
    assert run.call_args.args == (["/usr/sbin/chpasswd"],)
    assert run.call_args.kwargs["stdin"] == b"fixture:" + secret + b"\n"
    assert secret.decode() not in repr(run.call_args.args)


def test_fixture_command_accepts_private_stdin_without_shell_or_argument_interpolation():
    payload = b"fixture:$(id); PRIVATE_SENTINEL\n"
    result = fixture._run(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"],
        stdin=payload,
    )
    assert result == payload


def test_prepare_only_creates_private_keys_and_bounded_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(fixture, "ROOT_BASE", tmp_path)
    root = fixture.prepare()
    try:
        assert root.stat().st_mode & 0o777 == 0o700
        for name in ("a", "b", "hostkey", "prepared.json"):
            assert (root / name).stat().st_mode & 0o777 == 0o600
        assert fixture._prepared(root)[2] == os.getuid()
        assert {p.name for p in root.iterdir()} == {
            "a",
            "a.pub",
            "b",
            "b.pub",
            "hostkey",
            "hostkey.pub",
            "prepared.json",
        }
    finally:
        shutil.rmtree(root)


def test_new_account_home_is_empty_private_and_owned(tmp_path):
    home = tmp_path / "home"
    account = SimpleNamespace(pw_dir=str(home), pw_uid=os.getuid(), pw_gid=os.getgid())
    assert fixture._new_home(account) == home
    assert not list(home.iterdir())
    assert home.stat().st_mode & 0o777 == 0o700
    assert home.stat().st_uid == os.getuid() and home.stat().st_gid == os.getgid()


@pytest.mark.parametrize("kind", ["directory", "symlink"])
def test_new_home_never_reuses_existing_paths(tmp_path, kind):
    target = tmp_path / "target"
    target.mkdir()
    sentinel = target / "sentinel"
    sentinel.write_text("UNCHANGED")
    home = target if kind == "directory" else tmp_path / "home"
    if kind == "symlink":
        home.symlink_to(target, target_is_directory=True)
    account = SimpleNamespace(pw_dir=str(home), pw_uid=os.getuid(), pw_gid=os.getgid())
    with pytest.raises(FileExistsError):
        fixture._new_home(account)
    assert sentinel.read_text() == "UNCHANGED"


def test_provision_refuses_existing_home_before_creating_accounts(tmp_path):
    token = "123456abcdef"
    root = tmp_path / (fixture.PREFIX + token)
    with (
        patch.object(fixture, "_privileged"),
        patch.object(fixture, "_prepared", return_value=(root, token, os.getuid(), os.getgid())),
        patch.object(fixture.pwd, "getpwnam", side_effect=KeyError),
        patch.object(fixture.grp, "getgrnam", side_effect=KeyError),
        patch.object(fixture.os.path, "lexists", return_value=True),
        patch.object(fixture, "_run") as run,
    ):
        with pytest.raises(RuntimeError, match="home already exists"):
            fixture.provision(root)
        run.assert_not_called()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/tmp",
        "/home/test",
        "/tmp/jupyhop-m5-accounts-other",
        "/tmp/jupyhop-m5-accounts-abcdef/../../home",
    ],
)
def test_actions_cannot_target_an_arbitrary_path(path):
    with pytest.raises(RuntimeError):
        fixture._root(path)


def test_privileged_actions_refuse_before_running_commands():
    with patch.object(os, "geteuid", return_value=1000), patch.object(fixture, "_run") as run:
        with pytest.raises(RuntimeError, match="sudo"):
            fixture.provision(Path("/tmp/jupyhop-m5-accounts-123456abcdef"))
        with pytest.raises(RuntimeError, match="sudo"):
            fixture.cleanup(Path("/tmp/jupyhop-m5-accounts-123456abcdef"))
        run.assert_not_called()


@pytest.mark.parametrize(
    "change",
    [{"pw_uid": 0}, {"pw_uid": 1002}, {"pw_dir": "/home/other"}, {"pw_gecos": "unrelated account"}],
)
def test_cleanup_rejects_changed_or_foreign_account_identity(change):
    token, name = "123456abcdef", "jht_123456abcdef_a"
    values = {"pw_uid": 1001, "pw_dir": "/home/" + name, "pw_gecos": "JupyHop M5 " + token}
    values.update(change)
    with patch.object(fixture.pwd, "getpwnam", return_value=SimpleNamespace(**values)):
        with pytest.raises(RuntimeError):
            fixture._account({"name": name, "uid": 1001}, token)


def test_fixture_signal_refuses_pid_identity_change_before_signalling():
    descriptor = os.open(os.devnull, os.O_RDONLY)
    with (
        patch.object(os, "pidfd_open", return_value=descriptor, create=True),
        patch.object(fixture, "_start", return_value="new"),
        patch.object(fixture.signal, "pidfd_send_signal", create=True) as send,
    ):
        with pytest.raises(RuntimeError, match="identity changed"):
            fixture._signal(os.getpid(), os.getuid(), fixture.signal.SIGTERM, "old")
        send.assert_not_called()


def test_prepared_symlink_cannot_supply_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(fixture, "ROOT_BASE", tmp_path)
    target = tmp_path / "outside"
    target.mkdir(mode=0o700)
    root = tmp_path / "jupyhop-m5-accounts-123456abcdef"
    root.symlink_to(target, target_is_directory=True)
    with pytest.raises(OSError):
        fixture._prepared(root)
