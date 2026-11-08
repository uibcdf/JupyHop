"""Unprivileged M5 acceptance against the explicitly provisioned test accounts.

Use m5_accounts prepare/provision/check first. Only its two generated SSH aliases
and sessions created by this experiment are touched. The optional shared server
environment must be readable/executable by both temporary accounts.
"""

import argparse
import json
import uuid
from contextlib import ExitStack
from pathlib import Path

import requests

from experiments.m0_spike import execute
from experiments.m5_accounts import check
from jupyhop.discovery import discover, select_server
from jupyhop.errors import DiscoveryError, JupyHopError
from jupyhop.lifecycle import lifecycle, require_lifecycle_ok
from jupyhop.managed import new_id, require_ready, start
from jupyhop.opening import open_connection
from jupyhop.ssh import SSHTransport


def login(base, password):
    client = requests.Session()
    client.trust_env = False
    client.get(base + "login", timeout=3)
    client.post(
        base + "login", data={"_xsrf": client.cookies.get("_xsrf"), "password": password}, timeout=3
    )
    client.headers["X-XSRFToken"] = client.cookies.get("_xsrf") or ""
    return client


def run(root, server_python):
    check(root)
    config = root / "ssh_config"
    ready = json.loads((root / "ready.json").read_text())
    assert len({user["uid"] for user in ready["users"]}) == 2
    aliases = ("account-a", "account-b")
    transports = {alias: SSHTransport(alias, config=config, timeout=45) for alias in aliases}
    passwords = {alias: "fixture-" + uuid.uuid4().hex for alias in aliases}
    active = []
    reports = {}
    kernels = {}
    name = "acceptance-" + uuid.uuid4().hex[:8]
    try:
        for alias in aliases:
            sid = new_id()
            active.append((alias, sid))
            report = start(
                transports[alias],
                helper_python="/usr/bin/python3",
                server_python=server_python,
                workdir="~/project",
                name=name,
                password=passwords[alias],
                session_id=sid,
            )
            require_ready(report)
            reports[alias] = report
        assert reports[aliases[0]]["identity"]["uid"] != reports[aliases[1]]["identity"]["uid"]
        assert reports[aliases[0]]["identity"]["scope"] != reports[aliases[1]]["identity"]["scope"]
        print(
            "PASS: two actual UIDs independently launch the same display name in private host/account registries",
            flush=True,
        )

        ports = []
        with ExitStack() as stack:
            for index, alias in enumerate(aliases):
                report = discover(transports[alias])
                server = select_server(report, reports[alias]["id"], interactive=False)
                tunnel, _ = stack.enter_context(open_connection(transports[alias], report, server))
                ports.append(tunnel.local_port)
                base = f"http://127.0.0.1:{tunnel.local_port}{server['base_url']}"
                denied = stack.enter_context(login(base, passwords[aliases[1 - index]]))
                assert denied.get(base + "api/status", timeout=3).status_code == 403
                client = stack.enter_context(login(base, passwords[alias]))
                response = client.post(
                    base + "api/sessions",
                    json={
                        "path": "account-test.ipynb",
                        "name": "account-test",
                        "type": "notebook",
                        "kernel": {"name": "python3"},
                    },
                    timeout=15,
                )
                response.raise_for_status()
                session = response.json()
                kernel = session["kernel"]["id"]
                cookie = "; ".join(f"{c.name}={c.value}" for c in client.cookies)
                assert execute(
                    base, "", kernel, f"marker = {70 + index}; print(marker)", cookie=cookie
                ).strip() == str(70 + index)
                kernels[alias] = (kernel, session["id"], 70 + index)
            assert len(set(ports)) == 2
        print(
            "PASS: independent authenticated kernels run concurrently; the other account's password is denied",
            flush=True,
        )

        for alias, other in ((aliases[0], aliases[1]), (aliases[1], aliases[0])):
            other_server = reports[other]["server"]
            listing = discover(transports[alias], runtime_dirs=other_server["sources"])
            assert all(s["id"] != reports[other]["id"] for s in listing["servers"])
            assert any(
                s["id"] == reports[alias]["id"] and s["state"] == "ready"
                for s in listing["servers"]
            )
            data = transports[alias].run(["cat", reports[other]["record_path"]])
            assert data.returncode != 0 and not data.stdout
            for operation in ("stop", "archive"):
                denied = lifecycle(
                    transports[alias], operation, reports[other]["id"], python="/usr/bin/python3"
                )
                assert denied["error"] == "not_managed"
            try:
                with open_connection(transports[alias], listing, other_server):
                    raise AssertionError("Foreign process passed ownership validation")
            except DiscoveryError:
                pass
            assert (
                lifecycle(
                    transports[other], "status", reports[other]["id"], python="/usr/bin/python3"
                )["servers"][0]["state"]
                == "ready"
            )
        print(
            "PASS: each real Unix account cannot enumerate/read/open/stop/archive the other's managed session; both remain alive",
            flush=True,
        )

        for alias in aliases:
            listing = discover(transports[alias])
            server = select_server(listing, reports[alias]["id"], interactive=False)
            with open_connection(transports[alias], listing, server) as (tunnel, _):
                base = f"http://127.0.0.1:{tunnel.local_port}{server['base_url']}"
                with login(base, passwords[alias]) as client:
                    kernel, sid, marker = kernels[alias]
                    sessions = client.get(base + "api/sessions", timeout=3).json()
                    assert any(s["id"] == sid and s["kernel"]["id"] == kernel for s in sessions)
                    cookie = "; ".join(f"{c.name}={c.value}" for c in client.cookies)
                    assert execute(base, "", kernel, "print(marker)", cookie=cookie).strip() == str(
                        marker
                    )
            require_lifecycle_ok(
                lifecycle(
                    transports[alias], "stop", reports[alias]["id"], python="/usr/bin/python3"
                )
            )
            require_lifecycle_ok(
                lifecycle(
                    transports[alias], "archive", reports[alias]["id"], python="/usr/bin/python3"
                )
            )
            active.remove((alias, reports[alias]["id"]))
        print(
            "PASS: both accounts reconnect to the same live notebook/kernel memory, then stop/archive only their own sessions",
            flush=True,
        )
    finally:
        for alias, sid in active:
            try:
                lifecycle(transports[alias], "stop", sid, python="/usr/bin/python3")
            except JupyHopError:
                pass
    print(
        "Real-account M5 acceptance passed. Operator cleanup of the temporary users/sshd remains explicit.",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--server-python", required=True)
    args = parser.parse_args()
    run(args.root, args.server_python)


if __name__ == "__main__":
    main()
