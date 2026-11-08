"""Check a selected server Python using only disposable loopback SSH state.

Run with --server-python /absolute/python; --expect-start-refusal checks older
servers that can be opened but cannot safely supply managed ephemeral ports.
"""

import argparse
import json

from experiments.jupyter_fixture import JupyterFixture
from experiments.lab import SSHLab, free_port
from experiments.m0_spike import execute
from experiments.managed_fixture import ManagedFixture
from jupyhop.discovery import discover, select_server
from jupyhop.lifecycle import lifecycle, require_lifecycle_ok
from jupyhop.managed import require_ready
from jupyhop.opening import open_connection
from jupyhop.ssh import SSHTransport


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-python", required=True)
    parser.add_argument("--expect-start-refusal", action="store_true")
    args = parser.parse_args()
    with SSHLab() as lab:
        transport = SSHTransport("destination", config=lab.config, timeout=40)
        # Older servers do not report port=0's actual socket. An explicit port is
        # fixture-only: JupyHop never adds a remote port allocator for them.
        with JupyterFixture(
            lab.root / "manual", runtime=lab.runtime, python=args.server_python, port=free_port()
        ) as fixture:
            report = discover(transport)
            server = select_server(report, None, interactive=False)
            version = server["version"]
            with open_connection(transport, report, server) as (tunnel, _):
                base = f"http://127.0.0.1:{tunnel.local_port}/science/"
                with fixture.client() as client:
                    response = client.post(
                        base + "api/kernels", json={"name": "python3"}, timeout=20
                    )
                    response.raise_for_status()
                    kernel = response.json()["id"]
                    try:
                        assert (
                            execute(base, fixture.info["token"], kernel, "print(6 * 7)").strip()
                            == "42"
                        )
                    finally:
                        client.delete(base + "api/kernels/" + kernel, timeout=10)
            assert fixture.process.poll() is None
        fixture = ManagedFixture(lab, server_python=args.server_python)
        try:
            report = fixture.launch()
            if args.expect_start_refusal:
                assert report["error"] == "unsupported_server_version", report["error"]
                assert report["record_path"] is None and fixture.record is None
                assert not (lab.home / "state/jupyhop").exists()
            else:
                require_ready(report)
                for operation in ("status", "stop", "archive"):
                    require_lifecycle_ok(lifecycle(transport, operation, fixture.sid))
        finally:
            fixture.close()
    print(
        json.dumps(
            {
                "server_version": version,
                "existing_open_kernel": "passed",
                "managed": "refused_before_write" if args.expect_start_refusal else "passed",
            }
        )
    )


if __name__ == "__main__":
    main()
