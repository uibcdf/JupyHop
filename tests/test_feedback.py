import io
import json
import os
import stat
import subprocess
import sys
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from experiments.ssh_permissions_smoke import PROGRAM, _failure_reason
from jupyhop import _discovery_probe as probe
from jupyhop.cli import _servers, main
from jupyhop.ssh import ssh_failure


def test_native_permission_failure_reports_only_fixed_stages_or_exception_classes():
    assert (
        _failure_reason(
            b"PRIVATE_SENTINEL\nRuntimeError: Unsafe default configuration not refused\n"
        )
        == "Unsafe default configuration not refused"
    )
    assert _failure_reason(b"PRIVATE_SENTINEL\nNameError: private_variable\n") == "NameError"
    assert _failure_reason(b"RuntimeError: PRIVATE_SENTINEL") == "unknown fixture failure"


def test_permission_fixture_executes_actual_classifier_source_and_removes_its_file(
    tmp_path, capsys
):
    token = "0" * 12
    expected = "jht_" + token + "_a"
    fake_home = "/home/" + expected
    uid = os.getuid()
    if uid == 0:
        pytest.skip("The fixture intentionally refuses root")
    tmp_path.chmod(0o700)
    payload = {
        "uid": uid,
        "token": token,
        "errors": files("jupyhop").joinpath("errors.py").read_text(),
        "ssh": files("jupyhop").joinpath("ssh.py").read_text(),
    }
    real_open, real_stat = os.open, Path.stat

    def redirected_open(path, *args, **kwargs):
        return real_open(tmp_path if path == fake_home + "/.ssh" else path, *args, **kwargs)

    def redirected_stat(path, *args, **kwargs):
        if str(path) == fake_home + "/.ssh/config":
            path = tmp_path / "config"
        return real_stat(path, *args, **kwargs)

    def native_config(argv, **kwargs):
        assert argv == ["/usr/bin/ssh", "-G", "workstation"]
        unsafe = stat.S_IMODE((tmp_path / "config").stat().st_mode) == 0o664
        return subprocess.CompletedProcess(
            argv,
            255 if unsafe else 0,
            stdout=b"",
            stderr=(
                f"Bad owner or permissions on {fake_home}/.ssh/config\n".encode() if unsafe else b""
            ),
        )

    with (
        patch.dict(sys.modules),
        patch("sys.stdin", io.StringIO(json.dumps(payload))),
        patch("pwd.getpwuid", return_value=SimpleNamespace(pw_name=expected, pw_dir=fake_home)),
        patch("os.open", side_effect=redirected_open),
        patch.object(Path, "stat", redirected_stat),
        patch("subprocess.run", side_effect=native_config) as run,
    ):
        exec(compile(PROGRAM, "<fixture-driver>", "exec"), {})
        assert run.call_count == 3
    assert json.loads(capsys.readouterr().out)["feedback"] is True
    assert not (tmp_path / "config").exists()


@pytest.mark.parametrize("interactive", [False, True])
def test_config_permissions_are_actionable_without_echoing_raw_stderr(
    tmp_path, capsys, interactive
):
    (tmp_path / ".ssh").mkdir(mode=0o700)
    config = tmp_path / ".ssh/config"
    config.write_text("Host workstation\n    HostName workstation.example.org\n")
    config.chmod(0o664)
    diagnostic = f"Bad owner or permissions on {config}\nPRIVATE_SENTINEL\n"
    real_popen = subprocess.Popen

    def fixture_process(argv, **kwargs):
        return real_popen(
            [sys.executable, "-c", f"import sys; sys.stderr.write({diagnostic!r}); sys.exit(255)"],
            **kwargs,
        )

    with (
        patch("jupyhop.connection.terminal_available", return_value=interactive),
        patch("jupyhop.connection.subprocess.Popen", side_effect=fixture_process),
        patch("jupyhop.ssh.pwd.getpwuid", return_value=SimpleNamespace(pw_dir=str(tmp_path))),
    ):
        assert main(["doctor", "workstation"]) == 3
    output = capsys.readouterr()
    assert "group/other writes" in output.err and "chmod 600" in output.err
    assert "local ~/.ssh/config" in output.err and "PRIVATE_SENTINEL" not in output.err
    assert stat.S_IMODE(config.stat().st_mode) == 0o664


def test_wrong_owner_is_distinct_from_write_permissions(tmp_path):
    config = tmp_path / ".ssh/config"
    info = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_uid=os.getuid() + 1)
    with (
        patch("pathlib.Path.stat", return_value=info),
        patch("jupyhop.ssh.pwd.getpwuid", return_value=SimpleNamespace(pw_dir=str(tmp_path))),
    ):
        message = str(ssh_failure(f"Bad owner or permissions on {config}\n".encode()))
    assert "ownership" in message and "chmod alone cannot fix" in message
    assert "No permissions were changed" not in message or "chmod 600" not in message


def test_gateway_or_include_error_cannot_be_misidentified_as_local(tmp_path):
    local = tmp_path / "ssh_config"
    local.write_text("Host workstation\n")
    local.chmod(0o600)
    message = str(
        ssh_failure(b"Bad owner or permissions on /PRIVATE_SENTINEL/gateway-config", config=local)
    )
    assert "gateway/include" in message and "did not" in message
    assert "PRIVATE_SENTINEL" not in message and "rejected local" not in message


def test_connection_timeout_is_not_blended_with_terminal_auth_deadline():
    message = str(
        ssh_failure(
            b"Permission denied, please try again.\nConnection timed out during banner exchange PRIVATE_SENTINEL"
        )
    )
    assert "handshake timed out" in message and "--ssh-auth-timeout" in message
    assert (
        "--timeout" in message
        and "before retrying" in message
        and "PRIVATE_SENTINEL" not in message
    )


def test_permission_classification_survives_an_unavailable_local_passwd_entry():
    with patch("jupyhop.ssh.pwd.getpwuid", side_effect=KeyError("PRIVATE_SENTINEL")):
        message = str(ssh_failure(b"Bad owner or permissions on /example/config"))
    assert "PRIVATE_SENTINEL" not in message and "Inspect the exact file" in message


def test_a_full_diagnostic_sample_does_not_mark_later_scanned_directories_limited(tmp_path):
    earlier, later = tmp_path / "earlier", tmp_path / "later"
    earlier.mkdir(mode=0o700)
    later.mkdir(mode=0o700)
    for number in range(64):
        (earlier / f"jpserver-{number + 1}.json").touch(mode=0o600)
    (later / "jpserver-1000.json").touch(mode=0o600)

    def candidate(fd, name, path, scope):
        return {"id": name, "state": "ready" if path == str(later) else "stale"}

    report = {"identity": None, "paths": [], "servers": [], "issues": []}
    with (
        patch.object(
            probe, "_paths", return_value=[(str(earlier), "explicit"), (str(later), "explicit")]
        ),
        patch.object(probe, "_candidate", side_effect=candidate),
    ):
        probe.discover({"runtime_dirs": []}, report)
    assert [p["status"] for p in report["paths"]] == ["ok", "ok"]
    assert "sample_limit" in report["issues"] and "scan_limit" not in report["issues"]
    assert sum(s["state"] == "ready" for s in report["servers"]) == 1


def test_directory_entry_limit_is_reported_as_a_scan_bound(tmp_path):
    tmp_path.chmod(0o700)
    for number in range(513):
        (tmp_path / f"ordinary-{number}").touch()
    report = {"identity": None, "paths": [], "servers": [], "issues": []}
    with patch.object(probe, "_paths", return_value=[(str(tmp_path), "explicit")]):
        probe.discover({"runtime_dirs": []}, report)
    assert report["paths"][0]["status"] == "limited"
    assert "scan_limit" in report["issues"] and "sample_limit" not in report["issues"]


def test_default_human_discovery_summarizes_stale_rows_and_explicit_all_restores_them(capsys):
    stale = {
        "id": "a" * 24,
        "origin": "unmanaged",
        "state": "stale",
        "name": None,
        "port": 8888,
        "reason": "process_or_file_gone",
    }
    ready = dict(stale, id="b" * 24, state="ready", reason="verified")
    _servers({"servers": [stale, ready]}, all_candidates=False)
    output = capsys.readouterr()
    assert stale["id"] not in output.out and ready["id"] in output.out
    assert "partial sample" in output.err and "stale=1" in output.err
    _servers({"servers": [stale, ready]}, all_candidates=True)
    assert stale["id"] in capsys.readouterr().out


def test_native_permission_experiment_refuses_an_ordinary_account_before_any_file_access():
    with (
        patch("sys.stdin", io.StringIO(json.dumps({"token": "0" * 12, "uid": 1000}))),
        patch(
            "pwd.getpwuid",
            return_value=SimpleNamespace(pw_name="ordinary-user", pw_dir="/example/home"),
        ),
        patch("os.getuid", return_value=1000),
        patch("os.open") as opened,
    ):
        with pytest.raises(RuntimeError, match="generated fixture account"):
            exec(compile(PROGRAM, "<fixture>", "exec"), {})
        opened.assert_not_called()
