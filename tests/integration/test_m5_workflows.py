import getpass
import json
import os
import selectors
import signal
import socket
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path

import pytest
import requests

from experiments.lab import SSHLab
from experiments.m0_spike import execute
from experiments.managed_fixture import ManagedFixture
from jupyhop.config import Config, load_config
from jupyhop.discovery import discover, select_server
from jupyhop.fleet import inventory
from jupyhop.lifecycle import lifecycle, require_lifecycle_ok
from jupyhop.managed import start
from jupyhop.opening import open_connection
from jupyhop.ssh import SSHTransport

pytestmark = pytest.mark.integration


def fleet_config(root, first, second):
    path = root / "fleet-ssh"
    known = root / "fleet-known"
    known.write_bytes(
        (first.root / "known_hosts").read_bytes() + (second.root / "known_hosts").read_bytes()
    )
    path.write_text(f"""Host workstation-a
    HostName 127.0.0.1
    Port {first.ports[1]}
    IdentityFile {first.key}
    ProxyJump gateway-a
Host gateway-a
    HostName 127.0.0.1
    Port {first.ports[0]}
    IdentityFile {first.key}
Host workstation-b
    HostName 127.0.0.1
    Port {second.ports[1]}
    IdentityFile {second.key}
Host *
    User {getpass.getuser()}
    IdentitiesOnly yes
    UserKnownHostsFile {known}
    GlobalKnownHostsFile /dev/null
    StrictHostKeyChecking yes
    BatchMode yes
""")
    return path


def cleanup(lab):
    for path in (lab.home / "state/jupyhop").glob("hosts/*/sessions/*/record.json"):
        fixture = ManagedFixture(lab)
        fixture.record = json.loads(path.read_text())
        fixture.sid = fixture.record["id"]
        fixture.url = f"http://127.0.0.1:{fixture.record['port']}{fixture.record['base_url']}"
        fixture.close()


def login(base):
    client = requests.Session()
    client.trust_env = False
    client.get(base + "login", timeout=3)
    client.post(
        base + "login",
        data={"_xsrf": client.cookies.get("_xsrf"), "password": "fixture-password"},
        timeout=3,
    )
    client.headers["X-XSRFToken"] = client.cookies.get("_xsrf") or ""
    return client


def test_two_hosts_profile_launch_science_reconnect_and_archive(tmp_path):
    with SSHLab() as first, SSHLab() as second:
        ssh = fleet_config(tmp_path, first, second)
        project_a = first.home / "science α ; $(touch forbidden)"
        project_a.mkdir()
        (first.home / "project-link").symlink_to(project_a, target_is_directory=True)
        project_b = second.home / "science β"
        project_b.mkdir()
        environment = second.root / "separate-venv"
        subprocess.run(
            [sys.executable, "-m", "venv", "--system-site-packages", str(environment)], check=True
        )
        config = tmp_path / "config.toml"
        config.write_text(f"""version = 1
[profiles.first]
server_python = {json.dumps(sys.executable)}
workdir = "project-link"
[profiles.second]
server_python = {json.dumps(str(environment / "bin/python"))}
workdir = "~/science β"
[hosts.workstation-a]
profile = "first"
[hosts.workstation-b]
profile = "second"
""")
        config.chmod(0o600)
        reports = {}
        try:
            for host in ("workstation-a", "workstation-b"):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "jupyhop",
                        "start",
                        host,
                        "--config",
                        str(config),
                        "--ssh-config",
                        str(ssh),
                        "--password-stdin",
                        "--no-open",
                        "--json",
                        "--timeout",
                        "40",
                        "--name",
                        "research",
                    ],
                    input=b"fixture-password\n",
                    capture_output=True,
                    timeout=45,
                )
                assert result.returncode == 0, (
                    "Profile CLI start failed (raw secret-bearing output suppressed)"
                )
                reports[host] = json.loads(result.stdout)
                record = json.loads(Path(reports[host]["record_path"]).read_text())
                assert record["workdir"] == str(project_a if host == "workstation-a" else project_b)
                assert record["server_python"] == (
                    sys.executable if host == "workstation-a" else str(environment / "bin/python")
                )
            assert not (project_a / "forbidden").exists()
            listed = inventory(load_config(config), ssh_config=ssh)
            assert all(item["ok"] for item in listed["hosts"])
            assert len(listed["hosts"]) == 2
            kernels = {}
            ports = []
            with ExitStack() as stack:
                for index, entry in enumerate(listed["hosts"]):
                    host = entry["host"]
                    transport = SSHTransport(host, config=ssh)
                    server = select_server(entry["report"], reports[host]["id"], interactive=False)
                    tunnel, _ = stack.enter_context(
                        open_connection(transport, entry["report"], server)
                    )
                    ports.append(tunnel.local_port)
                    base = f"http://127.0.0.1:{tunnel.local_port}{server['base_url']}"
                    client = stack.enter_context(login(base))
                    response = client.post(
                        base + "api/kernels", json={"name": "python3"}, timeout=15
                    )
                    assert response.status_code == 201
                    kernel = response.json()["id"]
                    cookie = "; ".join(f"{c.name}={c.value}" for c in client.cookies)
                    assert execute(
                        base, "", kernel, f"marker = {40 + index}; print(marker)", cookie=cookie
                    ).strip() == str(40 + index)
                    kernels[host] = (kernel, 40 + index)
                assert len(set(ports)) == 2
            for host, (kernel, marker) in kernels.items():
                transport = SSHTransport(host, config=ssh)
                report = discover(transport)
                server = select_server(report, reports[host]["id"], interactive=False)
                with open_connection(transport, report, server) as (tunnel, _):
                    base = f"http://127.0.0.1:{tunnel.local_port}{server['base_url']}"
                    with login(base) as client:
                        cookie = "; ".join(f"{c.name}={c.value}" for c in client.cookies)
                        assert execute(
                            base, "", kernel, "print(marker)", cookie=cookie
                        ).strip() == str(marker)
                stopped = lifecycle(transport, "stop", reports[host]["id"])
                require_lifecycle_ok(stopped)
                retired = lifecycle(transport, "archive", reports[host]["id"])
                require_lifecycle_ok(retired)
                assert retired["archived"]["id"] == reports[host]["id"]
        finally:
            cleanup(first)
            cleanup(second)


def test_archive_refuses_live_then_preserves_evidence_and_releases_name(ssh_lab):
    fixture = ManagedFixture(ssh_lab, name="retire-and-reuse")
    try:
        fixture.__enter__()
        record = fixture.record_path.read_bytes()
        refused = lifecycle(fixture.transport, "archive", fixture.sid)
        assert refused["error"] == "session_active" and fixture.record_path.read_bytes() == record
        require_lifecycle_ok(lifecycle(fixture.transport, "stop", fixture.sid))
        stopped_record = fixture.record_path.read_bytes()
        result = lifecycle(fixture.transport, "archive", fixture.sid)
        require_lifecycle_ok(result)
        archived = fixture.record_path.parents[2] / "archive" / fixture.sid
        assert (archived / "record.json").read_bytes() == stopped_record
        assert (archived / "settings.json").stat().st_mode & 0o777 == 0o600
        assert (
            lifecycle(fixture.transport, "archive", fixture.sid)["archived"] == result["archived"]
        )
        with ManagedFixture(ssh_lab, name="retire-and-reuse") as replacement:
            assert replacement.sid != fixture.sid
    finally:
        fixture.close()


def test_no_host_cli_selection_and_partial_route_failure(ssh_lab, tmp_path):
    with ManagedFixture(ssh_lab, name="fleet-open") as fixture:
        config = tmp_path / "config.toml"
        config.write_text("version = 1\n[hosts.destination]\n")
        config.chmod(0o600)
        command = [
            sys.executable,
            "-m",
            "jupyhop",
            "open",
            "--config",
            str(config),
            "--ssh-config",
            str(ssh_lab.config),
            "--no-browser",
            "--json",
        ]
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True
        )
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                assert selector.select(25)
            report = json.loads(process.stdout.readline())
            assert report["id"] == fixture.sid and report["origin"] == "managed"
            process.send_signal(signal.SIGINT)
            process.communicate(timeout=10)
            assert process.returncode == 130
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=5)
        with socket.socket() as unavailable:
            # Reserve without listening, so no real service can occupy the port.
            unavailable.bind(("127.0.0.1", 0))
            unused = tmp_path / "unreachable"
            unused.write_text(
                f"Host missing\n    HostName 127.0.0.1\n    Port {unavailable.getsockname()[1]}\n"
            )
            data = inventory(Config(), ["missing"], ssh_config=unused, timeout=2)
            assert data["hosts"][0]["ok"] is False
            assert data["hosts"][0]["error"]["code"] == 3
        assert requests.get(fixture.url + "api", timeout=3).status_code == 200


def test_changed_ssh_route_and_duplicate_aliases_keep_one_remote_identity(ssh_lab, tmp_path):
    with ManagedFixture(ssh_lab, name="mobile-route") as fixture:
        ssh = tmp_path / "mobile-ssh"
        common = f"""Host mobile same-machine
    HostName 127.0.0.1
    Port {ssh_lab.ports[1]}
Host gateway
    HostName 127.0.0.1
    Port {ssh_lab.ports[0]}
Host *
    User {getpass.getuser()}
    IdentityFile {ssh_lab.key}
    IdentitiesOnly yes
    UserKnownHostsFile {ssh_lab.root}/known_hosts
    GlobalKnownHostsFile /dev/null
    StrictHostKeyChecking yes
    BatchMode yes
"""
        ssh.write_text(common)
        transport = SSHTransport("mobile", config=ssh)
        original = discover(transport)
        server = select_server(original, fixture.sid, interactive=False)
        with open_connection(transport, original, server) as (direct, _):
            # OpenSSH rereads the same file; JupyHop has no route/cache heuristics.
            ssh.write_text(common + "\nHost mobile\n    ProxyJump gateway\n")
            routed = discover(transport)
            selected = select_server(routed, fixture.sid, interactive=False)
            assert selected["pid"] == server["pid"]
            with open_connection(transport, routed, selected) as (jumped, _):
                assert direct.local_port != jumped.local_port
                assert (
                    requests.get(
                        f"http://127.0.0.1:{jumped.local_port}{server['base_url']}api", timeout=3
                    ).status_code
                    == 200
                )
            assert (
                requests.get(
                    f"http://127.0.0.1:{direct.local_port}{server['base_url']}api", timeout=3
                ).status_code
                == 200
            )
        routes = inventory(Config(), ["mobile", "same-machine"], ssh_config=ssh)
        assert all(
            any(s["id"] == fixture.sid for s in r["report"]["servers"]) for r in routes["hosts"]
        )
        conflict = start(
            SSHTransport("same-machine", config=ssh),
            server_python=sys.executable,
            name="mobile-route",
            password="fixture-password",
        )
        assert conflict["error"] == "name_conflict"
