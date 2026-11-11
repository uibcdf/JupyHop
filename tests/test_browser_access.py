import concurrent.futures
import http.client
import re
import socket
import threading
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from jupyhop import handoff
from jupyhop.auth import NativeCookie
from jupyhop.errors import BrowserAccessError


def _cookie():
    return NativeCookie(
        ['username-127-0-0-1-12345="2|fixture"; HttpOnly; Path=/project/; SameSite=Lax'],
        12345,
        "/project/",
    )


def _details(exchange):
    path = Path(urlsplit(exchange.uri).path)
    page = path.read_text()
    port = int(re.search(r":(\d+)/handoff", page)[1])
    proof = re.search(r'name="proof" value="([^"]+)', page)[1]
    return path, port, proof


def _post(port, proof, *, headers=None, path="/handoff", method="POST"):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request(
            method,
            path,
            "proof=" + proof,
            {
                "Origin": "null",
                "Content-Type": "application/x-www-form-urlencoded",
                **(headers or {}),
            },
        )
        response = connection.getresponse()
        return response.status, response.headers.get("Set-Cookie")
    finally:
        connection.close()


@pytest.mark.parametrize(
    "field",
    [
        "Domain=127.0.0.1",
        "Path=/",
        "HttpOnly=false",
        "SameSite=None",
        "Max-Age=0",
        "Path=/project/",
        "Secure",
        "\r\nX-Injected: data",
    ],
)
def test_cookie_scope_and_ambiguous_headers_are_refused(field):
    with pytest.raises(ValueError):
        NativeCookie([_cookie().set_cookie + "; " + field], 12345, "/project/")
    assert "fixture" not in repr(_cookie())


def test_handoff_only_delivers_once_and_cleans_up():
    offered = threading.Event()
    cookie = _cookie()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        with handoff.prepare_handoff("http://127.0.0.1:12345/project/", cookie) as exchange:
            path, port, proof = _details(exchange)
            assert cookie.set_cookie not in path.read_text()
            assert path.stat().st_mode & 0o777 == 0o600
            assert path.parent.stat().st_mode & 0o777 == 0o700
            waiting = pool.submit(exchange.wait, None, fallback=offered.set)
            assert offered.wait(1)
            for kwargs in (
                {"method": "GET"},
                {"method": "HEAD"},
                {"path": "//handoff"},
                {"headers": {"Host": "example.org"}},
                {"headers": {"Origin": "https://example.org"}},
                {"headers": {"Transfer-Encoding": "chunked"}},
                {"headers": {"Content-Length": "1025", "Expect": "100-continue"}},
                {"headers": {"X-Large": "x" * 16384}},
            ):
                code, reply = _post(port, proof, **kwargs)
                assert code >= 400 and reply is None
            assert _post(port, proof + "&proof=" + proof) == (403, None)
            with socket.create_connection(("127.0.0.1", port), timeout=1) as duplicate:
                duplicate.sendall(b"POST /handoff HTTP/1.1\r\nOrigin: null\r\nOrigin: null\r\n\r\n")
                assert b"403" in duplicate.recv(512)
            requests = [pool.submit(_post, port, proof) for _ in range(2)]
            waiting.result(timeout=4)
        delivered = []
        for attempt in requests:
            try:
                delivered.append(attempt.result(timeout=4))
            except OSError:
                pass
            except http.client.RemoteDisconnected:
                pass
    assert delivered == [(303, cookie.set_cookie)]
    assert not path.exists() and not path.parent.exists()
    with pytest.raises(OSError):
        _post(port, proof)


def test_expiry_closes_even_with_slow_trickle(monkeypatch):
    monkeypatch.setattr(handoff, "LIFETIME", 0.3)
    with handoff.prepare_handoff("http://127.0.0.1:12345/project/", _cookie()) as exchange:
        path, port, _ = _details(exchange)
        with socket.create_connection(("127.0.0.1", port), timeout=1) as slow:
            slow.sendall(b"POST /handoff HTTP/1.1\r\nOrigin:")
            with pytest.raises(BrowserAccessError, match="expired"):
                exchange.wait(None, fallback=lambda: None)
    assert not path.exists()
    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", port), timeout=1)
