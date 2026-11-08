import json
import os
import selectors
import signal
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import requests

from experiments.lab import SSHLab
from experiments.m0_spike import execute
from experiments.managed_fixture import ManagedFixture
from jupyhop.discovery import discover, select_server
from jupyhop.managed import start
from jupyhop.opening import open_connection
from jupyhop.ssh import SSHTransport

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def launch_lab():
    with SSHLab() as lab:
        yield lab


@pytest.mark.parametrize("host", ["direct", "destination"])
def test_managed_start_password_kernel_and_owned_registry(launch_lab, host):
    project = launch_lab.home / ("project α ; $(touch forbidden)-" + host)
    project.mkdir()
    with ManagedFixture(launch_lab, name="analysis-" + host, workdir=str(project)) as fixture:
        record = fixture.record
        assert record["workdir"] == str(project)
        assert Path(f"/proc/{record['pid']}/cwd").resolve() == project
        assert not (project / "forbidden").exists()
        assert fixture.record_path.stat().st_mode & 0o777 == 0o600
        settings = fixture.record_path.with_name("settings.json")
        assert settings.stat().st_mode & 0o777 == 0o600
        assert all(
            fixture.password not in p.read_text()
            for p in (settings, fixture.record_path, fixture.record_path.with_name("launch.py"))
        )
        transport = SSHTransport(host, config=launch_lab.config, timeout=40)
        report = discover(transport)
        server = select_server(report, fixture.sid, interactive=False)
        assert server["origin"] == "managed" and len(server["observed_id"]) == 24
        assert fixture.password not in json.dumps(report)
        with open_connection(transport, report, server) as (tunnel, url):
            assert "token=" not in url
            base = f"http://127.0.0.1:{tunnel.local_port}{server['base_url']}"
            assert requests.get(base + "api/status", timeout=3).status_code == 403
            with fixture.client(base, password="invalid-password") as denied:
                assert denied.get(base + "api/status", timeout=3).status_code == 403
            with fixture.client(base) as client:
                assert client.get(base + "api/status", timeout=3).status_code == 200
                response = client.post(base + "api/kernels", json={"name": "python3"}, timeout=15)
                assert response.status_code == 201
                kernel = response.json()["id"]
                try:
                    cookie = "; ".join(f"{c.name}={c.value}" for c in client.cookies)
                    assert execute(base, "", kernel, "print(6 * 7)", cookie=cookie).strip() == "42"
                finally:
                    client.delete(base + "api/kernels/" + kernel, timeout=10)


def test_two_managed_sessions_have_distinct_ids_ports_and_names(launch_lab):
    with (
        ManagedFixture(launch_lab, name="first") as first,
        ManagedFixture(launch_lab, name="second") as second,
    ):
        assert first.sid != second.sid
        assert first.record["port"] != second.record["port"]
        report = discover(first.transport)
        for fixture in (first, second):
            assert select_server(report, fixture.sid, interactive=False)["origin"] == "managed"


def test_concurrent_same_name_reserves_only_one_session(launch_lab):
    fixtures = [ManagedFixture(launch_lab, name="concurrent") for _ in range(2)]
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            reports = list(pool.map(lambda fixture: fixture.launch(), fixtures))
        assert sum(report["state"] == "ready" for report in reports) == 1
        assert sum(report["error"] == "name_conflict" for report in reports) == 1
    finally:
        for fixture in fixtures:
            fixture.close()


def test_missing_directory_and_python_do_not_create_session_records(launch_lab):
    before = set((launch_lab.home / "state").rglob("record.json"))
    for parameters, expected in [
        ({"workdir": str(launch_lab.root / "missing-project")}, "invalid_workdir"),
        ({"server_python": str(launch_lab.root / "missing-python")}, "missing_python"),
    ]:
        result = start(
            SSHTransport("direct", config=launch_lab.config, timeout=30),
            server_python=parameters.get("server_python", sys.executable),
            workdir=parameters.get("workdir", "~"),
            password="fixture-password",
        )
        assert result["state"] == "failed" and result["error"] == expected
    assert set((launch_lab.home / "state").rglob("record.json")) == before


def test_missing_server_dependencies_fail_before_creating_a_record(launch_lab):
    # A real executable with deliberately incompatible server environment.
    python = launch_lab.root / "empty-python"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(python)], check=True)
    result = start(
        SSHTransport("direct", config=launch_lab.config),
        server_python=str(python / "bin/python"),
        password="fixture-password",
    )
    assert result["error"] == "server_prerequisites"
    assert result["record_path"] is None


def test_stdlib_helper_launches_and_opens_jupyter_in_a_separate_environment(launch_lab):
    helper = launch_lab.root / "stdlib-start-helper"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(helper)], check=True)
    python = str(helper / "bin/python")
    with ManagedFixture(launch_lab, name="separate-helper", helper_python=python) as fixture:
        report = discover(fixture.transport, [python])
        server = select_server(report, fixture.sid, interactive=False)
        with open_connection(fixture.transport, report, server, [python]) as (tunnel, _):
            base = f"http://127.0.0.1:{tunnel.local_port}{server['base_url']}"
            with fixture.client(base) as client:
                assert client.get(base + "api/status", timeout=3).status_code == 200


def test_failed_initialization_keeps_recoverable_record(launch_lab):
    import shlex

    project = launch_lab.root / "vanishing-project"
    project.mkdir()
    wrapper = launch_lab.root / "initialization-failure-python"
    remover = "import os,sys; os.rmdir(sys.argv[1])"
    wrapper.write_text(
        "#!/bin/sh\nif [ \"$3\" != '-c' ]; then "
        + shlex.join([sys.executable, "-I", "-c", remover, str(project)])
        + "; fi\nexec "
        + shlex.quote(sys.executable)
        + ' "$@"\n'
    )
    wrapper.chmod(0o700)
    fixture = ManagedFixture(
        launch_lab, name="failed-start", workdir=str(project), server_python=str(wrapper)
    )
    try:
        result = fixture.launch()
        assert result["state"] == "failed"
        assert result["error"] == "server_initialization_failed"
        assert fixture.record["state"] == "failed"
        report = discover(fixture.transport)
        assert any(s["id"] == fixture.sid and s["state"] == "failed" for s in report["servers"])
    finally:
        fixture.close()


def test_discovery_will_not_adopt_managed_record_with_wrong_process_identity(launch_lab):
    with ManagedFixture(launch_lab, name="identity-guard") as fixture:
        original = fixture.record_path.read_bytes()
        corrupted = dict(fixture.record, process_start="1")
        fixture.record_path.write_text(json.dumps(corrupted))
        try:
            report = discover(fixture.transport)
            assert not any(
                s["id"] == fixture.sid and s["state"] == "ready" for s in report["servers"]
            )
            assert any(
                s["origin"] == "unmanaged" and s["pid"] == fixture.record["pid"]
                for s in report["servers"]
            )
            assert requests.get(fixture.url + "api", timeout=3).status_code == 200
        finally:
            fixture.record_path.write_bytes(original)


def test_newer_registry_is_not_modified_and_running_server_survives(launch_lab):
    with ManagedFixture(launch_lab, name="version-guard") as fixture:
        root = fixture.record_path.parents[2]
        header = root / "registry.json"
        original = header.read_bytes()
        incompatible = json.dumps(
            {"producer": "jupyhop", "schema": {"major": 2, "minor": 0}}
        ).encode()
        before = set((root / "sessions").iterdir())
        header.write_bytes(incompatible)
        try:
            result = start(
                fixture.transport,
                server_python=sys.executable,
                name="incompatible-start",
                password=fixture.password,
            )
            assert result["error"] == "incompatible_registry"
            assert header.read_bytes() == incompatible
            assert set((root / "sessions").iterdir()) == before
            assert requests.get(fixture.url + "api", timeout=3).status_code == 200
        finally:
            header.write_bytes(original)


def test_cli_start_password_stdin_and_signal_keep_remote_process_alive(launch_lab):
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    command = [
        sys.executable,
        "-m",
        "jupyhop",
        "start",
        "destination",
        "--ssh-config",
        str(launch_lab.config),
        "--password-stdin",
        "--json",
        "--no-browser",
        "--timeout",
        "40",
        "--name",
        "cli-session",
    ]
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        start_new_session=True,
    )
    snapshot = None
    try:
        process.stdin.write(b"fixture-password\n")
        process.stdin.close()
        process.stdin = None
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            assert selector.select(45), "CLI start readiness timed out"
        connection = json.loads(process.stdout.readline())
        sid = connection["id"]
        path = next((launch_lab.home / "state/jupyhop").glob(f"hosts/*/sessions/{sid}/record.json"))
        snapshot = json.loads(path.read_text())
        assert connection["origin"] == "managed"
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 130
        assert b"fixture-password" not in stdout + stderr
        os.kill(snapshot["pid"], 0)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=5)
        if snapshot is not None:
            subprocess.run(
                ["tmux", "-S", snapshot["socket"], "kill-server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
