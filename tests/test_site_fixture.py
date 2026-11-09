"""Cleanup must refuse unrelated paths even when invoked with operator inputs."""

import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from experiments.site_pilot import MANUAL_CLEANUP


@pytest.mark.parametrize("kind", ["symlink", "wrong-marker", "owned"])
def test_site_cleanup_requires_private_owned_directory_and_matching_marker(tmp_path, kind):
    root = Path("/tmp") / ("jupyhop-site-" + uuid.uuid4().hex)
    protected = tmp_path / "scientific-data.txt"
    protected.write_text("synthetic data must survive")
    if kind == "symlink":
        root.symlink_to(tmp_path, target_is_directory=True)
    else:
        root.mkdir(mode=0o700)
        (root / ".fixture").write_text(root.name if kind == "owned" else "unrelated")
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-c", MANUAL_CLEANUP],
            input=json.dumps({"root": str(root), "remove": True}).encode(),
            capture_output=True,
            timeout=10,
        )
        assert protected.read_text() == "synthetic data must survive"
        if kind == "owned":
            assert result.returncode == 0 and json.loads(result.stdout)["removed"]
            assert not root.exists()
        else:
            assert result.returncode != 0
            assert root.is_symlink() if kind == "symlink" else root.is_dir()
    finally:
        if root.is_symlink():
            root.unlink()
        elif root.exists():
            shutil.rmtree(root)
