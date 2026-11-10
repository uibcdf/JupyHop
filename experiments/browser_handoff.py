"""0.4 design spike: native Jupyter cookie handoff, not a product auth feature.

Run with the experiments dependencies and Chrome installed. Only SSHLab targets,
synthetic credentials and private browser profiles are used. Native token reads
are scoped to a known fixture runtime file over the selected SSH connection; no production credential protocol or managed-auth mode is added.
Use --remote-cookie to issue the native cookie remotely for the local forwarding
Host; the native token then stays out of the SSH reply. The default retains the
original comparison experiment. Neither path is a production credential API.
No real SSH configuration, browser profile or scientific session is accessed.
"""

import argparse
import html
import json
import os
import re
import secrets
import shutil
import subprocess
import threading
import time
from contextlib import contextmanager
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs, urlsplit

import requests

from experiments.browser_smoke import DevTools
from experiments.jupyter_fixture import JupyterFixture
from experiments.lab import SSHLab, stop
from experiments.m4_reconnect import independent_client
from experiments.managed_fixture import ManagedFixture
from jupyhop.discovery import discover, select_server
from jupyhop.opening import open_connection
from jupyhop.ssh import SSHTransport


@contextmanager
def chrome(root):
    binary = shutil.which("google-chrome") or shutil.which("chromium")
    if binary is None:
        raise RuntimeError("This optional spike requires Chrome/Chromium")
    profile = root / "browser"
    process = subprocess.Popen(
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
        deadline = time.monotonic() + 15
        while not active.exists():
            if process.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError("Private Chrome with its default sandbox could not start")
            time.sleep(0.1)
        port = int(active.read_text().splitlines()[0])
        with requests.Session() as client:
            client.trust_env = False
            pages = client.get(f"http://127.0.0.1:{port}/json", timeout=5).json()
        devtools = DevTools(next(p["webSocketDebuggerUrl"] for p in pages if p["type"] == "page"))
        devtools.command("Page.enable")
        yield devtools
    finally:
        if devtools is not None:
            devtools.socket.close()
        stop(process)
        shutil.rmtree(profile, ignore_errors=True)


def fixture_token(tunnel, fixture, report, server, *, local_port=None):
    """Exercise a private SSH read on one known fixture, not general discovery."""
    request = {
        "source": files("jupyhop").joinpath("_discovery_probe.py").read_text(),
        "directory": str(fixture.record.parent),
        "name": fixture.record.name,
        "scope": report["identity"]["scope"],
        "expected": server.get("observed_id", server["id"]),
        "local_port": local_port,
    }
    bootstrap = r"""import json, os, sys
try:
    request = json.load(sys.stdin)
    namespace = {'__name__': 'fixture_handoff_probe'}
    exec(compile(request['source'], '<fixture-handoff-probe>', 'exec'), namespace)
    directory = namespace['_directory'](request['directory'])
    try:
        def checked():
            result = namespace['_candidate'](directory, request['name'], request['directory'], request['scope'])
            if result['state'] != 'ready' or result['id'] != request['expected']:
                raise ValueError
            return result
        checked()
        value = namespace['_read_record'](directory, request['name'])
        credential = value.get('token')
        if not isinstance(credential,str) or not 1 <= len(credential) <= 4096 or any(ord(c)<33 or ord(c)>126 for c in credential):
            raise ValueError
        current = checked()
        port = request['local_port']
        if port is None:
            print(json.dumps({'token': credential}))
        else:
            if type(port) is not int or not 1 <= port <= 65535:
                raise ValueError
            import http.client
            from urllib.parse import quote
            connection = http.client.HTTPConnection('127.0.0.1', current['port'], timeout=3)
            try:
                base = current['base_url']
                connection.request('GET', base+'login?next='+quote(base,safe=''), headers={'Host':'127.0.0.1:'+str(port), 'Authorization':'token '+credential})
                response = connection.getresponse()
                if response.status != 302:
                    raise ValueError
                cookies = [v for k,v in response.getheaders() if k.lower() == 'set-cookie']
                if not cookies or sum(map(len,cookies)) > 4096:
                    raise ValueError
                checked()
                print(json.dumps({'cookies': cookies}))
            finally:
                connection.close()
    finally:
        os.close(directory)
except Exception:
    print(json.dumps({'error':'fixture_credential_unavailable'}))
    sys.exit(1)
"""
    result = tunnel.run(
        ["python3", "-I", "-B", "-c", bootstrap], stdin=json.dumps(request).encode()
    )
    if result.returncode or len(result.stdout) > 8192:
        raise RuntimeError("Private fixture credential read refused; raw output suppressed")
    value = json.loads(result.stdout)
    if local_port is not None:
        if set(value) != {"cookies"} or not isinstance(value["cookies"], list):
            raise RuntimeError("Private fixture cookie response invalid; raw output suppressed")
        assert fixture.info["token"].encode() not in result.stdout
        return value["cookies"]
    if set(value) != {"token"} or not isinstance(value["token"], str):
        raise RuntimeError("Private fixture credential response invalid; raw output suppressed")
    return value["token"]


def cookie_headers(base, credential, *, password):
    """Let native Jupyter authenticate and issue its own cookie; never forge one."""
    with requests.Session() as client:
        client.trust_env = False
        if password:
            client.get(base + "login", timeout=5)
            response = client.post(
                base + "login",
                data={"_xsrf": client.cookies.get("_xsrf"), "password": credential},
                allow_redirects=False,
                timeout=5,
            )
        else:
            response = client.get(
                base + "login",
                headers={"Authorization": "token " + credential},
                allow_redirects=False,
                timeout=5,
            )
        assert response.status_code == 302, "Native Jupyter login did not confirm authentication"
        expected = re.sub(r"[^a-zA-Z0-9]", "-", "username-" + urlsplit(base).netloc)
        headers = []
        for value in response.raw.headers.getlist("Set-Cookie"):
            parsed = SimpleCookie()
            parsed.load(value)
            if expected in parsed:
                cookie = parsed[expected]
                assert cookie["httponly"] and not cookie["domain"]
                assert cookie["path"] == urlsplit(base).path
                headers.append(value)
        assert len(headers) == 1, "Unexpected native authentication cookie"
        # No Authorization header on this request: it must use the issued cookie.
        assert client.get(base + "api/sessions", timeout=5).status_code == 200
        return headers


@contextmanager
def handoff(root, base, cookies):
    """Narrow POST-only one-use relay; HTTP/WebSockets stay in OpenSSH's tunnel."""
    proof = secrets.token_urlsafe(32)
    state = {"used": False, "deadline": time.monotonic() + 60}
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log request headers, bodies, paths or cookies.

        def reject(self, code):
            self.send_response(code)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            self.reject(405)

        def do_POST(self):
            if (
                self.path != "/handoff"
                or self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}"
                or self.headers.get("Origin") != "null"
                or self.headers.get_content_type() != "application/x-www-form-urlencoded"
            ):
                self.reject(403)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 4096:
                    self.reject(413)
                    return
                body = parse_qs(self.rfile.read(length).decode("ascii"), strict_parsing=True)
                supplied = body.get("proof", [""])
                valid = set(body) == {"proof"} and len(supplied) == 1
                valid = valid and secrets.compare_digest(supplied[0], proof)
            except (ValueError, UnicodeError):
                valid = False
            if not valid:
                self.reject(403)
                return
            with lock:
                if state["used"] or time.monotonic() >= state["deadline"]:
                    self.reject(410)
                    return
                state["used"] = True
            self.send_response(303)
            for value in cookies:
                self.send_header("Set-Cookie", value)
            self.send_header("Location", base + "lab")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Length", "0")
            self.end_headers()
            launch.unlink(missing_ok=True)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    target = f"http://127.0.0.1:{server.server_port}/handoff"
    launch = root / "launch.html"
    page = (
        '<!doctype html><meta charset="utf-8"><meta name="referrer" content="no-referrer">'
        f'<form method="post" action="{html.escape(target, quote=True)}">'
        f'<input type="hidden" name="proof" value="{proof}"></form>'
        "<script>document.forms[0].submit()</script>"
    )
    descriptor = os.open(launch, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(page)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield launch, target, proof, state
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
        launch.unlink(missing_ok=True)


def negative_checks(target, proof):
    with requests.Session() as client:
        client.trust_env = False
        attempts = [
            client.get(target, timeout=5),
            client.post(target, data={"proof": "invalid"}, headers={"Origin": "null"}, timeout=5),
            client.post(
                target, data={"proof": proof}, headers={"Origin": "https://example.org"}, timeout=5
            ),
            client.post(
                target,
                data={"proof": proof},
                headers={"Origin": "null", "Host": "example.org"},
                timeout=5,
            ),
        ]
    assert [r.status_code for r in attempts] == [405, 403, 403, 403]
    assert all("Set-Cookie" not in r.headers for r in attempts)


def kernel_roundtrip(devtools, base, *, create):
    code = "handoff_marker=42;print(handoff_marker)" if create else "print(handoff_marker)"
    script = r"""(async () => {
        const xsrf = decodeURIComponent(document.cookie.split('; ').find(c => c.startsWith('_xsrf=')).split('=').slice(1).join('='));
        let session;
        if (CREATE) {
            const r = await fetch(BASE+'api/sessions', {method:'POST',headers:{'Content-Type':'application/json','X-XSRFToken':xsrf},body:JSON.stringify({path:'handoff.ipynb',type:'notebook',name:'handoff',kernel:{name:'python3'}})});
            if (r.status !== 201) throw Error('fixture session creation failed');
            session = await r.json();
        } else {
            const r = await fetch(BASE+'api/sessions');
            if (r.status !== 200) throw Error('fixture session lookup failed');
            session = (await r.json()).find(s => s.path === 'handoff.ipynb');
        }
        const output = await new Promise((resolve,reject) => {
            const ws = new WebSocket('ws://'+location.host+BASE+'api/kernels/'+session.kernel.id+'/channels?session_id=handoff-spike');
            let text='';const timer=setTimeout(()=>{ws.close();reject(Error('timeout'));},15000);
            ws.onopen=()=>ws.send(JSON.stringify({header:{msg_id:'handoff-message',msg_type:'execute_request',username:'fixture',session:'handoff-spike',date:new Date().toISOString(),version:'5.3'},parent_header:{},metadata:{},channel:'shell',content:{code:CODE,silent:false,store_history:false,user_expressions:{},allow_stdin:false,stop_on_error:true}}));
            ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.parent_header.msg_id!=='handoff-message')return;if(m.msg_type==='stream')text+=m.content.text;if(m.msg_type==='status'&&m.content.execution_state==='idle'){clearTimeout(timer);ws.close();resolve(text.trim());}};
            ws.onerror=()=>{clearTimeout(timer);reject(Error('websocket'));};
        });
        return {kernel:session.kernel.id,session:session.id,output};
    })()"""
    return devtools.evaluate(
        script.replace("CREATE", json.dumps(create))
        .replace("BASE", json.dumps(urlsplit(base).path))
        .replace("CODE", json.dumps(code))
    )


def visit(lab, transport, fixture, label, *, create=False, password=False, remote_cookie=False):
    report = discover(transport)
    server = select_server(report, None, interactive=False)
    with open_connection(transport, report, server) as (tunnel, _):
        base = f"http://127.0.0.1:{tunnel.local_port}{server['base_url']}"
        if create and not password:
            wrong = dict(server, observed_id="f" * 24)
            refused = False
            try:
                fixture_token(tunnel, fixture, report, wrong)
            except RuntimeError:
                refused = True
            assert refused, "Wrong selected identity must not release a credential"
            original_mode = fixture.record.stat().st_mode & 0o777
            try:
                fixture.record.chmod(0o644)
                refused = False
                try:
                    fixture_token(tunnel, fixture, report, server)
                except RuntimeError:
                    refused = True
                assert refused, "Nonprivate runtime metadata must not release a credential"
            finally:
                fixture.record.chmod(original_mode)
        if remote_cookie and not password:
            cookies = fixture_token(tunnel, fixture, report, server, local_port=tunnel.local_port)
            credential = fixture.info["token"]  # Leak-check marker held only by the test harness.
            expected = re.sub(r"[^a-zA-Z0-9]", "-", "username-" + urlsplit(base).netloc)
            parsed = SimpleCookie()
            for header in cookies:
                parsed.load(header)
            assert expected in parsed and parsed[expected]["httponly"]
            assert (
                parsed[expected]["path"] == urlsplit(base).path and not parsed[expected]["domain"]
            )
            with requests.Session() as client:
                client.trust_env = False
                response = client.get(
                    base + "api/sessions",
                    headers={"Cookie": expected + "=" + parsed[expected].coded_value},
                    timeout=5,
                )
                assert response.status_code == 200
        else:
            credential = (
                fixture.password if password else fixture_token(tunnel, fixture, report, server)
            )
            assert credential
            cookies = cookie_headers(base, credential, password=password)
        root = lab.root / label
        root.mkdir(mode=0o700)
        with handoff(root, base, cookies) as (launch, target, proof, state):
            negative_checks(target, proof)
            assert credential not in launch.read_text()
            assert launch.stat().st_mode & 0o777 == 0o600
            with chrome(root) as devtools:
                devtools.command("Page.navigate", {"url": launch.as_uri()})
                devtools.until("!!document.querySelector('.jp-LabShell')")
                assert state["used"] and not launch.exists()
                history = devtools.command("Page.getNavigationHistory")
                assert all(
                    "token=" not in e["url"]
                    and proof not in e["url"]
                    and credential not in e["url"]
                    for e in history["entries"]
                )
                result = kernel_roundtrip(devtools, base, create=create)
                assert result["output"] == "42"
            with requests.Session() as client:
                client.trust_env = False
                replay = client.post(
                    target,
                    data={"proof": proof},
                    headers={"Origin": "null"},
                    allow_redirects=False,
                    timeout=5,
                )
            assert replay.status_code == 410 and "Set-Cookie" not in replay.headers
        with handoff(root, base, cookies) as (_, target, proof, state):
            state["deadline"] = time.monotonic() - 1
            with requests.Session() as client:
                client.trust_env = False
                expired = client.post(
                    target,
                    data={"proof": proof},
                    headers={"Origin": "null"},
                    allow_redirects=False,
                    timeout=5,
                )
            assert expired.status_code == 410 and "Set-Cookie" not in expired.headers
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--remote-cookie",
        action="store_true",
        help="Mint the native cookie remotely; do not return the runtime token over SSH.",
    )
    args = parser.parse_args()
    with SSHLab() as lab:
        with JupyterFixture(lab.root / "native-token", runtime=lab.runtime, lab=True) as fixture:
            first = visit(
                lab,
                SSHTransport("destination", config=lab.config),
                fixture,
                "first",
                create=True,
                remote_cookie=args.remote_cookie,
            )
            config = independent_client(lab, "second-client", jump=False)
            second = visit(
                lab,
                SSHTransport("remote", config=config),
                fixture,
                "second",
                remote_cookie=args.remote_cookie,
            )
            assert first["kernel"] == second["kernel"] and first["session"] == second["session"]
            print(
                "PASS: native token -> Jupyter-issued cookie -> private-file POST -> browser/HTTP/WebSocket, no browser login prompt"
            )
            print(
                "PASS: fresh key/config/profile after all first-client connections close; same live kernel, session and memory"
            )
        with ManagedFixture(lab, name="legacy-password") as fixture:
            visit(
                lab,
                SSHTransport("destination", config=lab.config),
                fixture,
                "legacy",
                create=True,
                password=True,
            )
            print(
                "PASS: existing 0.3 managed password -> native login cookie -> browser handoff; password still required once"
            )
    if args.remote_cookie:
        print(
            "PASS: native cookie issued on the remote side for the local forwarding Host; no runtime token in either SSH reply"
        )
    print(
        "PASS: GET/invalid proof/origin/host refused; replay and expired proof refused; no secret URL history"
    )
    print(
        "All disposable brokers, browsers, SSH/Jupyter fixtures and kernels cleaned; production credential protocol and managed-auth mode are not implemented"
    )


if __name__ == "__main__":
    main()
