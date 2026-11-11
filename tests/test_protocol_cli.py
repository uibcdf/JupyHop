import copy
import json
from unittest.mock import patch

import pytest

from jupyhop.cli import main
from jupyhop.doctor import diagnose
from jupyhop.errors import PrerequisiteError, ProtocolError, SSHError
from jupyhop.protocol import parse_doctor
from jupyhop.ssh import CommandResult, SSHTransport


@pytest.fixture
def envelope():
    return {
        "protocol": {"major": 1, "minor": 0},
        "operation": "doctor",
        "data": {
            "identity": {"uid": 1000, "user": "researcher"},
            "python": {"version": "3.14.10", "executable": "/env/bin/python", "supported": True},
            "jupyter_server": {"version": "2.21.1"},
            "jupyter_core": {"version": "5.9.1"},
            "runtime_dirs": [
                {
                    "path": "/home/researcher/runtime",
                    "source": "selected-python",
                    "status": "missing",
                }
            ],
            "coverage": "selected-interpreter-only",
            "process_managers": {"systemd_user": "unavailable", "tmux": True},
        },
    }


def result(envelope, code=0, stderr=b""):
    return CommandResult(code, json.dumps(envelope).encode(), stderr)


def test_minor_compatibility_and_secret_field_allowlist(envelope):
    envelope["protocol"]["minor"] = 20
    envelope["token"] = "PRIVATE_SENTINEL"
    envelope["data"]["identity"]["cookie"] = "PRIVATE_SENTINEL"
    parsed = parse_doctor(json.dumps(envelope).encode())
    assert parsed["protocol"]["minor"] == 20
    assert "PRIVATE_SENTINEL" not in json.dumps(parsed)


def test_major_mismatch(envelope):
    envelope["protocol"]["major"] = 2
    with pytest.raises(ProtocolError, match="Incompatible"):
        parse_doctor(json.dumps(envelope).encode())


def test_duplicate_protocol_fields_are_rejected(envelope):
    raw = json.dumps(envelope).replace('"major": 1', '"major": 99, "major": 1').encode()
    with pytest.raises(ProtocolError, match="Malformed"):
        parse_doctor(raw)


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"[]",
        b"null",
        b"{}",
        b"banner\n{}",
        b"{} trailing",
        b"\xff",
        b"[" * 12000,
        b"x" * 65537,
    ],
)
def test_malformed_bounded_protocol(raw):
    with pytest.raises(ProtocolError):
        parse_doctor(raw)


@pytest.mark.parametrize(
    "section,key,value",
    [
        ("identity", "uid", True),
        ("identity", "user", "bad\x1b[0m"),
        ("identity", "user", "bad\u009b"),
        ("identity", "user", "bad\ud800"),
        ("python", "supported", "yes"),
        ("python", "version", "x" * 4097),
        ("process_managers", "systemd_user", "other"),
    ],
)
def test_wrong_field_types_and_terminal_controls(envelope, section, key, value):
    envelope["data"][section][key] = value
    with pytest.raises(ProtocolError):
        parse_doctor(json.dumps(envelope).encode())


def test_json_cli_missing_dependencies_and_no_secret_output(envelope, capsys):
    envelope["data"]["jupyter_server"]["version"] = None
    envelope["data"]["token"] = "PRIVATE_SENTINEL"
    with patch.object(SSHTransport, "run", return_value=result(envelope)):
        assert main(["doctor", "workstation", "--json"]) == 4
    output = capsys.readouterr()
    parsed = json.loads(output.out)
    assert not parsed["ok"]
    assert parsed["missing"] == ["jupyter_server"]
    assert "--remote-python" in output.err
    assert "PRIVATE_SENTINEL" not in output.out + output.err


def test_human_cli_success_with_partial_coverage(envelope, capsys):
    with patch.object(SSHTransport, "run", return_value=result(envelope)):
        assert main(["doctor", "workstation"]) == 0
    output = capsys.readouterr()
    assert "no server discovery" in output.out
    assert output.err == ""


@pytest.mark.parametrize(
    "code,exception", [(127, PrerequisiteError), (1, PrerequisiteError), (255, SSHError)]
)
def test_remote_exit_classification(envelope, code, exception):
    with patch.object(
        SSHTransport, "run", return_value=result(envelope, code=code, stderr=b"PRIVATE_SENTINEL")
    ):
        with pytest.raises(exception) as exc:
            diagnose(SSHTransport("workstation"))
    assert "PRIVATE_SENTINEL" not in str(exc.value)


def test_remote_python_path_policy_and_safe_source_transport(envelope):
    with pytest.raises(ValueError):
        diagnose(SSHTransport("workstation"), "~/bin/python")
    with patch.object(SSHTransport, "run", return_value=result(envelope)) as run:
        diagnose(SSHTransport("workstation"), "/remote env/α/python")
    assert run.call_args.args == (["/remote env/α/python", "-I", "-B", "-"],)
    assert b"def probe" in run.call_args.kwargs["stdin"]


@pytest.mark.parametrize(
    "argv",
    [
        ["start", "workstation", "--auth", "token", "--password-stdin"],
        ["start", "workstation", "--no-open", "--login", "auto"],
        ["open", "workstation", "--json", "--login", "auto", "--no-browser"],
        ["doctor", "workstation", "--report", "--verbose"],
        ["doctor", "-oProxyCommand=id"],
        ["doctor", "workstation", "--timeout", "nan"],
    ],
)
def test_invalid_cli_and_unimplemented_commands(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2
    assert capsys.readouterr().err


def test_error_stdout_empty(envelope, capsys):
    broken = copy.deepcopy(envelope)
    broken["protocol"]["major"] = 99
    with patch.object(SSHTransport, "run", return_value=result(broken)):
        assert main(["doctor", "workstation", "--json"]) == 5
    output = capsys.readouterr()
    assert output.out == ""
    assert "Incompatible" in output.err


def test_interrupt_is_actionable(capsys):
    with patch.object(SSHTransport, "run", side_effect=KeyboardInterrupt):
        assert main(["doctor", "workstation"]) == 130
    assert "not modified" in capsys.readouterr().err
