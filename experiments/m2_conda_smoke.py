"""Discover/open manual servers in two existing Conda interpreters, via jump.

python -m experiments.m2_conda_smoke --second-python /absolute/environment/python
Only private fixture servers are created, read or stopped.
"""

import argparse
import sys

from experiments.jupyter_fixture import JupyterFixture
from experiments.lab import SSHLab
from experiments.m0_spike import execute
from jupyhop.discovery import discover
from jupyhop.opening import open_connection
from jupyhop.ssh import SSHTransport


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--second-python", required=True)
    args = parser.parse_args()
    with (
        SSHLab() as lab,
        JupyterFixture(lab.root / "first", runtime=lab.runtime),
        JupyterFixture(lab.root / "second", python=args.second_python) as second,
    ):
        transport = SSHTransport("destination", config=lab.config)
        pythons = [sys.executable, args.second_python]
        report = discover(transport, pythons, [str(second.runtime)])
        candidates = [s for s in report["servers"] if s["state"] == "ready"]
        if len(candidates) != 2 or len({s["id"] for s in candidates}) != 2:
            raise RuntimeError("Two environment servers were not distinguished")
        server = next(s for s in candidates if s["pid"] == second.process.pid)
        with open_connection(transport, report, server, pythons) as (tunnel, _):
            base = f"http://127.0.0.1:{tunnel.local_port}/science/"
            with second.client() as client:
                result = client.post(base + "api/kernels", json={"name": "python3"}, timeout=15)
                result.raise_for_status()
                kernel = result.json()["id"]
                try:
                    observed = execute(base, second.info["token"], kernel, "print(6 * 7)")
                    if observed.strip() != "42":
                        raise RuntimeError("Second environment kernel execution differs")
                finally:
                    client.delete(base + "api/kernels/" + kernel, timeout=10)
    print(
        "PASS: two Conda environments, distinct manual servers, custom runtime, explicit interpreters, ProxyJump and kernel execution"
    )


if __name__ == "__main__":
    main()
