"""Check a Conda candidate and its exact archive; never upload credentials or files.

Publication itself belongs to UIBCDF's pinned build/upload/promote actions.
This module supplies JupyHop-specific source gates and artifact acceptance.
"""

import argparse
import ast
import hashlib
import json
import os
import re
import shlex
import subprocess
import tarfile
import tomllib
from email import message_from_bytes
from pathlib import Path, PurePosixPath
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "uibcdf/jupyhop"
WORKFLOW = ".github/workflows/checks.yml"
VERSION = re.compile(r"(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
JOBS = {f"linux (3.{minor})" for minor in range(11, 15)} | {
    "server-compatibility (2.17.0)",
    "server-compatibility (2.20.0)",
}


def project_version(root=ROOT):
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    if not VERSION.fullmatch(version):
        raise ValueError("Use numeric x.y.z versions")
    tree = ast.parse((root / "src/jupyhop/__init__.py").read_text())
    declared = [
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets)
    ]
    if declared != [version]:
        raise ValueError("Client/package versions differ")
    return version


def read_github(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "jupyhop-conda-release"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    request = Request("https://api.github.com/repos/" + REPOSITORY + path, headers=headers)
    with urlopen(request, timeout=20) as response:
        body = response.read(2 * 1024 * 1024 + 1)
    if len(body) > 2 * 1024 * 1024:
        raise ValueError("GitHub response exceeds the evidence bound")
    return json.loads(body)


def check_source(sha, version):
    if not SHA.fullmatch(sha) or not VERSION.fullmatch(version):
        raise ValueError("A full candidate SHA and numeric version are required")
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if actual != sha or project_version() != version:
        raise ValueError("Checkout or version differs from the requested candidate")
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=normal"], cwd=ROOT, text=True
    )
    if dirty.strip():
        raise ValueError("Publication requires a clean committed source checkout")
    if os.environ.get("GITHUB_REPOSITORY", REPOSITORY) != REPOSITORY:
        raise ValueError("Publication must run in the owning repository")
    if os.environ.get("GITHUB_SHA", sha) != sha:
        raise ValueError("Workflow source and candidate must be the same commit")
    if os.environ.get("GITHUB_REF", "refs/heads/main") != "refs/heads/main":
        raise ValueError("Dispatch publication from main")
    query = urlencode({"head_sha": sha, "status": "success", "per_page": 100})
    runs = read_github("/actions/workflows/checks.yml/runs?" + query)["workflow_runs"]
    matching = [
        run
        for run in runs
        if run.get("head_sha") == sha
        and run.get("path") == WORKFLOW
        and run.get("event") == "push"
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
    ]
    if not matching:
        raise ValueError("No successful source acceptance run at this exact candidate")
    run = max(matching, key=lambda item: item["id"])
    jobs = read_github(f"/actions/runs/{run['id']}/jobs?per_page=100")["jobs"]
    if len(jobs) != len(JOBS) or {job["name"] for job in jobs} != JOBS:
        raise ValueError("Source acceptance matrix is incomplete")
    for job in jobs:
        if job.get("status") != "completed" or job.get("conclusion") != "success":
            raise ValueError("Every source acceptance job must succeed")
        if job["name"].startswith("linux ("):
            required = {
                "Run pytest --run-integration",
                "Run python -m experiments.package_smoke",
                "Verify installed client upgrade from 0.1.0 using the actual candidate",
                "Verify installed client upgrade from published 0.2.0 source",
            }
            if job["name"] == "linux (3.14)":
                required |= {
                    "Run google-chrome --version && python -m experiments.browser_smoke",
                    "Run python -m experiments.browser_smoke --managed --reconnect",
                    "Verify real Unix account isolation",
                    "Verify native Unix SSH password workflows",
                    "Verify default SSH configuration permission feedback",
                    "Remove isolated account fixture",
                }
            executed = {
                step["name"] for step in job["steps"] if step.get("conclusion") == "success"
            }
            if not required <= executed:
                raise ValueError("Source acceptance omitted a required executed step")
        elif not any(
            step["name"].startswith("Run python -m experiments.m6_compatibility ")
            and step.get("conclusion") == "success"
            for step in job["steps"]
        ):
            raise ValueError("Server compatibility acceptance did not execute")
    return {"candidate_sha": sha, "version": version, "source_run_id": run["id"]}


def inspect_archive(path, version, build_number, root=ROOT):
    if not VERSION.fullmatch(version) or build_number < 0:
        raise ValueError("Invalid Conda version or build number")
    filename = f"jupyhop-{version}-py_{build_number}.tar.bz2"
    if path.name != filename or path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Unexpected Conda archive identity or size")
    payload = {}
    with tarfile.open(path, "r:bz2") as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            if (
                name.is_absolute()
                or ".." in name.parts
                or member.name != name.as_posix()
                or member.name in payload
                or not member.isfile()
                or member.size > 2 * 1024 * 1024
                or len(payload) >= 256
            ):
                raise ValueError("Unsafe Conda archive member")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("Unreadable Conda member")
            payload[member.name] = stream.read()
    if sum(map(len, payload.values())) > 16 * 1024 * 1024:
        raise ValueError("Conda payload exceeds the evidence bound")
    index = json.loads(payload["info/index.json"])
    if any(
        index.get(key) != value
        for key, value in {
            "name": "jupyhop",
            "version": version,
            "build": f"py_{build_number}",
            "build_number": build_number,
            "subdir": "noarch",
            "noarch": "python",
            "license": "MIT",
        }.items()
    ):
        raise ValueError("Conda index differs from the candidate")
    dependencies = {item.replace(" ", "") for item in index["depends"]}
    if dependencies not in (
        {"python>=3.11,<3.15", "__linux", "openssh"},
        {"python>=3.11,<3.15.0a0", "__linux", "openssh"},
    ):
        raise ValueError("Conda runtime must be Linux, supported Python and OpenSSH only")
    link = json.loads(payload["info/link.json"])["noarch"]
    if link.get("type") != "python" or link.get("entry_points") != ["jupyhop = jupyhop.cli:main"]:
        raise ValueError("Conda must create the exact jupyhop launcher")
    expected = {
        "site-packages/jupyhop/" + p.name: p.read_bytes()
        for p in (root / "src/jupyhop").glob("*.py")
    }
    expected["site-packages/jupyhop/py.typed"] = (root / "src/jupyhop/py.typed").read_bytes()
    actual = {
        name: data for name, data in payload.items() if name.startswith("site-packages/jupyhop/")
    }
    if actual != expected or payload["info/licenses/LICENSE"] != (root / "LICENSE").read_bytes():
        raise ValueError("Conda payload differs from the reviewed Python source/license")
    prefix = f"site-packages/jupyhop-{version}.dist-info/"
    if any(not name.startswith(("info/", "site-packages/jupyhop/", prefix)) for name in payload):
        raise ValueError("Conda payload contains an unexpected install path")
    if any(
        not name.startswith("info/")
        and (
            data.startswith((b"\x7fELF", b"MZ")) or name.endswith((".so", ".pyd", ".dll", ".dylib"))
        )
        for name, data in payload.items()
    ):
        raise ValueError("The noarch client must not contain native binaries")
    metadata = message_from_bytes(payload[prefix + "METADATA"])
    if metadata["Name"] != "jupyhop" or metadata["Version"] != version:
        raise ValueError("Installed Python package identity differs")
    if any("extra ==" not in value for value in metadata.get_all("Requires-Dist", [])):
        raise ValueError("The Python client must have no mandatory Python dependencies")
    return {
        "artifact": str(path.resolve()),
        "filename": filename,
        "package": "jupyhop",
        "version": version,
        "build_number": build_number,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("check-source", "inspect"))
    parser.add_argument("--version", required=True)
    parser.add_argument("--candidate-sha")
    parser.add_argument("--build-number", type=int, default=0)
    parser.add_argument("--built-paths")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    if args.operation == "check-source":
        result = check_source(args.candidate_sha or "", args.version)
    else:
        paths = shlex.split(args.built_paths or "")
        if len(paths) != 1:
            raise ValueError("Expected exactly one noarch Conda archive")
        if project_version() != args.version:
            raise ValueError("Version differs from the reviewed source")
        result = inspect_archive(Path(paths[0]), args.version, args.build_number)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    if args.github_output:
        with args.github_output.open("a") as stream:
            for key, value in result.items():
                if "\n" in str(value) or "\r" in str(value):
                    raise ValueError("Multiline action outputs are forbidden")
                stream.write(f"{key}={value}\n")
    print("PASS:", args.operation, args.version)


if __name__ == "__main__":
    main()
