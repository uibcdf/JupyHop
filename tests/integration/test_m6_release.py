"""Release gates use only disposable loopback SSH/Jupyter fixtures."""

import base64
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
import websocket
from jupyter_client.session import Session

from experiments.jupyter_fixture import JupyterFixture
from jupyhop.discovery import discover, select_server
from jupyhop.opening import open_connection
from jupyhop.ssh import SSHTransport

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("interrupt", [signal.SIGTERM, signal.SIGHUP])
def test_signal_during_probe_cleans_owned_ssh_before_open(ssh_lab, tmp_path, interrupt):
    marker = tmp_path / "probe-started"
    helper = tmp_path / "waiting-python"
    helper.write_text(f"#!/bin/sh\ntouch '{marker}'\nexec /bin/sleep 30\n")
    helper.chmod(0o700)
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "jupyhop",
            "doctor",
            "destination",
            "--ssh-config",
            str(ssh_lab.config),
            "--remote-python",
            str(helper),
        ],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 10
        while not marker.exists():
            assert process.poll() is None
            assert time.monotonic() < deadline
            time.sleep(0.05)
        children = Path(f"/proc/{process.pid}/task/{process.pid}/children")
        owned = [int(value) for value in children.read_text().split()]
        assert owned
        process.send_signal(interrupt)
        out, err = process.communicate(timeout=10)
        assert process.returncode == 130 and not out and b"interrupted" in err
        for pid in owned:
            assert not Path(f"/proc/{pid}").exists()
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=5)


def test_large_contents_and_sustained_websocket_through_jump(ssh_lab):
    with JupyterFixture(ssh_lab.root / "release-data", runtime=ssh_lab.runtime) as fixture:
        transport = SSHTransport("destination", config=ssh_lab.config)
        report = discover(transport)
        selected = select_server(report, None, interactive=False)
        with open_connection(transport, report, selected) as (tunnel, _):
            base = f"http://127.0.0.1:{tunnel.local_port}/science/"
            with fixture.client() as client:
                payload = bytes(range(256)) * 32768  # 8 MiB; never scientific data.
                encoded = base64.b64encode(payload).decode("ascii")
                result = client.put(
                    base + "api/contents/large.bin",
                    json={
                        "type": "file",
                        "format": "base64",
                        "content": encoded,
                    },
                    timeout=20,
                )
                assert result.status_code == 201
                result = client.get(base + "api/contents/large.bin?format=base64", timeout=20)
                result.raise_for_status()
                restored = base64.b64decode(result.json()["content"])
                assert hashlib.sha256(restored).digest() == hashlib.sha256(payload).digest()
                result = client.post(base + "api/kernels", json={"name": "python3"}, timeout=20)
                result.raise_for_status()
                kernel = result.json()["id"]
                try:
                    url = (
                        base.replace("http:", "ws:")
                        + f"api/kernels/{kernel}/channels?session_id={uuid.uuid4()}"
                    )
                    with closing(
                        websocket.create_connection(
                            url,
                            header=["Authorization: token " + fixture.info["token"]],
                            origin=base.rstrip("/"),
                            timeout=15,
                        )
                    ) as ws:
                        session = Session()
                        for index in range(64):
                            message = session.msg(
                                "execute_request",
                                {
                                    "code": f"import time; time.sleep(0.05); print('{index}:' + 'x'*65536)",
                                    "silent": False,
                                    "store_history": False,
                                    "user_expressions": {},
                                    "allow_stdin": False,
                                    "stop_on_error": True,
                                },
                            )
                            ws.send(json.dumps(message, default=lambda value: value.isoformat()))
                            output = []
                            while True:
                                response = json.loads(ws.recv())
                                if (
                                    response.get("parent_header", {}).get("msg_id")
                                    != message["header"]["msg_id"]
                                ):
                                    continue
                                assert response["msg_type"] != "error"
                                if response["msg_type"] == "stream":
                                    output.append(response["content"]["text"])
                                if (
                                    response["msg_type"] == "status"
                                    and response["content"]["execution_state"] == "idle"
                                ):
                                    break
                            assert "".join(output) == f"{index}:" + "x" * 65536 + "\n"
                finally:
                    client.delete(base + "api/kernels/" + kernel, timeout=10)
                assert client.delete(base + "api/contents/large.bin", timeout=5).status_code == 204
        assert fixture.process.poll() is None


def test_live_password_rotation_requires_fresh_authorized_login(ssh_lab):
    # A private fixture control file changes the live provider. No control API is
    # added to JupyHop or exposed over HTTP, and the scientific server is not used.
    control = ssh_lab.root / "rotated"
    source = f"""import sys
from pathlib import Path
from jupyter_server.serverapp import ServerApp
from jupyter_server.auth import passwd
from tornado.ioloop import PeriodicCallback
app = ServerApp.instance()
app.initialize(sys.argv[1:])
def rotate():
    if Path({str(control)!r}).exists():
        app.identity_provider.hashed_password = passwd('rotated-fixture-password')
        Path({str(control)!r}).unlink()
callback = PeriodicCallback(rotate, 100)
callback.start()
app.start()
"""
    native_popen = subprocess.Popen

    def launch(argv, **kwargs):
        if "jupyter_server" in argv and "-m" in argv:
            argv = [*argv[:3], "-c", source, argv[-1]]
        return native_popen(argv, **kwargs)

    with patch("experiments.jupyter_fixture.subprocess.Popen", side_effect=launch):
        with JupyterFixture(
            ssh_lab.root / "rotation", runtime=ssh_lab.runtime, password=True
        ) as fixture:
            transport = SSHTransport("destination", config=ssh_lab.config)
            report = discover(transport)
            server = select_server(report, None, interactive=False)
            original_pid = fixture.process.pid
            with open_connection(transport, report, server) as (tunnel, _):
                base = f"http://127.0.0.1:{tunnel.local_port}/science/"
                with fixture.client(base) as first:
                    assert first.get(base + "api/status", timeout=3).status_code == 200
                control.touch(mode=0o600)
                deadline = time.monotonic() + 5
                while control.exists():
                    assert time.monotonic() < deadline
                    time.sleep(0.05)
            # A new tunnel/client has neither a password cache nor a trusted old
            # cookie. Existing authorized cookies follow Jupyter's own policy.
            fresh = discover(transport)
            same = select_server(fresh, server["id"], interactive=False)
            assert same["pid"] == original_pid
            with open_connection(transport, fresh, same) as (tunnel, _):
                base = f"http://127.0.0.1:{tunnel.local_port}/science/"
                with fixture.client(base) as rejected:
                    assert rejected.get(base + "api/status", timeout=3).status_code == 403
                with requests.Session() as login:
                    login.trust_env = False
                    login.get(base + "login", timeout=3)
                    login.post(
                        base + "login",
                        data={
                            "_xsrf": login.cookies.get("_xsrf"),
                            "password": "rotated-fixture-password",
                        },
                        timeout=3,
                    )
                    assert login.get(base + "api/status", timeout=3).status_code == 200
            assert fixture.process.poll() is None
