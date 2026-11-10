import json
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

import pytest

from jupyhop.cli import main
from jupyhop.diagnostics import client_report, kernel_report, support_report
from jupyhop.errors import ProtocolError, SSHError
from jupyhop.ssh import CommandResult, SSHTransport


@pytest.fixture
def diagnosis():
    return {
        "host": "PRIVATE_SENTINEL",
        "ok": True,
        "data": {
            "identity": {"user": "PRIVATE_SENTINEL", "uid": 1000},
            "python": {
                "version": "3.14.10+PRIVATE_SENTINEL",
                "executable": "/PRIVATE_SENTINEL/python",
                "supported": True,
            },
            "jupyter_server": {"version": "2.21.1+PRIVATE_SENTINEL"},
            "jupyter_core": {"version": "5.9.1"},
            "runtime_dirs": [{"status": "accessible", "path": "/PRIVATE_SENTINEL/runtime"}],
            "process_managers": {"systemd_user": "available", "tmux": True},
            "token": "PRIVATE_SENTINEL",
        },
    }


def test_support_report_is_allowlisted_and_distinguishes_selected_interpreter_from_kernel(
    diagnosis,
):
    with (
        patch("jupyhop.diagnostics.client_report", return_value={}),
        patch("jupyhop.diagnostics.diagnose", return_value=diagnosis),
    ):
        report, code = support_report(SSHTransport("workstation"), "python3")
    text = json.dumps(report)
    assert code == 0 and report["report_version"] == 1
    assert "PRIVATE_SENTINEL" not in text and "executable" not in text
    assert report["remote"]["python"] == "3.14.10"
    assert "no kernel executed" in report["remote"]["coverage"]


@pytest.mark.parametrize(
    "failure,code,stage", [(SSHError, 3, "ssh"), (ProtocolError, 5, "remote-protocol")]
)
def test_failed_remote_probe_retains_local_diagnostics_without_raw_errors(failure, code, stage):
    with (
        patch("jupyhop.diagnostics.client_report", return_value={"python": "3.14.10"}),
        patch("jupyhop.diagnostics.diagnose", side_effect=failure("PRIVATE_SENTINEL")),
    ):
        report, result = support_report(SSHTransport("workstation"), "python3")
    assert result == code and report["outcome"]["stage"] == stage
    assert report["client"]["python"] == "3.14.10" and report["remote"] is None
    assert "PRIVATE_SENTINEL" not in json.dumps(report)


def test_notebook_report_never_initiates_ssh_and_does_not_require_jupyter():
    with (
        patch("jupyhop.diagnostics.version", side_effect=PackageNotFoundError),
        patch.object(SSHTransport, "run") as remote,
    ):
        result = kernel_report()
    assert result["context"] == "notebook-kernel" and result["report_version"] == 1
    assert all(value is None for value in result["packages"].values())
    assert not {"hostname", "cwd", "pid", "environ", "executable"} & result.keys()
    remote.assert_not_called()


def test_openssh_version_probe_is_bounded_and_does_not_reflect_its_banner():
    with patch(
        "jupyhop.diagnostics._run_bounded",
        return_value=CommandResult(0, b"", b"OpenSSH_10.2p1 PRIVATE_SENTINEL"),
    ) as bounded:
        result = client_report()
    bounded.assert_called_once_with(["ssh", "-V"], b"", 2)
    assert result["openssh"] == "10.2" and "PRIVATE_SENTINEL" not in json.dumps(result)
    with patch("jupyhop.diagnostics._run_bounded", side_effect=SSHError("PRIVATE_SENTINEL")):
        assert client_report()["openssh"] is None


def test_doctor_report_prints_one_shareable_json_and_retains_prerequisite_exit(diagnosis, capsys):
    diagnosis["ok"] = False
    diagnosis["data"]["jupyter_server"]["version"] = None
    with (
        patch("jupyhop.diagnostics.client_report", return_value={}),
        patch("jupyhop.diagnostics.diagnose", return_value=diagnosis),
    ):
        assert main(["doctor", "workstation", "--report", "--json"]) == 4
    result = json.loads(capsys.readouterr().out)
    assert result["outcome"]["code"] == 4 and result["remote"]["jupyter_server"] is None
    assert "PRIVATE_SENTINEL" not in json.dumps(result)
