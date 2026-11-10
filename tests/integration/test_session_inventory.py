import pytest

from experiments.lab import SSHLab
from experiments.managed_fixture import ManagedFixture
from jupyhop.lifecycle import lifecycle, require_lifecycle_ok
from jupyhop.session_inventory import inspect_sessions, summary
from jupyhop.ssh import SSHTransport

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("host", ["direct", "destination"])
def test_inventory_observes_live_stopped_and_archived_without_writing(host):
    with SSHLab() as lab, ManagedFixture(lab, name="analysis") as fixture:
        transport = SSHTransport(host, config=lab.config, timeout=40)
        before = fixture.record_path.read_bytes()
        launch = fixture.record_path.parent / "launch.py"
        runner = launch.read_bytes()
        report = inspect_sessions(transport)
        assert report["complete"] and report["error"] is None
        assert summary(report) == {
            "ready": 1,
            "stopped": 0,
            "review": 0,
            "unarchived": 1,
            "archived": 0,
            "archive_count_exact": True,
        }
        assert report["sessions"][0]["id"] == fixture.sid
        assert fixture.record_path.read_bytes() == before and launch.read_bytes() == runner
        stopped = lifecycle(transport, "stop", fixture.sid)
        require_lifecycle_ok(stopped)
        assert summary(inspect_sessions(transport))["stopped"] == 1
        archived = lifecycle(transport, "archive", fixture.sid)
        require_lifecycle_ok(archived)
        after = inspect_sessions(transport)
        assert summary(after)["unarchived"] == 0
        assert summary(after)["archived"] == 1
        assert after["history"]["entries"][0]["id"] == fixture.sid
        assert after["history"]["entries"][0]["name"] == "analysis"
        assert "password" not in str(after)
