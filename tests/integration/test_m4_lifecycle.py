import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import requests

from experiments.jupyter_fixture import JupyterFixture
from experiments.lab import SSHLab, stop
from experiments.m0_spike import execute
from experiments.m4_reconnect import independent_client, worker_client
from experiments.managed_fixture import ManagedFixture
from jupyhop._discovery_probe import process_identity
from jupyhop.discovery import discover, select_server
from jupyhop.lifecycle import lifecycle, require_lifecycle_ok
from jupyhop.opening import open_connection
from jupyhop.ssh import SSHTransport

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def lifecycle_lab():
    with SSHLab() as lab:
        yield lab


def gone(pid):
    try:
        process_identity(pid)
        return False
    except (FileNotFoundError, ProcessLookupError):
        return True


def until(condition, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.05)
    pytest.fail("Disposable lifecycle observation timed out")


def capture(fixture):
    paths = list(
        (fixture.lab.home / "state/jupyhop").glob(f"hosts/*/sessions/{fixture.sid}/record.json")
    )
    if not paths:
        return False
    fixture.record_path = paths[0]
    fixture.record = json.loads(paths[0].read_text())
    if fixture.record.get("port"):
        fixture.base = fixture.record["base_url"]
        fixture.url = f"http://127.0.0.1:{fixture.record['port']}{fixture.base}"
        return True
    return False


def test_independent_clients_preserve_notebook_kernel_memory_and_stop(lifecycle_lab):
    with ManagedFixture(lifecycle_lab, name="independent-clients") as fixture:
        a = independent_client(lifecycle_lab, "client-a", jump=True)
        b = independent_client(lifecycle_lab, "client-b", jump=False)
        assert a.read_text() != b.read_text()
        assert a.with_name("identity.pub").read_bytes() != b.with_name("identity.pub").read_bytes()
        first = worker_client(a, fixture.sid, fixture.password, create=True)
        second = worker_client(b, fixture.sid, fixture.password)
        assert first["session"] == second["session"]
        assert first["kernel"] == second["kernel"]
        assert first["pid"] == second["pid"] == fixture.record["pid"]
        assert second["output"] == "42 [42]"
        kernel_pid = int(first["output"])
        transport = SSHTransport("remote", config=b)
        result = lifecycle(transport, "stop", fixture.sid)
        require_lifecycle_ok(result)
        assert result["servers"][0]["state"] == "stopped"
        until(lambda: gone(kernel_pid))
        again = lifecycle(transport, "stop", fixture.sid)
        require_lifecycle_ok(again)
        assert again["servers"][0]["state"] == "stopped"
        assert any(
            s["id"] == fixture.sid and s["state"] == "stopped"
            for s in discover(transport)["servers"]
        )


def test_reboot_and_reused_process_identity_never_signal_a_live_server(lifecycle_lab):
    with ManagedFixture(lifecycle_lab, name="boot-and-pid") as fixture:
        original = fixture.record_path.read_bytes()
        try:
            for change in ({"boot_id": "previous-boot"}, {"process_start": "1"}):
                fixture.record_path.write_text(json.dumps(dict(fixture.record, **change)))
                report = lifecycle(fixture.transport, "status", fixture.sid)
                require_lifecycle_ok(report)
                assert report["servers"][0]["state"] == "stale"
                report = lifecycle(fixture.transport, "stop", fixture.sid)
                require_lifecycle_ok(report)
                assert report["servers"][0]["state"] == "stale"
                assert requests.get(fixture.url + "api", timeout=3).status_code == 200
        finally:
            fixture.record_path.write_bytes(original)


def test_two_owned_forwards_share_one_live_kernel_without_restarting(lifecycle_lab):
    with ManagedFixture(lifecycle_lab, name="parallel-forwards") as fixture:
        a = SSHTransport("destination", config=lifecycle_lab.config)
        b = SSHTransport("direct", config=lifecycle_lab.config)
        report = discover(a)
        server = select_server(report, fixture.sid, interactive=False)
        with open_connection(a, report, server) as (first, _):
            base_a = f"http://127.0.0.1:{first.local_port}{fixture.base}"
            with fixture.client(base_a) as client_a:
                kernel = client_a.post(
                    base_a + "api/kernels", json={"name": "python3"}, timeout=15
                ).json()["id"]
                cookie_a = "; ".join(f"{c.name}={c.value}" for c in client_a.cookies)
                assert (
                    execute(
                        base_a,
                        "",
                        kernel,
                        "parallel_marker = 42; print(parallel_marker)",
                        cookie=cookie_a,
                    ).strip()
                    == "42"
                )
                with open_connection(b, report, server) as (second, _):
                    assert first.local_port != second.local_port
                    base_b = f"http://127.0.0.1:{second.local_port}{fixture.base}"
                    with fixture.client(base_b) as client_b:
                        cookie_b = "; ".join(f"{c.name}={c.value}" for c in client_b.cookies)
                        assert (
                            execute(
                                base_b, "", kernel, "print(parallel_marker)", cookie=cookie_b
                            ).strip()
                            == "42"
                        )
                assert (
                    execute(base_a, "", kernel, "print(parallel_marker)", cookie=cookie_a).strip()
                    == "42"
                )


def test_unrelated_process_and_changed_socket_are_not_stopped(lifecycle_lab):
    with (
        ManagedFixture(lifecycle_lab, name="foreign-process") as fixture,
        subprocess.Popen(["/bin/sleep", "30"]) as unrelated,
    ):
        original = fixture.record_path.read_bytes()
        try:
            for change in (
                {"pid": unrelated.pid, "process_start": process_identity(unrelated.pid)},
                {"socket_inode": "1"},
            ):
                fixture.record_path.write_text(json.dumps(dict(fixture.record, **change)))
                report = lifecycle(fixture.transport, "stop", fixture.sid)
                assert report["error"] == "unverified_owner"
                assert unrelated.poll() is None
                assert requests.get(fixture.url + "api", timeout=3).status_code == 200
        finally:
            fixture.record_path.write_bytes(original)
            unrelated.terminate()
            unrelated.wait(timeout=5)


def test_only_selected_managed_server_is_stopped(lifecycle_lab):
    with (
        ManagedFixture(lifecycle_lab, name="selected-stop") as selected,
        ManagedFixture(lifecycle_lab, name="keep-running") as other,
        JupyterFixture(
            lifecycle_lab.root / "manual-stop-guard", runtime=lifecycle_lab.runtime
        ) as unmanaged,
    ):
        report = lifecycle(selected.transport, "stop", selected.sid)
        require_lifecycle_ok(report)
        assert report["servers"][0]["state"] == "stopped"
        assert requests.get(other.url + "api", timeout=3).status_code == 200
        assert requests.get(unmanaged.url + "api", timeout=3).status_code == 200


def test_concurrent_stops_are_safe_and_eventually_stopped(lifecycle_lab):
    with ManagedFixture(lifecycle_lab, name="concurrent-stop") as fixture:
        with ThreadPoolExecutor(max_workers=2) as pool:
            reports = list(
                pool.map(lambda _: lifecycle(fixture.transport, "stop", fixture.sid), range(2))
            )
        assert all(r["error"] in (None, "stop_pending") for r in reports)
        until(lambda: gone(fixture.record["pid"]))
        assert (
            lifecycle(fixture.transport, "status", fixture.sid)["servers"][0]["state"] == "stopped"
        )


def test_crashed_server_is_stale_and_is_never_automatically_restarted(lifecycle_lab):
    with ManagedFixture(lifecycle_lab, name="crash-observation") as fixture:
        os.kill(fixture.record["pid"], signal.SIGKILL)  # Only this newly created fixture PID.
        until(lambda: gone(fixture.record["pid"]))
        report = lifecycle(fixture.transport, "status", fixture.sid)
        require_lifecycle_ok(report)
        assert report["servers"][0]["state"] == "stale"
        assert lifecycle(fixture.transport, "stop", fixture.sid)["servers"][0]["state"] == "stale"


def test_status_and_stop_refuse_incompatible_registry_without_updates(lifecycle_lab):
    with ManagedFixture(lifecycle_lab, name="lifecycle-version") as fixture:
        header = fixture.record_path.parents[2] / "registry.json"
        original = header.read_bytes()
        incompatible = json.dumps(
            {"producer": "jupyhop", "schema": {"major": 1, "minor": 1}}
        ).encode()
        before = fixture.record_path.read_bytes()
        header.write_bytes(incompatible)
        try:
            for command in ("status", "stop"):
                result = lifecycle(fixture.transport, command, fixture.sid)
                assert result["error"] == "incompatible_registry"
                assert header.read_bytes() == incompatible
                assert fixture.record_path.read_bytes() == before
                assert requests.get(fixture.url + "api", timeout=3).status_code == 200
        finally:
            header.write_bytes(original)


def test_cli_status_and_confirmed_stop_do_not_expose_credentials(lifecycle_lab):
    with ManagedFixture(lifecycle_lab, name="cli-stop") as fixture:
        prefix = [sys.executable, "-m", "jupyhop"]
        arguments = [
            "destination",
            fixture.sid,
            "--ssh-config",
            str(lifecycle_lab.config),
            "--json",
        ]
        for operation, extra in (("status", []), ("stop", ["--yes"])):
            result = subprocess.run(
                prefix + [operation] + arguments + extra, capture_output=True, timeout=30
            )
            assert result.returncode == 0
            data = json.loads(result.stdout)
            assert data["servers"][0]["state"] == ("ready" if operation == "status" else "stopped")
            assert fixture.password.encode() not in result.stdout + result.stderr
            assert b"argon2:" not in result.stdout + result.stderr


def test_lost_start_and_stop_replies_are_reconciled_without_duplicate_launch(lifecycle_lab):
    fixture = ManagedFixture(lifecycle_lab, name="interrupted-rpc")
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    start_code = """import sys
from pathlib import Path
import jupyhop.managed as m
from jupyhop.ssh import SSHTransport
m.BOOTSTRAP=m.BOOTSTRAP.replace("n['start_main'](p['request'])", "f=n['_prepare']; n['_prepare']=lambda r:(f(r),__import__('time').sleep(30))[0]; n['start_main'](p['request'])")
m.start(SSHTransport('destination',config=Path(sys.argv[1]),timeout=60),server_python=sys.executable,password=sys.stdin.readline().strip(),session_id=sys.argv[2],name='interrupted-rpc')
"""
    stop_code = """import sys
from pathlib import Path
import jupyhop.lifecycle as m
from jupyhop.ssh import SSHTransport
m._BOOTSTRAP=m._BOOTSTRAP.replace("n['lifecycle_main'](p['request'])", "f=n['_stop']; n['_stop']=lambda *a:(f(*a),__import__('time').sleep(30))[0]; n['lifecycle_main'](p['request'])")
m.lifecycle(SSHTransport('destination',config=Path(sys.argv[1]),timeout=60),'stop',sys.argv[2])
"""
    clients = []
    try:
        for index, code in enumerate((start_code, stop_code)):
            process = subprocess.Popen(
                [sys.executable, "-c", code, str(lifecycle_lab.config), fixture.sid],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=environment,
            )
            clients.append(process)
            process.stdin.write((fixture.password + "\n").encode())
            process.stdin.close()
            if index == 0:
                until(lambda: capture(fixture), timeout=30)
                assert fixture.record["state"] == "starting"
            else:
                until(lambda: gone(fixture.record["pid"]))
            # KeyboardInterrupt runs SSHTransport's finally: close its private
            # SSH/ProxyJump group too, without receiving the delayed RPC reply.
            process.send_signal(signal.SIGINT)
            process.wait(timeout=5)
            report = lifecycle(fixture.transport, "status", fixture.sid)
            require_lifecycle_ok(report)
            assert report["servers"][0]["state"] == ("ready" if index == 0 else "stopped")
        record = json.loads(fixture.record_path.read_text())
        assert record["pid"] == fixture.record["pid"] and record["stop_requested"] is True
        assert lifecycle(fixture.transport, "stop", fixture.sid)["servers"][0]["state"] == "stopped"
    finally:
        for process in clients:
            stop(process)
        capture(fixture)
        fixture.close()
