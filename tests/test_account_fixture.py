import os
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from experiments import m5_accounts as fixture


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
