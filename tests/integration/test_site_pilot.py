"""Exercise the operator's generic site driver against an isolated SSH fixture."""

import json
import sys
from pathlib import Path

import pytest

from experiments.site_pilot import run_pilot
from jupyhop.errors import PrerequisiteError

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("missing_server_python", [False, True])
def test_site_driver_continuity_and_cleanup_on_confirmed_preflight_refusal(
    ssh_lab, tmp_path, missing_server_python
):
    evidence = tmp_path / "private-pilot.json"
    original_runtime = {
        path.name: path.read_bytes() for path in ssh_lab.runtime.iterdir() if path.is_file()
    }
    with evidence.open("w") as stream:
        kwargs = {
            "ssh_config": ssh_lab.config,
            "hold_seconds": 0.2,
            "evidence": stream,
        }
        if missing_server_python:
            with pytest.raises(PrerequisiteError):
                run_pilot("destination", "/nonexistent/python", [sys.executable], **kwargs)
        else:
            run_pilot("destination", sys.executable, [sys.executable], **kwargs)
    observed = json.loads(evidence.read_text())
    assert observed["state"] == (
        "cleaned_after_failure" if missing_server_python else "cleaned_after_pass"
    )
    assert not observed["cleanup_errors"]
    assert all(not Path(root).exists() for root, _ in observed["manual"])
    assert {
        path.name: path.read_bytes() for path in ssh_lab.runtime.iterdir() if path.is_file()
    } == original_runtime
    if not missing_server_python:
        first, second = observed["observations"]["first"], observed["observations"]["second"]
        assert first["kernel"] == second["kernel"] and first["session"] == second["session"]
        assert first["server_pid"] == second["server_pid"]
        assert second["progress"] > first["progress"]
