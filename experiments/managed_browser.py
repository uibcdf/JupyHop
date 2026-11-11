"""Verify the implemented start/resume browser path on disposable SSHLab hosts."""

import argparse
import json
import os
import select
import shlex
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import unquote, urlsplit

from experiments.browser_handoff import chrome, firefox, kernel_roundtrip
from experiments.lab import SSHLab, stop
from experiments.m4_reconnect import independent_client
from experiments.managed_fixture import ManagedFixture


@contextmanager
def attached(
    lab, argv, config, *, password=None, client_python=None, cancelled=False, system_launcher=False
):
    environment = dict(os.environ, XDG_CONFIG_HOME=str(lab.root / "client-config"))
    if client_python:
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONHOME", None)
    access_flags = ["--no-browser"]
    receipt = lab.root / "browser-launch-uri"
    if system_launcher:
        # The system launcher uses this private selection. The test actor then
        # opens the received URI in its isolated real browser.
        launcher = lab.root / "selected-browser"
        launcher.write_text('#!/bin/sh\nprintf "%s" "$1" > ' + shlex.quote(str(receipt)) + "\n")
        launcher.chmod(0o700)
        for key in ("DISPLAY", "WAYLAND_DISPLAY", "XDG_CURRENT_DESKTOP", "DESKTOP_SESSION"):
            environment.pop(key, None)
        environment["BROWSER"] = str(launcher)
        access_flags = ["--json", "--login", "auto"]
    with subprocess.Popen(
        [
            client_python or sys.executable,
            "-m",
            "jupyhop",
            *argv,
            "--batch",
            "--timeout",
            "40",
            "--ssh-config",
            str(config),
            *access_flags,
        ],
        stdin=subprocess.PIPE if password else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        start_new_session=True,
    ) as process:
        try:
            if password:
                process.stdin.write((password + "\n").encode())
                process.stdin.flush()
            if system_launcher:
                deadline = time.monotonic() + 35
                while not receipt.exists() or not receipt.stat().st_size:
                    if process.poll() is not None or time.monotonic() >= deadline:
                        stop(process)
                        raise RuntimeError(
                            "System launcher failed: " + process.stderr.read(4096).decode()
                        )
                    time.sleep(0.05)
                line = receipt.read_text()
                assert not select.select([process.stdout], [], [], 0)[0]
            else:
                assert select.select([process.stdout], [], [], 35)[0], (
                    "No protected launch file was offered"
                )
                line = process.stdout.readline().decode()
            if system_launcher and Path(line).is_absolute():
                # xdg-open can pass the selected application a filesystem path.
                launch = Path(line)
            elif "file://" in line:
                launch = Path(
                    unquote(urlsplit("file://" + line.split("file://", 1)[1].strip()).path)
                )
            else:
                stop(process)
                raise RuntimeError("Automatic access failed: " + process.stderr.read(4096).decode())
            assert launch.stat().st_mode & 0o777 == 0o600
            yield launch
            process.send_signal(signal.SIGTERM if cancelled else signal.SIGINT)
            stdout, stderr = process.communicate(timeout=10)
            assert process.returncode == 130
            assert (b"Jupyter is ready." in stderr) is not cancelled
            if system_launcher:
                result = json.loads(stdout)
                assert set(result) == {"host", "id", "origin", "url", "authentication", "tunnel"}
                assert result["authentication"] == "jupyter-login"
                assert result["tunnel"] == "attached"
            assert (
                b"token=" not in stdout + stderr and b"New Jupyter session password" not in stderr
            )
            assert b"Discovery is partial" not in stderr
            assert not launch.exists() and not launch.parent.exists()
        finally:
            stop(process)


def visit(
    lab,
    argv,
    config,
    browser,
    label,
    *,
    create,
    password=None,
    client_python=None,
    system_launcher=False,
):
    root = lab.root / label
    root.mkdir(mode=0o700)
    with (
        attached(
            lab,
            argv,
            config,
            password=password,
            client_python=client_python,
            system_launcher=system_launcher,
        ) as launch,
        browser(root, launch) as client,
    ):
        client.until("!!document.querySelector('.jp-LabShell')")
        parsed = urlsplit(client.evaluate("location.href"))
        assert parsed.path.endswith("/lab") and not parsed.query
        assert parsed.hostname == "127.0.0.1" and not launch.exists()
        base = f"http://{parsed.netloc}{parsed.path.removesuffix('lab')}"
        result = kernel_roundtrip(client, base, create=create)
        assert result["output"] == "42"
        return result


def managed_case(browser, *, password=None, client_python=None):
    with SSHLab() as lab:
        name = "browser-project"
        try:
            argv = ["start", "destination", "--server-python", sys.executable, "--name", name]
            if password:
                argv += ["--password-stdin"]
            first = visit(
                lab,
                argv,
                lab.config,
                browser,
                "first",
                create=True,
                password=password,
                client_python=client_python,
                system_launcher=password is None,
            )
            if not password:
                config = independent_client(lab, "independent", jump=False)
                reopen = ["resume", "remote", "--name", name]
                with attached(lab, reopen, config, client_python=client_python, cancelled=True):
                    pass
                second = visit(
                    lab,
                    reopen,
                    config,
                    browser,
                    "second",
                    create=False,
                    client_python=client_python,
                )
                assert first == second
        finally:
            # The lab's XDG state and sockets belong only to this invocation.
            for path in (lab.home / "state/jupyhop").glob("hosts/*/sessions/*/record.json"):
                fixture = ManagedFixture(lab)
                fixture.sid = path.parent.name
                fixture.record = json.loads(path.read_text())
                if fixture.record["port"]:
                    fixture.url = (
                        f"http://127.0.0.1:{fixture.record['port']}{fixture.record['base_url']}"
                    )
                fixture.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firefox", metavar="EXECUTABLE")
    parser.add_argument("--geckodriver", default="geckodriver")
    parser.add_argument(
        "--client-python", metavar="EXECUTABLE", help="Use an independently installed client wheel."
    )
    args = parser.parse_args()
    browser = (
        chrome
        if not args.firefox
        else lambda root, launch: firefox(root, launch, args.firefox, args.geckodriver)
    )
    managed_case(browser, client_python=args.client_python)
    managed_case(browser, password="disposable-browser-password", client_python=args.client_python)
    print(
        "PASS: default start and independent named resume preserve kernel/session/memory; fresh password-stdin start uses native browser access without reentry"
    )


if __name__ == "__main__":
    main()
