"""Installed-wheel upgrade acceptance using only disposable loopback resources.

Build the trusted historical client from a local commit. Supply an actual new
wheel, or explicitly build a temporary version preview without changing this
checkout. Neither path publishes a release or installs anything remotely.
"""

import argparse
import hashlib
import importlib.util
import io
import json
import math
import os
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
from contextlib import contextmanager
from email import message_from_bytes
from pathlib import Path
from zipfile import ZipFile

from experiments.lab import SSHLab

BASELINE_REF = "21e0dc97161d83088ae6ad850027fa4d17ee4d3c"
PROJECT = Path(__file__).resolve().parents[1]


def version_number(value):
    if re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2}", value) is None:
        raise ValueError("Use a numeric x.y.z version without prefixes or suffixes")
    return tuple(map(int, value.split(".")))


def run_command(argv, *, environment=None, cwd=None, stdin=None, timeout=90):
    result = subprocess.run(
        argv, input=stdin, capture_output=True, env=environment, cwd=cwd, timeout=timeout
    )
    if result.returncode:
        # Commands can receive fixture passwords. Keep arbitrary output private.
        raise RuntimeError("Upgrade fixture command failed; raw output suppressed")
    return result.stdout


def build_wheel(source, destination):
    if importlib.util.find_spec("setuptools") is None:
        raise RuntimeError(
            "Offline wheel builds require the dev build backend; install .[dev] including setuptools>=77 first"
        )
    destination.mkdir()
    run_command(
        [sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", str(destination)],
        cwd=source,
    )
    wheels = list(destination.glob("*.whl"))
    assert len(wheels) == 1
    return wheels[0]


def wheel_version(path):
    with ZipFile(path) as artifact:
        names = [name for name in artifact.namelist() if name.endswith(".dist-info/METADATA")]
        assert len(names) == 1, "Expected a single trusted JupyHop distribution"
        metadata = message_from_bytes(artifact.read(names[0]))
        assert metadata["Name"] == "jupyhop"
        version = metadata["Version"]
        version_number(version)
        return version


def prepare_wheels(root, baseline_ref, *, candidate_wheel=None, preview_version=None):
    if re.fullmatch(r"[0-9a-f]{7,40}", baseline_ref) is None:
        raise ValueError("Use a trusted local commit hash for the baseline")
    if preview_version is not None:
        version_number(preview_version)
    previous = root / "baseline-source"
    previous.mkdir()
    archived = run_command(["git", "archive", baseline_ref], cwd=PROJECT)
    with tarfile.open(fileobj=io.BytesIO(archived)) as snapshot:
        snapshot.extractall(previous, filter="data")
    old_wheel = build_wheel(previous, root / "baseline-dist")
    if preview_version is not None:
        source = root / "preview-source"
        source.mkdir()
        for name in ("pyproject.toml", "README.md", "LICENSE"):
            shutil.copyfile(PROJECT / name, source / name)
        shutil.copytree(
            PROJECT / "src",
            source / "src",
            ignore=shutil.ignore_patterns("*.egg-info", "__pycache__"),
        )
        project_file = source / "pyproject.toml"
        current = tomllib.loads(project_file.read_text())["project"]["version"]
        assert version_number(preview_version) >= version_number(current)
        for path in (project_file, source / "src/jupyhop/__init__.py"):
            text = path.read_text()
            old = f'version = "{current}"' if path == project_file else f'__version__ = "{current}"'
            assert text.count(old) == 1
            path.write_text(text.replace(old, old.replace(current, preview_version)))
        new_wheel = build_wheel(source, root / "preview-dist")
    else:
        new_wheel = candidate_wheel.resolve(strict=True)
    assert version_number(wheel_version(new_wheel)) > version_number(wheel_version(old_wheel))
    return old_wheel, new_wheel


class InstalledClient:
    def __init__(self, lab, label, wheel, *, jump):
        from experiments.m4_reconnect import independent_client

        self.config = independent_client(lab, label, jump=jump)
        self.root = self.config.parent
        self.environment = dict(os.environ)
        for key in ("PYTHONPATH", "PYTHONHOME"):
            self.environment.pop(key, None)
        self.environment.update(
            HOME=str(self.root),
            XDG_CONFIG_HOME=str(self.root / "config"),
            PYTHONNOUSERSITE="1",
            PIP_CONFIG_FILE=os.devnull,
            PIP_DISABLE_PIP_VERSION_CHECK="1",
        )
        self.venv = self.root / "venv"
        self.python = self.venv / "bin/python"
        self.cli = self.venv / "bin/jupyhop"
        self.run([sys.executable, "-I", "-m", "venv", str(self.venv)])
        self.install(wheel)

    def run(self, argv, *, stdin=None):
        return run_command(argv, environment=self.environment, cwd=self.root, stdin=stdin)

    def install(self, wheel):
        self.run(
            [str(self.python), "-I", "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)]
        )
        self.run(
            [
                str(self.python),
                "-I",
                "-c",
                "import importlib.util; assert importlib.util.find_spec('jupyter_server') is None",
            ]
        )
        installed = self.run([str(self.cli), "--version"]).decode().strip()
        assert installed.endswith(wheel_version(wheel))

    def command(self, operation, sid=None, *extra):
        return [
            str(self.cli),
            operation,
            "remote",
            *([sid] if sid else []),
            "--ssh-config",
            str(self.config),
            "--json",
            "--timeout",
            "40",
            *extra,
        ]

    def rpc(self, operation, sid=None, *extra, stdin=None):
        return json.loads(self.run(self.command(operation, sid, *extra), stdin=stdin))

    @contextmanager
    def opened(self, sid):
        process = subprocess.Popen(
            self.command("open", sid, "--no-browser"),
            cwd=self.root,
            env=self.environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                assert selector.select(45), "Installed client open timed out"
            connection = json.loads(process.stdout.readline())
            assert connection["id"] == sid and connection["origin"] == "managed"
            assert (
                connection["authentication"] == "jupyter-login"
                and "token=" not in connection["url"]
            )
            yield connection["url"].split("login?", 1)[0]
            process.send_signal(signal.SIGINT)
            process.communicate(timeout=10)
            assert process.returncode == 130
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate(timeout=5)


def kernel_observation(base, *, create=False, duration=0, password="fixture-password"):
    import requests

    from experiments.m0_spike import execute

    with requests.Session() as client:
        client.trust_env = False
        client.get(base + "login", timeout=5).raise_for_status()
        client.post(
            base + "login",
            data={"_xsrf": client.cookies.get("_xsrf"), "password": password},
            timeout=5,
        ).raise_for_status()
        client.headers["X-XSRFToken"] = client.cookies.get("_xsrf") or ""
        if create:
            response = client.post(
                base + "api/sessions",
                json={
                    "path": "upgrade.ipynb",
                    "type": "notebook",
                    "name": "upgrade",
                    "kernel": {"name": "python3"},
                },
                timeout=20,
            )
            response.raise_for_status()
            session = response.json()
            code = f"""import json, os, threading, time
upgrade_marker = sum(range(4096))
upgrade_progress = [0]
upgrade_started = threading.Event()
upgrade_finish = threading.Event()
def upgrade_compute():
    deadline = time.monotonic() + {duration + 300!r}
    upgrade_started.set()
    while not upgrade_finish.wait(0.1) and time.monotonic() < deadline:
        assert sum(range(4096)) == upgrade_marker
        upgrade_progress[0] += 1
threading.Thread(target=upgrade_compute, daemon=True).start()
assert upgrade_started.wait(5)
"""
        else:
            response = client.get(base + "api/sessions", timeout=5)
            response.raise_for_status()
            sessions = response.json()
            assert len(sessions) == 1 and sessions[0]["path"] == "upgrade.ipynb"
            session = sessions[0]
            code = ""
        code += "\nprint(json.dumps({'pid': os.getpid(), 'marker': upgrade_marker, 'progress': upgrade_progress[0]}))"
        cookie = "; ".join(f"{item.name}={item.value}" for item in client.cookies)
        result = json.loads(execute(base, "", session["kernel"]["id"], code, cookie=cookie))
        return dict(result, session=session["id"], kernel=session["kernel"]["id"])


def check_continuity(first, current):
    for key in ("pid", "marker", "session", "kernel"):
        assert first[key] == current[key], f"Kernel continuity failed: {key}"
    assert current["progress"] > first["progress"], "Background computation stopped progressing"


def exercise(old_wheel, new_wheel, *, hold_seconds=2, reverse_managed=False):
    from experiments.managed_fixture import ManagedFixture

    with SSHLab() as lab:
        cleanup = ManagedFixture(lab)
        try:
            upgraded = InstalledClient(lab, "upgraded-client", old_wheel, jump=True)
            old = InstalledClient(lab, "old-client", old_wheel, jump=False)
            fresh = InstalledClient(lab, "fresh-client", new_wheel, jump=True)
            launched = upgraded.rpc(
                "start",
                None,
                "--server-python",
                sys.executable,
                "--workdir",
                "~",
                "--name",
                "upgrade-fixture",
                "--password-stdin",
                "--no-open",
                stdin=b"fixture-password\n",
            )
            assert launched["state"] == "ready"
            sid = launched["id"]
            record_path = Path(launched["record_path"])
            assert record_path.is_relative_to(lab.home / "state/jupyhop")
            original_record = record_path.read_bytes()
            record = cleanup.record = json.loads(original_record)
            cleanup.url = f"http://127.0.0.1:{record['port']}{record['base_url']}"
            runner_path = record_path.with_name("launch.py")
            original_runner = runner_path.read_bytes()
            assert hashlib.sha256(original_runner).hexdigest() == record["runner_sha256"]
            with upgraded.opened(sid) as base:
                first = kernel_observation(base, create=True, duration=hold_seconds)
            print(
                "PASS: installed old client started a kernel and closed every first-client connection",
                flush=True,
            )
            disconnected = time.monotonic()
            deadline = disconnected + hold_seconds
            while time.monotonic() < deadline:
                time.sleep(min(30, max(0, deadline - time.monotonic())))
                if time.monotonic() < deadline:
                    print(
                        f"OBSERVED: disconnected toy workload, {time.monotonic() - disconnected:.0f}s elapsed",
                        flush=True,
                    )
            upgraded.install(new_wheel)
            for client in (upgraded, old, fresh):
                status = client.rpc("status", sid)
                assert status["error"] is None and status["servers"][0]["state"] == "ready"
                assert status["servers"][0]["pid"] == record["pid"]
            with upgraded.opened(sid) as new_base, old.opened(sid) as old_base:
                check_continuity(first, kernel_observation(new_base))
                check_continuity(first, kernel_observation(old_base))
                with fresh.opened(sid) as fresh_base:
                    last = kernel_observation(fresh_base)
                    check_continuity(first, last)
            assert record_path.read_bytes() == original_record
            assert runner_path.read_bytes() == original_runner
            print(
                "PASS: upgraded, concurrent old and independent new installed clients retain server/kernel/session/PID/memory/progress and immutable registry/runner",
                flush=True,
            )
            for _ in range(2):
                stopped = fresh.rpc("stop", sid, "--yes")
                assert stopped["error"] is None and stopped["servers"][0]["state"] == "stopped"
            archived = fresh.rpc("archive", sid, "--yes")
            assert archived["archived"]["id"] == sid
            print(
                "PASS: new installed client safely stops and archives only the experiment UUID",
                flush=True,
            )
            if reverse_managed:
                reverse_access(lab, old, fresh, cleanup)
        finally:
            # A lost reply in either launch can still leave a session in this lab.
            for path in (lab.home / "state/jupyhop").glob("hosts/*/sessions/*/record.json"):
                cleanup.sid = path.parent.name
                cleanup.record = json.loads(path.read_text())
                if cleanup.record.get("port"):
                    cleanup.url = (
                        f"http://127.0.0.1:{cleanup.record['port']}{cleanup.record['base_url']}"
                    )
                cleanup.close()


def reverse_access(lab, old, fresh, cleanup):
    """Check that an installed 0.3 client understands a 0.4 token runner."""
    import requests

    launched = fresh.rpc(
        "start",
        None,
        "--server-python",
        sys.executable,
        "--name",
        "new-token-fixture",
        "--no-open",
    )
    assert launched["state"] == "ready"
    sid = cleanup.sid = launched["id"]
    path = Path(launched["record_path"])
    assert path.is_relative_to(lab.home / "state/jupyhop")
    cleanup.record = record = json.loads(path.read_text())
    cleanup.url = f"http://127.0.0.1:{record['port']}{record['base_url']}"
    assert old.rpc("status", sid)["servers"][0]["state"] == "ready"
    token = json.loads(Path(record["runtime"], f"jpserver-{record['pid']}.json").read_text())[
        "token"
    ]
    assert re.fullmatch(r"[a-f0-9]{64}", token)
    with old.opened(sid) as base, requests.Session() as client:
        client.trust_env = False
        assert client.get(base + "api/status", timeout=4).status_code == 403
        assert (
            client.get(
                base + "api/status", headers={"Authorization": "token " + token}, timeout=4
            ).status_code
            == 200
        )
    assert old.rpc("stop", sid, "--yes")["servers"][0]["state"] == "stopped"
    assert old.rpc("archive", sid, "--yes")["archived"]["id"] == sid
    print(
        "PASS: installed 0.3 observes, opens manually, stops and archives a new token runner",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", default=BASELINE_REF)
    candidate = parser.add_mutually_exclusive_group(required=True)
    candidate.add_argument("--candidate-wheel", type=Path)
    candidate.add_argument("--preview-version")
    parser.add_argument("--hold-seconds", type=float, default=2)
    parser.add_argument(
        "--reverse-managed", action="store_true", help="Also check 0.3 against a new token runner."
    )
    args = parser.parse_args()
    if not math.isfinite(args.hold_seconds) or not 0 <= args.hold_seconds <= 14400:
        parser.error("Hold duration must be between 0 and 14400 seconds")
    with tempfile.TemporaryDirectory(prefix="jupyhop-upgrade-") as directory:
        root = Path(directory)
        root.chmod(0o700)
        old, new = prepare_wheels(
            root,
            args.baseline_ref,
            candidate_wheel=args.candidate_wheel,
            preview_version=args.preview_version,
        )
        print(
            "Mode:",
            "temporary version preview" if args.preview_version else "actual candidate wheel",
            flush=True,
        )
        for label, wheel in (("baseline", old), ("candidate", new)):
            print(
                label,
                wheel_version(wheel),
                "SHA256",
                hashlib.sha256(wheel.read_bytes()).hexdigest(),
                flush=True,
            )
        exercise(old, new, hold_seconds=args.hold_seconds, reverse_managed=args.reverse_managed)


if __name__ == "__main__":
    main()
