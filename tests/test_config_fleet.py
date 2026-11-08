import io
import json
import os
from unittest.mock import patch

import pytest

from jupyhop.cli import main
from jupyhop.config import Config, load_config, parse_config
from jupyhop.errors import SelectionError, SSHError
from jupyhop.fleet import inventory, select_inventory
from jupyhop.ssh import SSHTransport

VALID = b"""version = 1
[profiles.research]
server_python = "/env with spaces/bin/python"
workdir = "~/project"
[hosts.workstation]
profile = "research"
remote_python = "/helper/bin/python"
runtime_dirs = ["~/extra-runtime"]
"""


def test_profile_and_discovery_defaults_remain_separate():
    config = parse_config(VALID)
    assert config.profile("workstation").server_python == "/env with spaces/bin/python"
    assert config.discovery_options("workstation", None, ["~/manual"]) == (
        ["/helper/bin/python"],
        ["~/extra-runtime", "~/manual"],
    )
    assert config.discovery_options("workstation", ["python3"], None)[0] == ["python3"]


@pytest.mark.parametrize(
    "raw",
    [
        b"version = 2",
        b"version = true",
        b"",
        b"[profiles.x]\nserver_python = 'python3'",
        b"version = 1\npassword = 'PRIVATE_SENTINEL'",
        b"version = 1\n[hosts.workstation]\nUser = 'PRIVATE_SENTINEL'",
        b"version = 1\n[hosts.workstation]\nprofile = 'missing'",
        b"version = 1\n[profiles.x]\nserver_python = 'conda activate research'",
        b"version = 1\n[profiles.x]\nserver_python = 'python3'\nworkdir = '~other/project'",
        b"version = 1\n[hosts.workstation]\nruntime_dirs = '/runtime'",
        b"version = 1\n[hosts.workstation]\nruntime_dirs = [4]",
        b"version = 1\n[hosts.workstation]\nremote_python = 4",
        b"version=1\nversion=1",
        b"version = 'PRIVATE_SENTINEL",
        b"x" * 65537,
    ],
)
def test_invalid_config_is_rejected_without_echoing_values(raw):
    with pytest.raises(ValueError) as error:
        parse_config(raw)
    assert "PRIVATE_SENTINEL" not in str(error.value)


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo", "shared"])
def test_unsafe_config_files_are_refused(tmp_path, kind):
    path = tmp_path / "config.toml"
    if kind == "fifo":
        os.mkfifo(path, 0o600)
    else:
        path.write_bytes(VALID)
        path.chmod(0o644)
        if kind == "symlink":
            original = path.with_name("target")
            path.rename(original)
            path.symlink_to(original)
        elif kind == "hardlink":
            os.link(path, path.with_name("duplicate"))
        else:
            path.chmod(0o666)
    with pytest.raises(ValueError):
        load_config(path)


def test_optional_xdg_file_and_explicit_missing_file_policy(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert load_config() == Config()
    with pytest.raises(ValueError, match="does not exist"):
        load_config(tmp_path / "missing")
    path = tmp_path / "jupyhop/config.toml"
    path.parent.mkdir()
    path.write_bytes(VALID)
    path.chmod(0o644)
    assert "workstation" in load_config().hosts


@pytest.mark.parametrize(
    "overrides,python,workdir",
    [
        ([], "/env with spaces/bin/python", "~/project"),
        (["--server-python", "python3", "--workdir", "~/override"], "python3", "~/override"),
    ],
)
def test_cli_profile_precedence_without_shell_activation(tmp_path, overrides, python, workdir):
    path = tmp_path / "config.toml"
    path.write_bytes(VALID)
    path.chmod(0o600)
    report = {"id": "a" * 32, "state": "ready", "error": None}
    with (
        patch("jupyhop.cli.password_input", return_value="fixture-password"),
        patch("jupyhop.cli.start", return_value=report) as launch,
    ):
        assert (
            main(["start", "workstation", "--config", str(path), "--no-open", "--json", *overrides])
            == 0
        )
    assert launch.call_args.kwargs["server_python"] == python
    assert launch.call_args.kwargs["workdir"] == workdir
    assert launch.call_args.kwargs["helper_python"] == "/helper/bin/python"


def test_bad_config_fails_before_any_ssh(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("version = 2")
    path.chmod(0o600)
    with patch.object(SSHTransport, "run") as run, pytest.raises(SystemExit):
        main(["list", "workstation", "--config", str(path)])
    run.assert_not_called()


def test_fleet_keeps_healthy_results_and_per_route_errors():
    report = {"host": "first", "servers": [{"id": "a" * 32, "state": "ready"}]}
    with patch("jupyhop.fleet.discover", side_effect=[report, SSHError("route unavailable")]):
        result = inventory(Config(), ["first", "second"])
    assert result["version"] == 1 and result["complete"] is False
    assert result["hosts"][0]["report"] == report
    assert result["hosts"][1]["error"] == {"code": 3, "message": "route unavailable"}


def test_fleet_selection_includes_host_and_never_guesses():
    candidates = {
        "hosts": [
            {
                "ok": True,
                "report": {
                    "host": host,
                    "servers": [{"id": "a" * 32, "origin": "managed", "state": "ready"}],
                },
            }
            for host in ("first", "second")
        ]
    }
    with pytest.raises(SelectionError, match="Multiple"):
        select_inventory(candidates, interactive=False)
    with patch("sys.stdin", io.StringIO("2\n")):
        assert select_inventory(candidates, interactive=True)[0]["host"] == "second"


def test_list_json_reports_partial_failure_with_exit_14(capsys):
    data = {
        "version": 1,
        "complete": False,
        "hosts": [
            {"host": "first", "ok": True, "report": {"servers": []}, "error": None},
            {
                "host": "second",
                "ok": False,
                "report": None,
                "error": {"code": 3, "message": "route unavailable"},
            },
        ],
    }
    with patch("jupyhop.cli.inventory", return_value=data):
        assert main(["list", "first", "second", "--json"]) == 14
    captured = capsys.readouterr()
    assert json.loads(captured.out) == data
    assert "second" in captured.err
