"""Launch a trusted historical runner, then observe/stop it with this client.

Run `python -m experiments.m4_compatibility --legacy-ref COMMIT` from a checkout
containing that local commit. Uses only disposable loopback SSH/Jupyter state.
"""

import argparse
import hashlib
import re
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from experiments.lab import SSHLab
from experiments.managed_fixture import ManagedFixture
from jupyhop.lifecycle import lifecycle, require_lifecycle_ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-ref", required=True)
    args = parser.parse_args()
    if re.fullmatch(r"[0-9a-f]{7,40}", args.legacy_ref) is None:
        parser.error("Use a trusted local commit hash.")
    sources = {}
    for name in ("_discovery_probe.py", "_managed_remote.py"):
        sources[name] = subprocess.run(
            ["git", "show", args.legacy_ref + ":src/jupyhop/" + name],
            capture_output=True,
            check=True,
        ).stdout.decode()
    reader = SimpleNamespace(joinpath=lambda name: SimpleNamespace(read_text=lambda: sources[name]))
    with SSHLab() as lab:
        with (
            patch("jupyhop.managed.files", return_value=reader),
            ManagedFixture(lab, name="legacy-runner") as fixture,
        ):
            original = fixture.record_path.with_name("launch.py").read_bytes()
            assert hashlib.sha256(original).hexdigest() == fixture.record["runner_sha256"]
            report = lifecycle(fixture.transport, "status", fixture.sid)
            require_lifecycle_ok(report)
            assert report["servers"][0]["state"] == "ready"
            report = lifecycle(fixture.transport, "stop", fixture.sid)
            require_lifecycle_ok(report)
            assert report["servers"][0]["state"] == "stopped"
            assert fixture.record_path.with_name("launch.py").read_bytes() == original
            assert (
                lifecycle(fixture.transport, "stop", fixture.sid)["servers"][0]["state"]
                == "stopped"
            )
    print(
        "PASS: legacy immutable runner survives client upgrade, remains unchanged and supports safe status/idempotent stop without schema migration"
    )


if __name__ == "__main__":
    main()
