import io
import json
from unittest.mock import patch

import pytest

from jupyhop.cli import _parser, main
from jupyhop.discovery import select_server
from jupyhop.errors import LifecycleError, SelectionError
from jupyhop.selection import resolve_name

SID = "a" * 32


@pytest.fixture
def snapshot():
    return {
        "version": 1,
        "host": "workstation",
        "identity": {"uid": 1000, "user": "researcher", "scope": "b" * 24},
        "sessions": [{"id": SID, "name": "analysis", "state": "ready", "reason": "verified"}],
        "complete": True,
        "error": None,
        "history_error": None,
        "history": {"entries": [], "offset": 0, "next_offset": None, "complete": True},
    }


def lifecycle_reply(operation, *, state="stopped", error=None):
    return {
        "host": "workstation",
        "identity": {},
        "error": error,
        "servers": []
        if operation == "archive"
        else [{"id": SID, "name": "analysis", "state": state, "reason": "managed_" + state}],
        **(
            {"archived": {"id": SID, "path": "/example/archive/" + SID}}
            if operation == "archive"
            else {}
        ),
    }


def test_interactive_single_candidate_is_a_visible_named_choice(capsys):
    server = {"id": SID, "name": "analysis", "state": "ready", "origin": "managed"}
    with patch("sys.stdin", io.StringIO("1\n")):
        assert select_server({"servers": [server]}, None, interactive=True) is server
    assert "analysis" in capsys.readouterr().err
    with patch("sys.stdin", io.StringIO("")):
        with pytest.raises(SelectionError):
            select_server({"servers": [server]}, None, interactive=True)


def test_explicit_name_or_uuid_bypasses_choice_and_hex_names_are_unambiguous():
    server = {"id": SID, "name": "c" * 32, "state": "ready", "origin": "managed"}
    with patch("sys.stdin.readline", side_effect=AssertionError("Unexpected prompt")):
        assert select_server({"servers": [server]}, SID, interactive=True) is server
        assert select_server({"servers": [server]}, None, name="c" * 32, interactive=True) is server
    with pytest.raises(SelectionError):
        resolve_name([server, dict(server, id="d" * 32)], "c" * 32)
    with pytest.raises(SelectionError):
        resolve_name([dict(server, origin="unmanaged")], "c" * 32)


def test_id_and_name_are_mutually_exclusive_in_cli_before_ssh():
    with pytest.raises(SystemExit):
        _parser().parse_args(["open", "workstation", SID, "--name", "analysis"])
    assert _parser().parse_args(["resume", "workstation", "--name", "analysis"]).command == "resume"


@pytest.mark.parametrize("operation", ["stop", "archive"])
@pytest.mark.parametrize("selector", [[], ["--name", "analysis"]])
def test_automation_cannot_guess_a_lifecycle_target(operation, selector):
    with (
        patch("sys.stdin.isatty", return_value=False),
        patch("jupyhop.controls.inspect_sessions") as inspect,
        patch("jupyhop.controls.lifecycle") as mutate,
    ):
        assert main([operation, "workstation", *selector, "--yes"]) == 11
        inspect.assert_not_called()
        mutate.assert_not_called()


def test_interactive_stop_selects_pins_confirms_and_archives(snapshot, capsys):
    calls = []

    def mutate(transport, operation, identifier, **kwargs):
        calls.append((operation, identifier))
        return lifecycle_reply(operation)

    with (
        patch("sys.stdin", io.StringIO("1\nstop\n")),
        patch("sys.stdin.isatty", return_value=True),
        patch("jupyhop.controls.inspect_sessions", return_value=snapshot),
        patch("jupyhop.controls.lifecycle", side_effect=mutate),
    ):
        assert main(["stop", "workstation"]) == 0
    output = capsys.readouterr()
    assert calls == [("stop", SID), ("archive", SID)]
    assert "Stop and archive" in output.err and "all its kernels" in output.err
    assert "Archived" in output.out


def test_name_reuse_during_confirmation_cannot_retarget_the_uuid(snapshot):
    class Reused(io.StringIO):
        def readline(self, *args):
            snapshot["sessions"][0]["id"] = "c" * 32
            return "stop\n"

    with (
        patch("sys.stdin", Reused()),
        patch("sys.stdin.isatty", return_value=True),
        patch("jupyhop.controls.inspect_sessions", return_value=snapshot),
        patch(
            "jupyhop.controls.lifecycle", return_value=lifecycle_reply("stop", error="not_managed")
        ) as mutate,
    ):
        assert main(["stop", "workstation", "--name", "analysis"]) == 11
    assert mutate.call_count == 1
    assert mutate.call_args.args[2] == SID


def test_declining_or_eof_has_no_lifecycle_effect(snapshot):
    for text in ("", "1\nno\n"):
        with (
            patch("sys.stdin", io.StringIO(text)),
            patch("sys.stdin.isatty", return_value=True),
            patch("jupyhop.controls.inspect_sessions", return_value=snapshot),
            patch("jupyhop.controls.lifecycle") as mutate,
        ):
            assert main(["stop", "workstation"]) in {7, 11}
            mutate.assert_not_called()


def test_stop_only_scripts_keep_the_original_json_shape(capsys):
    with patch("jupyhop.controls.lifecycle", return_value=lifecycle_reply("stop")) as mutate:
        assert main(["stop", "workstation", SID, "--yes", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["servers"][0]["state"] == "stopped" and "stop" not in result
    mutate.assert_called_once()


def test_interactive_keep_record_is_stop_only():
    with (
        patch("sys.stdin", io.StringIO("stop\n")),
        patch("sys.stdin.isatty", return_value=True),
        patch("jupyhop.controls.lifecycle", return_value=lifecycle_reply("stop")) as mutate,
    ):
        assert main(["stop", "workstation", SID, "--keep-record"]) == 0
    assert mutate.call_count == 1 and mutate.call_args.args[1] == "stop"


@pytest.mark.parametrize("failed_phase", ["stop", "archive", None])
def test_explicit_script_completion_is_one_json_document_with_separate_phase_outcomes(
    failed_phase, capsys
):
    calls = []

    def mutate(transport, operation, identifier, **kwargs):
        calls.append(operation)
        if operation == failed_phase:
            raise LifecycleError("Fixture transport outcome unknown")
        return lifecycle_reply(operation)

    with patch("jupyhop.controls.lifecycle", side_effect=mutate):
        code = main(["stop", "workstation", SID, "--yes", "--archive", "--json"])
    output = capsys.readouterr()
    if failed_phase == "stop":
        assert code == 13 and calls == ["stop"]
    else:
        assert code == (13 if failed_phase else 0)
        result = json.loads(output.out)
        assert result["version"] == 1 and result["stop"]["servers"][0]["state"] == "stopped"
        assert calls == ["stop", "archive"]
        if failed_phase:
            assert "was stopped" in output.err and "same UUID" in output.err


def test_pending_stop_does_not_archive(capsys):
    with patch(
        "jupyhop.controls.lifecycle",
        return_value=lifecycle_reply("stop", state="stopping", error="stop_pending"),
    ) as mutate:
        assert main(["stop", "workstation", SID, "--yes", "--archive", "--json"]) == 13
    assert mutate.call_count == 1
    assert json.loads(capsys.readouterr().out)["archive"] is None


def test_status_counts_history_and_legacy_json_remain_distinct(snapshot, capsys):
    snapshot["sessions"][0].update(state="stopped", reason="managed_stopped")
    snapshot["history"]["entries"] = [{"id": "c" * 32, "name": "earlier", "record_state": "ready"}]
    with (
        patch("jupyhop.controls.inspect_sessions", return_value=snapshot),
        patch("jupyhop.controls.lifecycle", return_value=lifecycle_reply("status")) as legacy,
    ):
        assert main(["status", "workstation"]) == 0
        human = capsys.readouterr().out
        assert "stopped awaiting archive=1" in human and "archived=1" in human
        legacy.assert_not_called()
        assert main(["status", "workstation", "--history", "--json"]) == 0
        assert json.loads(capsys.readouterr().out)["summary"]["archived"] == 1
        assert main(["status", "workstation", "--json"]) == 0
        assert "servers" in json.loads(capsys.readouterr().out)
        legacy.assert_called_once()


def test_manage_rejects_headless_and_returns_from_its_owned_tunnel(snapshot, capsys):
    with (
        patch("sys.stdin.isatty", return_value=False),
        patch("jupyhop.cli.inspect_sessions") as inspect,
    ):
        assert main(["manage", "workstation"]) == 7
        inspect.assert_not_called()
    candidate = dict(snapshot["sessions"][0], origin="managed")
    report = {
        "identity": snapshot["identity"],
        "servers": [candidate],
        "coverage": {"paths": [], "issues": []},
    }
    with (
        patch("sys.stdin", io.StringIO("1\n1\n6\n")),
        patch("sys.stdin.isatty", return_value=True),
        patch("jupyhop.cli.inspect_sessions", return_value=snapshot),
        patch("jupyhop.cli.discover", return_value=report),
        patch("jupyhop.cli._open", side_effect=KeyboardInterrupt) as opened,
    ):
        assert main(["manage", "workstation"]) == 0
    assert opened.call_count == 1
    assert "Returning to management" in capsys.readouterr().err
