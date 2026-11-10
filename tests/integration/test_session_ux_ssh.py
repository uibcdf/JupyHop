import json
import os
import pty
import select
import signal
import subprocess
import sys
import time
from importlib.resources import files
from pathlib import Path

import pytest

from experiments.lab import SSHLab
from experiments.m0_spike import execute
from experiments.managed_fixture import ManagedFixture
from jupyhop.lifecycle import lifecycle, require_lifecycle_ok
from jupyhop.managed import start
from jupyhop.session_inventory import inspect_sessions, summary
from jupyhop.ssh import SSHTransport

pytestmark = pytest.mark.integration


def test_full_registry_refuses_without_creating_record_then_archive_releases_capacity():
    with SSHLab() as lab:
        program = (
            files("jupyhop").joinpath("_managed_remote.py").read_bytes()
            + b"""
with Registry(create=True) as registry, registry.lock():
    for index in range(128):
        sid=f"{index:032x}"
        os.mkdir(sid,0o700,dir_fd=registry.sessions)
        runtime=os.path.join(registry.root,'sessions',sid,'runtime')
        record={'schema':SCHEMA,'id':sid,'owner_uid':os.getuid(),'name':f'retired-{index}',
            'state':'failed','manager':'tmux','runtime':runtime,'workdir':os.path.expanduser('~'),
            'server_python':sys.executable,'socket':os.path.join(registry.root,'missing.sock'),
            'base_url':'/jupyhop/'+sid+'/','boot_id':boot_id(),'pid':None,'port':None,
            'process_start':None,'socket_inode':None,'runner_sha256':hashlib.sha256(b'pass').hexdigest(),
            'error':'launch_failed'}
        with registry.session(sid) as descriptor:
            _write(descriptor,'launch.py',b'pass')
            _save(descriptor,'record.json',record)
"""
        )
        transport = SSHTransport("destination", config=lab.config, timeout=40)
        prepared = transport.run(["python3", "-I", "-B", "-"], stdin=program)
        assert prepared.returncode == 0
        before = {str(p): p.read_bytes() for p in lab.home.rglob("record.json")}
        try:
            refused = start(
                transport,
                server_python=sys.executable,
                name="quota-new",
                password="fixture-password",
                session_id="f" * 32,
            )
            assert refused["error"] == "registry_full" and refused["record_path"] is None
            assert {str(p): p.read_bytes() for p in lab.home.rglob("record.json")} == before
            assert summary(inspect_sessions(transport))["unarchived"] == 128
            require_lifecycle_ok(lifecycle(transport, "archive", "0" * 32))
            assert summary(inspect_sessions(transport))["unarchived"] == 127
            with ManagedFixture(lab, name="quota-new"):
                assert summary(inspect_sessions(transport))["ready"] == 1
                assert summary(inspect_sessions(transport))["unarchived"] == 128
        finally:
            # A regressed refusal must not leak a fixture's possible launcher.
            for path in lab.home.rglob("record.json"):
                if path.parent.name == "f" * 32:
                    fixture = ManagedFixture(lab)
                    fixture.sid = "f" * 32
                    fixture.record = json.loads(path.read_text())
                    if fixture.record.get("port"):
                        fixture.url = (
                            f"http://127.0.0.1:{fixture.record['port']}{fixture.record['base_url']}"
                        )
                    fixture.close()


def test_optional_diagnostic_api_runs_in_a_live_kernel_without_ssh_or_scientific_state_export():
    with SSHLab() as lab, ManagedFixture(lab) as fixture, fixture.client() as client:
        response = client.post(fixture.url + "api/kernels", json={"name": "python3"}, timeout=15)
        assert response.status_code == 201
        kernel = response.json()["id"]
        cookie = "; ".join(f"{item.name}={item.value}" for item in client.cookies)
        source = str(Path(__file__).resolve().parents[2] / "src")
        code = f"""import sys,json
sys.path.insert(0,{source!r})
from unittest.mock import patch
from jupyhop.diagnostics import kernel_report
scientific_marker='PRIVATE_SENTINEL'
with patch('jupyhop.ssh.SSHTransport.run',side_effect=AssertionError('Unexpected SSH')):
    result=kernel_report()
assert scientific_marker=='PRIVATE_SENTINEL'
print(json.dumps(result))
"""
        report = json.loads(execute(fixture.url, "", kernel, code, cookie=cookie))
        assert report["context"] == "notebook-kernel" and report["report_version"] == 1
        assert report["packages"]["ipykernel"] is not None
        assert "PRIVATE_SENTINEL" not in json.dumps(report) and "executable" not in report


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


@pytest.mark.parametrize("termination", ["interrupt", "terminate"])
def test_actual_management_terminal_returns_after_interrupt_or_exits_on_termination(termination):
    with SSHLab() as lab, ManagedFixture(lab, name="analysis") as fixture:
        pid, terminal = pty.fork()
        if pid == 0:
            environment = dict(
                os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src")
            )
            os.execve(
                sys.executable,
                [
                    sys.executable,
                    "-m",
                    "jupyhop",
                    "manage",
                    "destination",
                    "--ssh-config",
                    str(lab.config),
                    "--no-browser",
                    "--timeout",
                    "40",
                ],
                environment,
            )
        transcript = bytearray()
        phase = 0
        reaped = False
        try:
            deadline = time.monotonic() + 40
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
                if phase == 0 and b"Select an action number" in transcript:
                    os.write(terminal, b"1\n")
                    phase = 1
                elif phase == 1 and b"Select a session number" in transcript:
                    os.write(terminal, b"1\n")
                    phase = 2
                elif phase == 2 and b"Tunnel attached." in transcript:
                    if termination == "interrupt":
                        os.write(terminal, b"\x03")
                    else:
                        os.kill(pid, signal.SIGTERM)
                    phase = 3
                elif phase == 3 and transcript.count(b"Select an action number") >= 2:
                    os.write(terminal, b"6\n")
                    phase = 4
            else:
                pytest.fail("Management terminal did not complete within its deadline")
            _, status = os.waitpid(pid, 0)
            reaped = True
            assert os.waitstatus_to_exitcode(status) == (0 if termination == "interrupt" else 130)
            assert phase == (4 if termination == "interrupt" else 3)
            assert fixture.record_path.exists()
            with fixture.client() as client:
                assert client.get(fixture.url + "api/status", timeout=3).status_code == 200
        finally:
            if not reaped:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                os.waitpid(pid, 0)
            os.close(terminal)
