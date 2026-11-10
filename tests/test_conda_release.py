"""Publication gates must reject untested commits and altered package payloads."""

import io
import json
import tarfile
from pathlib import Path
from unittest.mock import patch

import pytest

from experiments import conda_release as release


def archive_payload():
    version = release.project_version()
    index = {
        "name": "jupyhop",
        "version": version,
        "build": "py_0",
        "build_number": 0,
        "noarch": "python",
        "subdir": "noarch",
        "license": "MIT",
        "depends": ["python >=3.11,<3.15", "__linux", "openssh"],
    }
    payload = {
        "info/index.json": json.dumps(index).encode(),
        "info/link.json": json.dumps(
            {"noarch": {"type": "python", "entry_points": ["jupyhop = jupyhop.cli:main"]}}
        ).encode(),
        "info/licenses/LICENSE": Path("LICENSE").read_bytes(),
        f"site-packages/jupyhop-{version}.dist-info/METADATA": (
            f"Name: jupyhop\nVersion: {version}\n\n"
        ).encode(),
    }
    payload.update(
        {
            "site-packages/jupyhop/" + p.name: p.read_bytes()
            for p in Path("src/jupyhop").iterdir()
            if p.is_file()
        }
    )
    return payload


def write_archive(tmp_path, payload, *, symlink=False):
    archive = tmp_path / f"jupyhop-{release.project_version()}-py_0.tar.bz2"
    with tarfile.open(archive, "w:bz2") as stream:
        for name, data in payload.items():
            member = tarfile.TarInfo(name)
            member.size = len(data)
            stream.addfile(member, io.BytesIO(data))
        if symlink:
            member = tarfile.TarInfo("site-packages/escape")
            member.type = tarfile.SYMTYPE
            member.linkname = "/outside"
            stream.addfile(member)
    return archive


def test_conda_source_license_and_launcher_match_reviewed_package(tmp_path):
    result = release.inspect_archive(
        write_archive(tmp_path, archive_payload()), release.project_version(), 0
    )
    assert result["filename"].endswith("-py_0.tar.bz2")
    assert len(result["sha256"]) == 64


@pytest.mark.parametrize(
    "change", ["path", "alias", "native", "source", "platform", "dependency", "launcher", "symlink"]
)
def test_conda_archive_rejects_unsafe_or_different_installation(tmp_path, change):
    payload = archive_payload()
    if change == "path":
        payload["../escape"] = b"unreviewed"
    elif change == "alias":
        payload["info/./index.json"] = payload["info/index.json"]
    elif change == "native":
        payload[f"site-packages/jupyhop-{release.project_version()}.dist-info/unreviewed.so"] = (
            b"\x7fELF"
        )
    elif change == "source":
        payload["site-packages/jupyhop/cli.py"] += b"\n# altered after review\n"
    elif change in {"platform", "dependency"}:
        index = json.loads(payload["info/index.json"])
        if change == "platform":
            index["depends"].remove("__linux")
        else:
            index["depends"].append("jupyter_server")
        payload["info/index.json"] = json.dumps(index).encode()
    elif change == "launcher":
        payload["info/link.json"] = b'{"noarch":{"type":"python","entry_points":[]}}'
    path = write_archive(tmp_path, payload, symlink=change == "symlink")
    with pytest.raises(ValueError):
        release.inspect_archive(path, release.project_version(), 0)


def source_gate_responses(sha):
    run = {
        "id": 17,
        "head_sha": sha,
        "path": release.WORKFLOW,
        "event": "push",
        "status": "completed",
        "conclusion": "success",
    }
    steps = [
        "Run pytest --run-integration",
        "Run python -m experiments.package_smoke",
        "Verify installed client upgrade from 0.1.0 using the actual candidate",
        "Verify installed client upgrade from published 0.2.0 source",
        "Run google-chrome --version && python -m experiments.browser_smoke",
        "Run python -m experiments.browser_smoke --managed --reconnect",
        'Run python -m experiments.m6_compatibility --server-python "$(command -v python)"',
        "Verify real Unix account isolation",
        "Verify native Unix SSH password workflows",
        "Verify default SSH configuration permission feedback",
        "Remove isolated account fixture",
    ]
    jobs = [
        {
            "name": name,
            "status": "completed",
            "conclusion": "success",
            "steps": [{"name": name, "conclusion": "success"} for name in steps],
        }
        for name in release.JOBS
    ]
    return [{"workflow_runs": [run]}, {"jobs": jobs}]


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "wrong_commit",
        "missing_job",
        "skipped_step",
        "failed_job",
        "missing_02_upgrade",
        "missing_config_acceptance",
    ],
)
def test_source_acceptance_requires_exact_complete_executed_matrix(monkeypatch, failure):
    sha = "1" * 40
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("GITHUB_REF", raising=False)
    responses = source_gate_responses(sha)
    if failure == "wrong_commit":
        responses[0]["workflow_runs"][0]["head_sha"] = "2" * 40
    elif failure in {"missing_02_upgrade", "missing_config_acceptance"}:
        name = (
            "Verify installed client upgrade from published 0.2.0 source"
            if failure == "missing_02_upgrade"
            else "Verify default SSH configuration permission feedback"
        )
        job = next(j for j in responses[1]["jobs"] if j["name"] == "linux (3.14)")
        job["steps"] = [step for step in job["steps"] if step["name"] != name]
    elif failure == "missing_job":
        responses[1]["jobs"].pop()
    elif failure == "skipped_step":
        job = next(j for j in responses[1]["jobs"] if j["name"] == "linux (3.14)")
        job["steps"][-1]["conclusion"] = "skipped"
    elif failure == "failed_job":
        responses[1]["jobs"][0]["conclusion"] = "failure"
    with (
        patch.object(release.subprocess, "check_output", side_effect=[sha, ""]),
        patch.object(release, "read_github", side_effect=responses),
    ):
        if failure:
            with pytest.raises(ValueError):
                release.check_source(sha, release.project_version())
        else:
            assert release.check_source(sha, release.project_version())["source_run_id"] == 17


def test_source_gate_rejects_different_workflow_code(monkeypatch):
    sha = "1" * 40
    monkeypatch.setenv("GITHUB_SHA", "2" * 40)
    with (
        patch.object(release.subprocess, "check_output", side_effect=[sha, ""]),
        patch.object(release, "read_github") as network,
    ):
        with pytest.raises(ValueError, match="Workflow source"):
            release.check_source(sha, release.project_version())
        network.assert_not_called()


def test_source_gate_rejects_uncommitted_source_before_any_network_request():
    sha = "1" * 40
    with (
        patch.object(
            release.subprocess, "check_output", side_effect=[sha, " M src/jupyhop/cli.py"]
        ),
        patch.object(release, "read_github") as network,
    ):
        with pytest.raises(ValueError, match="clean committed"):
            release.check_source(sha, release.project_version())
        network.assert_not_called()
