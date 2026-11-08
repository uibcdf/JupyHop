import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

import pytest
import requests

from experiments.jupyter_fixture import JupyterFixture
from experiments.lab import SSHLab
from experiments.m0_spike import execute
from jupyhop._discovery_probe import endpoint
from jupyhop.discovery import discover, select_server
from jupyhop.errors import DiscoveryError, SelectionError, TunnelError
from jupyhop.opening import open_connection
from jupyhop.ssh import SSHTransport
from jupyhop.tunnel import Tunnel

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def manual_server(ssh_lab):
    with JupyterFixture(ssh_lab.root / "manual", runtime=ssh_lab.runtime) as server:
        yield server


@pytest.mark.parametrize("host", ["direct", "destination"])
def test_zero_config_discovery_and_open_existing_server(ssh_lab, manual_server, host):
    transport = SSHTransport(host, config=ssh_lab.config)
    report = discover(transport)
    server = select_server(report, None, interactive=False)
    assert server["pid"] == manual_server.process.pid
    assert server["state"] == "ready" and server["origin"] == "unmanaged"
    assert not report["coverage"]["complete"]
    with open_connection(transport, report, server) as (tunnel, url):
        assert urlsplit(url).hostname == "127.0.0.1"
        assert "token=" not in url
        assert urlsplit(url).path == "/science/login"
        base = f"http://127.0.0.1:{tunnel.local_port}/science/"
        assert requests.get(base + "api/status", timeout=3).status_code == 403
        assert (
            requests.get(
                base + "api/status", headers={"Authorization": "token invalid"}, timeout=3
            ).status_code
            == 403
        )
        # Ordinary Jupyter token login POST; token never travels in a URL.
        with requests.Session() as login:
            login.get(url, timeout=3)
            login.post(
                url,
                data={"_xsrf": login.cookies.get("_xsrf"), "password": manual_server.info["token"]},
                timeout=3,
            )
            assert login.get(base + "api/status", timeout=3).status_code == 200
        with manual_server.client() as client:
            result = client.post(base + "api/kernels", json={"name": "python3"}, timeout=15)
            assert result.status_code == 201
            kernel_id = result.json()["id"]
            try:
                observed = execute(base, manual_server.info["token"], kernel_id, "print(6 * 7)")
                assert observed.strip() == "42"
            finally:
                client.delete(base + "api/kernels/" + kernel_id, timeout=10)
    assert manual_server.process.poll() is None
    assert requests.get(manual_server.url + "api/", timeout=3).status_code == 200


def test_private_master_ignores_configured_forward_and_retries_collision(ssh_lab, manual_server):
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        port = occupied.getsockname()[1]
        config = ssh_lab.root / "static-forward.conf"
        config.write_text(
            f"Host *\n    LocalForward 127.0.0.1:{port} 127.0.0.1:{manual_server.port}\n"
            + ssh_lab.config.read_text()
        )
        from jupyhop.tunnel import _free_port

        alternative = _free_port()
        with patch("jupyhop.tunnel._free_port", side_effect=[port, alternative]):
            with Tunnel(SSHTransport("destination", config=config), manual_server.port) as tunnel:
                assert tunnel.local_port == alternative
                assert occupied.fileno() >= 0
                assert (
                    requests.get(
                        f"http://127.0.0.1:{alternative}/science/api/", timeout=3
                    ).status_code
                    == 200
                )


def test_concurrent_opens_have_independent_owned_tunnels(ssh_lab, manual_server):
    transport = SSHTransport("destination", config=ssh_lab.config)
    report = discover(transport)
    server = select_server(report, None, interactive=False)
    with open_connection(transport, report, server) as (first, _):
        with open_connection(transport, report, server) as (second, _):
            assert first.local_port != second.local_port
        assert (
            requests.get(f"http://127.0.0.1:{first.local_port}/science/api/", timeout=3).status_code
            == 200
        )


def test_multiple_servers_custom_paths_and_duplicate_runtime_metadata(ssh_lab, manual_server):
    with JupyterFixture(ssh_lab.root / "second") as second:
        report = discover(
            SSHTransport("destination", config=ssh_lab.config), runtime_dirs=[str(second.runtime)]
        )
        assert len([s for s in report["servers"] if s["state"] == "ready"]) == 2
        with pytest.raises(SelectionError, match="Multiple verified"):
            select_server(report, None, interactive=False)
        duplicate = second.runtime / manual_server.record.name
        duplicate.write_bytes(manual_server.record.read_bytes())
        duplicate.chmod(0o600)
        report = discover(
            SSHTransport("destination", config=ssh_lab.config), runtime_dirs=[str(second.runtime)]
        )
        candidates = [s for s in report["servers"] if s["state"] == "ready"]
        assert len(candidates) == 2
        assert (
            len(next(s for s in candidates if s["pid"] == manual_server.process.pid)["sources"])
            == 2
        )


def test_password_authentication_is_preserved(ssh_lab):
    with JupyterFixture(ssh_lab.root / "password", password=True) as fixture:
        transport = SSHTransport("destination", config=ssh_lab.config)
        report = discover(transport, runtime_dirs=[str(fixture.runtime)])
        server = next(s for s in report["servers"] if s["pid"] == fixture.process.pid)
        with open_connection(transport, report, server) as (tunnel, _):
            base = f"http://127.0.0.1:{tunnel.local_port}/science/"
            assert requests.get(base + "api/status", timeout=3).status_code == 403
            with fixture.client(base) as login:
                assert login.get(base + "api/status", timeout=3).status_code == 200


@pytest.mark.parametrize("address,auth", [("0.0.0.0", True), ("127.0.0.1", False)])
def test_unsafe_binding_or_unprotected_server_is_not_openable(ssh_lab, address, auth):
    # Never start even a disposable public Jupyter listener: test metadata lies
    # about a safe loopback server, and a deliberately auth-disabled fixture.
    with JupyterFixture(ssh_lab.root / f"unsupported-{auth}", auth=auth) as fixture:
        if address == "0.0.0.0":
            data = json.loads(fixture.record.read_text())
            data["hostname"] = address
            fixture.record.write_text(json.dumps(data))
        report = discover(
            SSHTransport("direct", config=ssh_lab.config), runtime_dirs=[str(fixture.runtime)]
        )
        server = next(s for s in report["servers"] if s["pid"] == fixture.process.pid)
        assert server["state"] == "unsupported"


def test_server_identity_change_refuses_open(ssh_lab, manual_server):
    transport = SSHTransport("direct", config=ssh_lab.config)
    report = discover(transport)
    server = dict(select_server(report, None, interactive=False), id="f" * 24)
    with pytest.raises(DiscoveryError, match="changed"):
        with open_connection(transport, report, server):
            pytest.fail("Unverified identity was opened")


@pytest.mark.parametrize("stop_signal", [signal.SIGINT, signal.SIGTERM, signal.SIGHUP])
def test_headless_cli_signal_closes_only_owned_tunnel(ssh_lab, manual_server, stop_signal):
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    command = [
        sys.executable,
        "-m",
        "jupyhop",
        "open",
        "destination",
        "--ssh-config",
        str(ssh_lab.config),
        "--no-browser",
        "--json",
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        start_new_session=True,
    )
    try:
        import selectors

        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            assert selector.select(20), "CLI readiness timed out"
        opened = json.loads(process.stdout.readline())
        port = urlsplit(opened["url"]).port
        process.send_signal(stop_signal)
        process.communicate(timeout=10)
        assert process.returncode == 130
        with pytest.raises(OSError):
            socket.create_connection(("127.0.0.1", port), timeout=0.2)
        assert manual_server.process.poll() is None
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=5)


def test_http_header_trickle_cannot_extend_absolute_deadline():
    done = threading.Event()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(3)

        def trickle():
            try:
                with listener.accept()[0] as channel:
                    channel.settimeout(1)
                    channel.recv(4096)
                    for chunk in (
                        b"HTTP/1.1 200 OK\r\n",
                        b"X-Test: ",
                        b"a",
                        b"b",
                        b"c",
                        b"d",
                        b"e",
                        b"f",
                    ):
                        channel.sendall(chunk)
                        if done.wait(0.4):
                            break
            except OSError:
                pass

        worker = threading.Thread(target=trickle, daemon=True)
        worker.start()
        started = time.monotonic()
        try:
            with pytest.raises(TimeoutError):
                endpoint(listener.getsockname()[1], "/")
            assert time.monotonic() - started < 3
        finally:
            done.set()
            worker.join(timeout=2)


def test_remote_connection_refusal_preserves_server(ssh_lab, manual_server):
    transport = SSHTransport("direct", config=ssh_lab.config)
    # Connection refusal is exercised against a reserved, non-listening local
    # port, never another server; the fixture Jupyter remains untouched.
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        with Tunnel(transport, reserved.getsockname()[1]) as tunnel:
            with pytest.raises(requests.RequestException):
                requests.get(f"http://127.0.0.1:{tunnel.local_port}/api/", timeout=2)
    assert manual_server.process.poll() is None


def test_ssh_policy_denies_forwarding_without_stopping_server(manual_server):
    with SSHLab(allow_target_forwarding=False) as lab:
        transport = SSHTransport("direct", config=lab.config)
        report = discover(transport, runtime_dirs=[str(manual_server.runtime)])
        server = select_server(report, None, interactive=False)
        with pytest.raises(TunnelError, match="forwarded Jupyter"):
            with open_connection(transport, report, server):
                pytest.fail("A denied SSH forward was opened")
    assert manual_server.process.poll() is None


def test_stdlib_helper_finds_jupyter_in_another_environment(ssh_lab, manual_server):
    environment = ssh_lab.root / "stdlib-helper"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(environment)], check=True)
    python = str(environment / "bin/python")
    transport = SSHTransport("destination", config=ssh_lab.config)
    report = discover(transport, [python])
    server = select_server(report, None, interactive=False)
    with open_connection(transport, report, server, [python]) as (tunnel, _):
        assert (
            requests.get(f"http://127.0.0.1:{tunnel.local_port}/science/api", timeout=3).status_code
            == 200
        )
