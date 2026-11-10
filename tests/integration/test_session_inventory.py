import json
import os
import pty
import select
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from experiments.lab import SSHLab
from experiments.managed_fixture import ManagedFixture
from jupyhop.lifecycle import lifecycle, require_lifecycle_ok
from jupyhop.session_inventory import inspect_sessions, summary
from jupyhop.ssh import SSHTransport

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("host", ["direct", "destination"])
def test_inventory_observes_live_stopped_and_archived_without_writing(host):
    with SSHLab() as lab, ManagedFixture(lab, name="analysis") as fixture:
        transport = SSHTransport(host, config=lab.config, timeout=40)
        before = fixture.record_path.read_bytes()
        launch = fixture.record_path.parent / "launch.py"
        runner = launch.read_bytes()
        report = inspect_sessions(transport)
        assert report["complete"] and report["error"] is None
        assert summary(report) == {
            "ready": 1,
            "stopped": 0,
            "review": 0,
            "unarchived": 1,
            "archived": 0,
            "archive_count_exact": True,
        }
        assert report["sessions"][0]["id"] == fixture.sid
        assert fixture.record_path.read_bytes() == before and launch.read_bytes() == runner
        stopped = lifecycle(transport, "stop", fixture.sid)
        require_lifecycle_ok(stopped)
        assert summary(inspect_sessions(transport))["stopped"] == 1
        archived = lifecycle(transport, "archive", fixture.sid)
        require_lifecycle_ok(archived)
        after = inspect_sessions(transport)
        assert summary(after)["unarchived"] == 0
        assert summary(after)["archived"] == 1
        assert after["history"]["entries"][0]["id"] == fixture.sid
        assert after["history"]["entries"][0]["name"] == "analysis"
        assert "password" not in str(after)


def terminal_stop(argv):
    pid, terminal = pty.fork()
    if pid == 0:
        environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
        os.execve(sys.executable, [sys.executable, "-m", "jupyhop", *argv], environment)
    transcript = bytearray()
    sent = reaped = False
    try:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if not select.select([terminal], [], [], 0.1)[0]:
                continue
            try:
                chunk = os.read(terminal, 4096)
            except OSError:
                break
            if not chunk:
                break
            transcript.extend(chunk)
            assert len(transcript) < 65536
            if b"Type stop to confirm:" in transcript and not sent:
                os.write(terminal, b"stop\n")
                sent = True
        else:
            pytest.fail("Disposable interactive lifecycle deadline exceeded")
        _, status = os.waitpid(pid, 0)
        reaped = True
        assert os.waitstatus_to_exitcode(status) == 0 and sent
        assert b"Stop and archive" in transcript and b"Archived" in transcript
    finally:
        if not reaped:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)
        os.close(terminal)


def test_named_open_interactive_completion_and_history_leave_other_server_untouched():
    with (
        SSHLab() as lab,
        ManagedFixture(lab, name="analysis") as first,
        ManagedFixture(lab, name="other") as second,
    ):
        common = ["--ssh-config", str(lab.config), "--timeout", "40", "--batch"]
        environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
        other_bytes = second.record_path.read_bytes()
        with subprocess.Popen(
            [
                sys.executable,
                "-m",
                "jupyhop",
                "open",
                "destination",
                "--name",
                "analysis",
                "--json",
                "--no-browser",
                *common,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            start_new_session=True,
        ) as opening:
            try:
                assert select.select([opening.stdout], [], [], 20)[0], (
                    "Named open did not return its connection"
                )
                connection = json.loads(opening.stdout.readline())
                assert connection["id"] == first.sid and connection["origin"] == "managed"
            finally:
                opening.send_signal(signal.SIGINT)
                opening.communicate(timeout=10)
            assert opening.returncode == 130
        terminal_stop(["stop", "destination", "--name", "analysis", *common])
        assert not first.record_path.exists()
        assert second.record_path.read_bytes() == other_bytes
        report = inspect_sessions(second.transport)
        assert report["sessions"][0]["id"] == second.sid and summary(report)["ready"] == 1
        assert report["history"]["entries"][0]["id"] == first.sid
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "jupyhop",
                "status",
                "destination",
                "--history",
                "--json",
                *common,
            ],
            capture_output=True,
            env=environment,
            timeout=20,
        )
        assert result.returncode == 0
        assert json.loads(result.stdout)["summary"]["archived"] == 1
        stopped = subprocess.run(
            [
                sys.executable,
                "-m",
                "jupyhop",
                "stop",
                "destination",
                second.sid,
                "--yes",
                "--json",
                *common,
            ],
            capture_output=True,
            env=environment,
            timeout=30,
        )
        assert (
            stopped.returncode == 0
            and json.loads(stopped.stdout)["servers"][0]["state"] == "stopped"
        )
        assert second.record_path.exists()  # Old scripts remain stop-only.
