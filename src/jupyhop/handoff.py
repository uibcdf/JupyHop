"""A bounded one-use local POST that delivers a native Jupyter cookie."""

import base64
import hashlib
import html
import io
import math
import os
import re
import secrets
import shutil
import socket
import subprocess
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast
from urllib.parse import urlsplit

from jupyhop.auth import NativeCookie
from jupyhop.errors import BrowserAccessError

LIFETIME = 60
_HEADER_LIMIT = 16 * 1024
_BODY_LIMIT = 1024
_SUBMIT = "document.forms[0].submit()"


class _MalformedRequest(ValueError):
    pass


class _SocketReader(io.RawIOBase):
    def __init__(self, channel: socket.socket, deadline: float):
        self.channel = channel
        self.deadline = deadline

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: Any) -> int:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        self.channel.settimeout(min(2, remaining))
        return self.channel.recv_into(buffer)


class _HeaderReader(io.BufferedReader):
    remaining = _HEADER_LIMIT

    def readline(self, size: int | None = -1) -> bytes:
        limit = self.remaining + 1
        line = super().readline(limit if size is None or size < 0 else min(limit, size))
        self.remaining -= len(line)
        if self.remaining < 0 or (line and not line.endswith(b"\r\n")):
            raise _MalformedRequest
        return line


class _Handler(BaseHTTPRequestHandler):
    def setup(self) -> None:
        super().setup()
        self.rfile.close()
        self.deadline = min(time.monotonic() + 5, self.relay.deadline)
        self.rfile = _HeaderReader(_SocketReader(self.connection, self.deadline))

    @property
    def relay(self) -> "_Relay":
        return cast(_Relay, self.server)

    def handle(self) -> None:
        try:
            super().handle()
        except _MalformedRequest:
            self.request_version = "HTTP/1.0"
            self.requestline = ""
            self._respond(400)

    def log_message(self, format: str, *args: object) -> None:
        pass

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        self._respond(code)

    def _respond(self, status: int, *, deliver: bool = False) -> None:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            return
        self.connection.settimeout(min(2, remaining))
        self.send_response(status)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        if deliver:
            self.send_header("Set-Cookie", self.relay.cookie.set_cookie)
            self.send_header("Location", self.relay.destination)
        self.end_headers()
        if deliver:
            self.relay.delivered = True

    def do_POST(self) -> None:
        if (
            self.requestline.split() != ["POST", "/handoff", "HTTP/1.1"]
            or self.headers.defects
            or any(
                not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", key)
                or any(ord(c) < 32 and c != "\t" or ord(c) == 127 for c in value)
                for key, value in self.headers.raw_items()
            )
            or self.headers.get_all("Host") != [f"127.0.0.1:{self.relay.server_port}"]
            or self.headers.get_all("Origin") != ["null"]
            or self.headers.get_all("Content-Type") != ["application/x-www-form-urlencoded"]
            or "Transfer-Encoding" in self.headers
            or "Expect" in self.headers
        ):
            self._respond(403)
            return
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1 or re.fullmatch(r"[0-9]{1,4}", lengths[0]) is None:
            self._respond(400)
            return
        length = int(lengths[0])
        if not 0 < length <= _BODY_LIMIT:
            self._respond(413)
            return
        body = self.rfile.read(length)
        if not secrets.compare_digest(body, self.relay.body):
            self._respond(403)
            return
        if self.relay.used or time.monotonic() >= self.deadline:
            self._respond(410)
            return
        # HTTPServer handles one connection at a time. Consume before any bytes are sent.
        self.relay.used = True
        self._respond(303, deliver=True)


class _Relay(HTTPServer):
    request_queue_size = 4
    allow_reuse_address = False
    allow_reuse_port = False

    def __init__(self, destination: str, cookie: NativeCookie, proof: str):
        self.destination = destination
        self.cookie = cookie
        self.body = ("proof=" + proof).encode("ascii")
        self.deadline = 0.0
        self.used = False
        self.delivered = False
        super().__init__(("127.0.0.1", 0), _Handler)

    def handle_error(
        self, request: socket.socket | tuple[bytes, socket.socket], client_address: tuple[str, int]
    ) -> None:
        # A rejected or disconnected peer must not print headers or request bodies.
        pass


def launch_file(uri: str) -> subprocess.Popen[bytes] | None:
    launcher = shutil.which("xdg-open")
    if launcher is not None:
        try:
            return subprocess.Popen(
                [launcher, uri],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            pass
    return None


class Handoff:
    def __init__(self, relay: _Relay, uri: str):
        self._relay = relay
        self.uri = uri

    @property
    def seconds_left(self) -> int:
        return max(0, math.ceil(self._relay.deadline - time.monotonic()))

    def wait(
        self,
        launcher: subprocess.Popen[bytes] | None,
        *,
        fallback: Callable[[], None] | None,
        check_connection: Callable[[], None] | None = None,
    ) -> None:
        offered = False
        while not self._relay.used:
            if check_connection is not None:
                check_connection()
            remaining = self._relay.deadline - time.monotonic()
            if remaining <= 0:
                raise BrowserAccessError(
                    "The browser access link expired. Open the session again for a fresh link."
                )
            if not offered and (launcher is None or launcher.poll() not in (None, 0)):
                if fallback is None:
                    raise BrowserAccessError("The system browser could not open the access link.")
                fallback()
                offered = True
            self._relay.timeout = min(0.2, remaining)
            self._relay.handle_request()
        if not self._relay.delivered:
            raise BrowserAccessError(
                "The browser disconnected during access delivery. Open the session again."
            )


@contextmanager
def prepare_handoff(destination: str, cookie: NativeCookie) -> Iterator[Handoff]:
    proof = secrets.token_urlsafe(32)
    try:
        with (
            TemporaryDirectory(prefix="jupyhop-browser-") as root,
            _Relay(destination, cookie, proof) as relay,
        ):
            path = Path(root) / "open-jupyter.html"
            target = f"http://127.0.0.1:{relay.server_port}/handoff"
            endpoint = urlsplit(destination)
            forward = f"{endpoint.scheme}://{endpoint.netloc}"
            digest = base64.b64encode(hashlib.sha256(_SUBMIT.encode()).digest()).decode()
            # Browsers may apply form-action to the final 303 target as well.
            csp = f"default-src 'none'; script-src 'sha256-{digest}'; form-action {target} {forward}; base-uri 'none'"
            page = (
                '<!doctype html><meta charset="utf-8"><meta name="referrer" content="no-referrer">'
                f'<meta http-equiv="Content-Security-Policy" content="{html.escape(csp, quote=True)}">'
                f'<form method="post" action="{target}">'
                f'<input type="hidden" name="proof" value="{proof}"></form>'
                f"<script>{_SUBMIT}</script>"
            )
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "w", encoding="ascii") as stream:
                stream.write(page)
            relay.deadline = time.monotonic() + LIFETIME
            yield Handoff(relay, path.as_uri())
    except OSError:
        raise BrowserAccessError(
            "Could not create or serve the private browser access link."
        ) from None
