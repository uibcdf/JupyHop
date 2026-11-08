"""Optional real Chrome + JupyterLab login/HTTP/WebSocket acceptance via SSH jump.

Run `python -m experiments.browser_smoke`. Chrome runs with its default sandbox,
a private temporary profile and loopback DevTools. No real user profile is read.
Only synthetic fixture credentials are entered; CDP payloads are never printed.
"""

import json
import shutil
import subprocess
import time
import uuid

import requests
import websocket

from experiments.jupyter_fixture import JupyterFixture
from experiments.lab import SSHLab, stop
from jupyhop.discovery import discover, select_server
from jupyhop.opening import open_connection
from jupyhop.ssh import SSHTransport


class DevTools:
    def __init__(self, url):
        self.socket = websocket.create_connection(url, suppress_origin=True, timeout=20)
        self.number = 0

    def command(self, method, params=None):
        self.number += 1
        number = self.number
        self.socket.send(json.dumps({"id": number, "method": method, "params": params or {}}))
        while True:
            value = json.loads(self.socket.recv())
            if value.get("id") == number:
                if "error" in value:
                    raise RuntimeError("Browser DevTools command failed; payload suppressed")
                return value.get("result", {})

    def evaluate(self, expression):
        value = self.command(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        if "exceptionDetails" in value:
            raise RuntimeError("Browser evaluation failed; payload suppressed")
        return value.get("result", {}).get("value")

    def until(self, expression):
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            if self.evaluate(expression):
                return
            time.sleep(0.1)
        raise RuntimeError("Browser readiness timed out")


def main():
    binary = shutil.which("google-chrome") or shutil.which("chromium")
    if binary is None:
        raise RuntimeError("Install Chrome/Chromium for this optional browser experiment")
    with (
        SSHLab() as lab,
        JupyterFixture(lab.root / "browser-server", runtime=lab.runtime, lab=True) as fixture,
    ):
        transport = SSHTransport("destination", config=lab.config)
        report = discover(transport)
        server = select_server(report, None, interactive=False)
        with open_connection(transport, report, server) as (_, login_url):
            profile = lab.root / "chrome-profile"
            profile.mkdir(mode=0o700)
            browser = subprocess.Popen(
                [
                    binary,
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
                deadline = time.monotonic() + 10
                while not active.exists():
                    if browser.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError(
                            "Private headless Chrome could not start with its default sandbox"
                        )
                    time.sleep(0.1)
                port = int(active.read_text().splitlines()[0])
                with requests.Session() as client:
                    client.trust_env = False
                    pages = client.get(f"http://127.0.0.1:{port}/json", timeout=3).json()
                devtools = DevTools(
                    next(page["webSocketDebuggerUrl"] for page in pages if page["type"] == "page")
                )
                devtools.command("Page.enable")
                devtools.command("Page.navigate", {"url": login_url})
                devtools.until("!!document.querySelector('input[name=password]')")
                # Credentials go in the existing login form, never a URL/argv.
                devtools.evaluate(
                    "document.querySelector('input[name=password]').value = "
                    + json.dumps(fixture.info["token"])
                    + "; document.querySelector('form').submit(); true"
                )
                devtools.until(
                    "location.pathname === '/science/lab' && !!document.querySelector('.jp-LabShell')"
                )
                print("PASS: Chrome login form, cookie auth and JupyterLab shell through ProxyJump")
                kernel_id = devtools.evaluate("""(async () => {
                    const xsrf = decodeURIComponent(document.cookie.split('; ').find(c => c.startsWith('_xsrf=')).split('=').slice(1).join('='));
                    const r = await fetch('/science/api/kernels', {method:'POST', headers:{'Content-Type':'application/json', 'X-XSRFToken':xsrf}, body:JSON.stringify({name:'python3'})});
                    if (r.status !== 201) throw Error('fixture kernel');
                    return (await r.json()).id;
                })()""")
                message_id = uuid.uuid4().hex
                code = """new Promise((resolve, reject) => {
                    const ws = new WebSocket('ws://' + location.host + '/science/api/kernels/' + KERNEL + '/channels?session_id=browser-fixture');
                    const timer = setTimeout(() => { ws.close(); reject(Error('timeout')); }, 15000);
                    let output = '';
                    ws.onopen = () => ws.send(JSON.stringify({header:{msg_id:MESSAGE,msg_type:'execute_request',username:'fixture',session:'browser-fixture',date:new Date().toISOString(),version:'5.3'},parent_header:{},metadata:{},channel:'shell',content:{code:'print(6 * 7)',silent:false,store_history:false,user_expressions:{},allow_stdin:false,stop_on_error:true}}));
                    ws.onmessage = e => { const m=JSON.parse(e.data); if(m.parent_header.msg_id !== MESSAGE) return;
                        if(m.msg_type === 'stream') output += m.content.text;
                        if(m.msg_type === 'status' && m.content.execution_state === 'idle') { clearTimeout(timer); ws.close(); resolve(output.trim()); }
                    };
                    ws.onerror = () => { clearTimeout(timer); reject(Error('websocket')); };
                })""".replace("KERNEL", json.dumps(kernel_id)).replace(
                    "MESSAGE", json.dumps(message_id)
                )
                if devtools.evaluate(code) != "42":
                    raise RuntimeError("Browser WebSocket kernel result differs")
                print("PASS: browser-authenticated kernel WebSocket execution returns 42")
                history = devtools.command("Page.getNavigationHistory")
                if any("token=" in entry["url"] for entry in history["entries"]):
                    raise RuntimeError("Sensitive query appeared in fixture browser history")
                print("PASS: browser navigation history contains no token query")
            finally:
                if devtools is not None:
                    devtools.socket.close()
                stop(browser)
    print("Browser acceptance complete; fixture server, kernel, tunnel and profile cleaned")


if __name__ == "__main__":
    main()
