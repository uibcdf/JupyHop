import os
import shutil
from pathlib import Path

import pytest

from experiments.lab import SSHLab


@pytest.fixture(autouse=True)
def isolated_local_config(tmp_path, monkeypatch):
    # A developer's optional host/profile preferences must never influence
    # fixture routes, working directories or executable selection.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "isolated-client-config"))


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration", action="store_true", help="Run private loopback sshd tests."
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration"):
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(
                    pytest.mark.skip(reason="Use --run-integration for disposable SSH tests")
                )


def pytest_ignore_collect(collection_path, config):
    # Unit-only development does not import optional Jupyter/browser dependencies.
    return collection_path.name == "integration" and not config.getoption("--run-integration")


@pytest.fixture(scope="session")
def ssh_lab():
    if os.getuid() == 0:
        pytest.fail("Integration fixtures must run as a non-root Unix account")
    for executable in ("ssh", "sshd", "ssh-keygen"):
        if shutil.which(executable) is None:
            pytest.fail(f"Required integration executable missing: {executable}")
    if not Path("/run/sshd").is_dir():
        pytest.fail("Integration prerequisite: /run/sshd must exist")
    with SSHLab() as lab:
        yield lab
