"""Regenerate documentation illustrations using disposable loopback SSH/Jupyter.

Run with the experiments dependencies and Chrome installed:
    python -m experiments.docs_assets

Only synthetic notebooks/credentials enter the isolated fixture. Chrome uses
its default sandbox and a private profile. Output replaces the two PNG assets
and the normalized session-menu transcript; real SSH configuration is not used.
"""

import argparse
import base64
import contextlib
import io
import json
import shutil
import subprocess
import time
from pathlib import Path
from unittest.mock import patch

import requests

from experiments.browser_smoke import DevTools
from experiments.lab import SSHLab, stop
from experiments.m0_spike import execute
from experiments.managed_fixture import ManagedFixture
from jupyhop.cli import main as cli_main
from jupyhop.discovery import discover, select_server
from jupyhop.opening import open_connection
from jupyhop.ssh import SSHTransport

CODE = 'continuity_marker = "hello from the remote kernel"\nprint(continuity_marker)\nprint(sum(range(10)))'
EXPECTED = "hello from the remote kernel\n45"


class Terminal(io.StringIO):
    def isatty(self):
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/_static"))
    args = parser.parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    quickstart = Path(__file__).resolve().parents[1] / "docs/quickstart.md"
    if CODE not in quickstart.read_text() or EXPECTED not in quickstart.read_text():
        raise RuntimeError("Update the fixture cell to match the current Quickstart")
    with SSHLab() as lab:
        project = lab.home / "analysis"
        project.mkdir(mode=0o700)
        with (
            ManagedFixture(lab, name="analysis", workdir=str(project)) as first,
            ManagedFixture(lab, name="simulation") as second,
        ):
            local_config = lab.root / "client.toml"
            local_config.write_text("version = 1\n")
            local_config.chmod(0o600)
            output, errors = Terminal(), Terminal()
            with (
                patch("sys.stdin", Terminal("6\n")),
                contextlib.redirect_stdout(output),
                contextlib.redirect_stderr(errors),
            ):
                assert (
                    cli_main(
                        [
                            "manage",
                            "destination",
                            "--ssh-config",
                            str(lab.config),
                            "--config",
                            str(local_config),
                            "--batch",
                        ]
                    )
                    == 0
                )
            menu = (
                (output.getvalue() + errors.getvalue())
                .replace("destination:", "workstation:")
                .replace(first.sid, "a" * 32)
                .replace(second.sid, "b" * 32)
            )
            assert "ready=2" in menu and "archived=0" in menu
            assert "1: Open/resume an existing server" in menu and "6: Exit management" in menu
            (output_dir / "session-menu.txt").write_text(menu.rstrip() + "\n")
            transport = SSHTransport("destination", config=lab.config, timeout=40)
            report = discover(transport)
            server = select_server(report, first.sid, interactive=False)
            with open_connection(transport, report, server) as (tunnel, login_url):
                base = f"http://127.0.0.1:{tunnel.local_port}{server['base_url']}"
                with first.client(base) as client:
                    session = client.post(
                        base + "api/sessions",
                        json={
                            "path": "first-notebook.ipynb",
                            "type": "notebook",
                            "name": "first-notebook",
                            "kernel": {"name": "python3"},
                        },
                        timeout=20,
                    )
                    session.raise_for_status()
                    kernel = session.json()["kernel"]["id"]
                    cookie = "; ".join(f"{item.name}={item.value}" for item in client.cookies)
                    observed = execute(base, "", kernel, CODE, cookie=cookie).strip()
                    assert observed == EXPECTED, "Unexpected notebook output"
                    notebook = {
                        "nbformat": 4,
                        "nbformat_minor": 5,
                        "metadata": {
                            "kernelspec": {
                                "name": "python3",
                                "display_name": "Python 3",
                                "language": "python",
                            }
                        },
                        "cells": [
                            {
                                "id": "welcome",
                                "cell_type": "markdown",
                                "metadata": {},
                                "source": "# Your computation lives here\n\nThe notebook and Python kernel run remotely. Your browser displays the results.",
                            },
                            {
                                "id": "continuity",
                                "cell_type": "code",
                                "metadata": {},
                                "source": CODE,
                                "execution_count": 1,
                                "outputs": [
                                    {
                                        "output_type": "stream",
                                        "name": "stdout",
                                        "text": observed + "\n",
                                    }
                                ],
                            },
                        ],
                    }
                    response = client.put(
                        base + "api/contents/first-notebook.ipynb",
                        json={"type": "notebook", "format": "json", "content": notebook},
                        timeout=10,
                    )
                    response.raise_for_status()
                profile = lab.root / "docs-chrome"
                browser = subprocess.Popen(
                    [
                        shutil.which("google-chrome"),
                        "--headless=new",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-background-networking",
                        "--disable-component-update",
                        "--disable-sync",
                        "--no-proxy-server",
                        "--remote-debugging-address=127.0.0.1",
                        "--remote-debugging-port=0",
                        f"--user-data-dir={profile}",
                        "about:blank",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                devtools = None
                try:
                    active = profile / "DevToolsActivePort"
                    deadline = time.monotonic() + 15
                    while not active.exists():
                        if browser.poll() is not None or time.monotonic() > deadline:
                            raise RuntimeError("Default-sandbox Chrome could not start")
                        time.sleep(0.1)
                    port = int(active.read_text().splitlines()[0])
                    with requests.Session() as client:
                        client.trust_env = False
                        pages = client.get(f"http://127.0.0.1:{port}/json", timeout=5).json()
                    devtools = DevTools(
                        next(
                            page["webSocketDebuggerUrl"] for page in pages if page["type"] == "page"
                        )
                    )
                    devtools.command(
                        "Emulation.setDeviceMetricsOverride",
                        {"width": 1120, "height": 520, "deviceScaleFactor": 1, "mobile": False},
                    )
                    devtools.command("Page.enable")
                    devtools.command("Page.navigate", {"url": login_url})
                    devtools.until("!!document.querySelector('input[name=password]')")
                    devtools.evaluate(
                        "document.querySelector('input[name=password]').value="
                        + json.dumps(first.password)
                        + ";document.querySelector('form').submit();true"
                    )
                    devtools.until("!!document.querySelector('.jp-LabShell')")
                    devtools.command(
                        "Page.navigate", {"url": base + "lab/tree/first-notebook.ipynb"}
                    )
                    devtools.until(
                        "!!document.querySelector('.jp-Notebook') && document.querySelector('.jp-Notebook').innerText.includes('45')"
                    )
                    time.sleep(2)
                    devtools.evaluate(
                        "Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'No')?.click(); document.activeElement?.blur(); true"
                    )
                    time.sleep(2)
                    screenshot = devtools.command("Page.captureScreenshot", {"format": "png"})
                    (output_dir / "first-notebook.png").write_bytes(
                        base64.b64decode(screenshot["data"])
                    )
                    history = devtools.command("Page.getNavigationHistory")
                    assert all("token=" not in entry["url"] for entry in history["entries"])
                    print(
                        "PASS: actual notebook result through fixture ProxyJump; screenshot contains no credential URL"
                    )
                    devtools.command(
                        "Emulation.setDeviceMetricsOverride",
                        {"width": 1200, "height": 630, "deviceScaleFactor": 1, "mobile": False},
                    )
                    devtools.command("Page.navigate", {"url": "about:blank"})
                    devtools.until("location.href === 'about:blank'")
                    card = """<!doctype html><html lang="en"><meta charset="utf-8"><title>JupyHop</title><style>*{box-sizing:border-box}body{margin:0;width:1200px;height:630px;padding:64px 76px;background:#f3f8f7;color:#163332;font-family:system-ui,sans-serif}.brand{color:#0b625f;font-size:32px;font-weight:750;letter-spacing:.02em}h1{font-size:62px;line-height:1.1;max-width:1000px;letter-spacing:-2px;margin:30px 0 22px}p{font-size:26px;margin:0 0 28px;color:#385653}pre{display:inline-block;border-radius:12px;padding:22px 30px;background:#123c3a;color:#f5fffd;font-size:30px;margin:0 0 30px}.footer{font-size:23px;color:#385653}</style><body><div class="brand">JupyHop</div><h1>Your remote notebooks.<br>Your local browser.</h1><p>Connect through the SSH access you already have.</p><pre>jupyhop open workstation</pre><div class="footer">Open · Start · Resume · Manage &nbsp; | &nbsp; Linux · MIT</div></body></html>"""
                    frame = devtools.command("Page.getFrameTree")["frameTree"]["frame"]["id"]
                    devtools.command("Page.setDocumentContent", {"frameId": frame, "html": card})
                    devtools.until(
                        "document.querySelector('h1')?.textContent.includes('Your remote notebooks')"
                    )
                    screenshot = devtools.command("Page.captureScreenshot", {"format": "png"})
                    (output_dir / "share-card.png").write_bytes(
                        base64.b64decode(screenshot["data"])
                    )
                    print("PASS: static 1200x630 share card rendered without external assets")
                finally:
                    if devtools is not None:
                        devtools.socket.close()
                    stop(browser)
    print("PASS: owned browser, tunnels, fixture servers and kernels cleaned")


if __name__ == "__main__":
    main()
