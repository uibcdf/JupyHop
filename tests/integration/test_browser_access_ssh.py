"""Production managed browser-access checks over a disposable OpenSSH route."""

import json
import re

import pytest
import requests
import websocket

from experiments.managed_fixture import ManagedFixture
from jupyhop.auth import observe, verify_cookie
from jupyhop.errors import ProtocolError
from jupyhop.opening import open_connection

pytestmark = pytest.mark.integration


def test_selected_cookie_uses_private_token_and_protected_forward(ssh_lab):
    fixture = ManagedFixture(ssh_lab, name="token-access")
    fixture.parameters.update(auth_mode="token", password=None)
    with fixture:
        observation = observe(fixture.transport, "python3", 20, name="token-access")
        assert observation.mode == "token" and observation.cookie is None
        runtime = fixture.record_path.parent / "runtime" / f"jpserver-{fixture.record['pid']}.json"
        token = json.loads(runtime.read_text())["token"]
        assert re.fullmatch(r"[a-f0-9]{64}", token)
        assert runtime.stat().st_mode & 0o777 == 0o600
        assert runtime.parent.stat().st_mode & 0o777 == 0o700
        for file in ("settings.json", "record.json", "server.log", "launch.py"):
            assert token not in fixture.record_path.with_name(file).read_text()
        assert not list(runtime.parent.glob("*-open.html"))
        original = fixture.record_path.read_bytes()
        with open_connection(
            fixture.transport,
            fixture.report,
            observation.server,
            managed_python="python3",
            managed_mode="token",
        ) as (tunnel, url):

            class Recorded:
                def run(self, argv, *, stdin=b""):
                    response = tunnel.run(argv, stdin=stdin)
                    assert token.encode() not in response.stdout + response.stderr
                    return response

            def issue(observed_id):
                return observe(
                    Recorded(),
                    "python3",
                    20,
                    identifier=fixture.sid,
                    identity=observation.identity,
                    observed_id=observed_id,
                    local_port=tunnel.local_port,
                )

            with pytest.raises(ProtocolError, match="target_changed"):
                issue("a" * 24)
            runtime.chmod(0o644)
            try:
                with pytest.raises(ProtocolError, match="unsafe_state"):
                    issue(observation.server["observed_id"])
            finally:
                runtime.chmod(0o600)
            issued = issue(observation.server["observed_id"])
            assert issued.cookie is not None and token not in repr(issued)
            verify_cookie(tunnel.local_port, fixture.base, issued.cookie)
            base = url.split("login?", 1)[0]
            with requests.Session() as client:
                client.trust_env = False
                assert client.get(base + "api/status", timeout=4).status_code == 403
                assert (
                    client.get(
                        base + "api/status", headers={"Authorization": "token invalid"}, timeout=4
                    ).status_code
                    == 403
                )
                kernel = client.post(
                    base + "api/kernels",
                    json={"name": "python3"},
                    headers={"Authorization": "token " + token},
                    timeout=12,
                )
                kernel.raise_for_status()
                endpoint = (
                    base.replace("http:", "ws:")
                    + "api/kernels/"
                    + kernel.json()["id"]
                    + "/channels"
                )
                try:
                    with pytest.raises(websocket.WebSocketBadStatusException) as denied:
                        websocket.create_connection(
                            endpoint, timeout=4, http_no_proxy=["127.0.0.1"]
                        )
                    assert denied.value.status_code in {401, 403}
                finally:
                    client.delete(
                        base + "api/kernels/" + kernel.json()["id"],
                        headers={"Authorization": "token " + token},
                        timeout=8,
                    )
        assert fixture.record_path.read_bytes() == original
