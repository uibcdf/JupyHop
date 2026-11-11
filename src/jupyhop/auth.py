"""Private managed browser access. Public reports never receive cookie fields."""

import http.client
import json
import re
import time
from dataclasses import dataclass
from http.cookies import CookieError, SimpleCookie
from importlib.resources import files
from typing import Any, NoReturn
from urllib.parse import urlencode

from jupyhop._auth_remote import AUTH_ERRORS, AUTH_LIMIT, AUTH_MODES, AUTH_PROTOCOL
from jupyhop._discovery_probe import _Connection
from jupyhop._native_cookie import login_path, native_cookie
from jupyhop.discovery import ProbeConnection, validate_python
from jupyhop.errors import (
    BrowserAccessError,
    DiscoveryError,
    PrerequisiteError,
    ProtocolError,
    SelectionError,
)
from jupyhop.protocol import _integer, _invalid_constant, _text, _unique_object, parse_discovery
from jupyhop.selection import validate_name
from jupyhop.ssh import STDIN_LIMIT, ssh_failure

_SERVER_FIELDS = {
    "id",
    "observed_id",
    "name",
    "origin",
    "state",
    "reason",
    "pid",
    "port",
    "address",
    "base_url",
    "version",
    "sources",
}


class NativeCookie:
    __slots__ = ("set_cookie", "request_cookie")

    def __init__(self, headers: list[str], port: int, base: str):
        self.set_cookie, self.request_cookie = native_cookie(headers, port, base)

    def __repr__(self) -> str:
        return "<NativeCookie redacted>"


@dataclass(frozen=True)
class AuthObservation:
    identity: dict[str, Any]
    server: dict[str, Any]
    mode: str
    context: dict[str, str]
    cookie: NativeCookie | None


def _refusal(error: str) -> NoReturn:
    if error == "name_not_found":
        raise SelectionError("Managed name not found. Check jupyhop status for current names.")
    if error in {"not_managed", "not_ready"}:
        raise DiscoveryError(
            "Selected managed session could not be verified as ready. Check jupyhop status before retrying."
        )
    if error in {"credential_unavailable", "native_login_failed", "budget_exceeded"}:
        raise BrowserAccessError(f"Automatic Jupyter access could not be prepared ({error}).")
    raise ProtocolError(
        f"Managed browser access was refused ({error}). Check jupyhop status and the remote environment."
    )


def _parse(raw: bytes, request: dict[str, Any]) -> AuthObservation:
    try:
        if len(raw) > AUTH_LIMIT:
            raise ValueError
        envelope = json.loads(
            raw.decode(), object_pairs_hook=_unique_object, parse_constant=_invalid_constant
        )
        version = envelope["protocol"]
        data = envelope["data"]
        if (
            set(envelope) != {"protocol", "operation", "data"}
            or version != AUTH_PROTOCOL
            or any(type(v) is not int for v in version.values())
            or envelope["operation"] != "browser_auth"
            or set(data) != {"id", "identity", "auth_mode", "context", "server", "cookie", "error"}
        ):
            raise ValueError
        error = data["error"]
        identity = data["identity"]
        if identity is not None:
            if set(identity) != {"uid", "user", "scope"} or not re.fullmatch(
                r"[a-f0-9]{24}", _text(identity["scope"])
            ):
                raise ValueError
            _integer(identity["uid"])
            _text(identity["user"])
        expected = request["expected_identity"]
        if error is not None and error != "manual_required":
            if error not in AUTH_ERRORS or any(
                data[k] is not None for k in ("context", "auth_mode", "server", "cookie")
            ):
                raise ValueError
            if (
                error != "target_changed"
                and expected is not None
                and identity not in (None, expected)
            ):
                raise ValueError
            _refusal(error)
        sid, mode, context, server = (data[k] for k in ("id", "auth_mode", "context", "server"))
        if (
            not re.fullmatch(r"[a-f0-9]{32}", sid)
            or ("id" in request and sid != request["id"])
            or identity is None
            or (expected is not None and identity != expected)
            or mode not in AUTH_MODES
            or set(context) != {"name", "project_display", "python_display"}
            or set(server) != _SERVER_FIELDS
        ):
            raise ValueError
        if (
            validate_name(context["name"]) != server["name"]
            or ("name" in request and context["name"] != request["name"])
            or any(
                len(_text(context[k]).encode()) > 256 for k in ("project_display", "python_display")
            )
        ):
            raise ValueError
        # Only the nonsecret candidate goes through the discovery validator.
        checked = parse_discovery(
            json.dumps(
                {
                    "protocol": version,
                    "operation": "discover",
                    "data": {
                        "identity": identity,
                        "complete": False,
                        "issues": [],
                        "servers": [server],
                        "paths": [
                            {"path": path, "status": "ok", "source": "managed"}
                            for path in server["sources"]
                        ],
                    },
                }
            ).encode()
        )["data"]["servers"][0]
        if (
            checked["id"] != sid
            or checked["origin"] != "managed"
            or checked["state"] != "ready"
            or checked["base_url"] != f"/jupyhop/{sid}/"
            or len(checked["sources"]) != 1
        ):
            raise ValueError
        cookie = None
        if request["action"] == "cookie" and checked["observed_id"] != request["observed_id"]:
            raise ValueError
        if request["action"] == "cookie" and mode == "token":
            if error is not None or not isinstance(data["cookie"], str):
                raise ValueError
            cookie = NativeCookie([data["cookie"]], request["local_port"], checked["base_url"])
        elif data["cookie"] is not None or error != (
            "manual_required" if request["action"] == "cookie" else None
        ):
            raise ValueError
        return AuthObservation(identity, checked, mode, context, cookie)
    except (
        KeyError,
        TypeError,
        ValueError,
        UnicodeError,
        AttributeError,
        RecursionError,
        CookieError,
    ):
        raise ProtocolError(
            "Invalid private browser-access response. Check jupyhop status and retry."
        ) from None


def observe(
    connection: ProbeConnection,
    python: str,
    timeout: float,
    *,
    identifier: str | None = None,
    name: str | None = None,
    identity: dict[str, Any] | None = None,
    observed_id: str | None = None,
    local_port: int | None = None,
) -> AuthObservation:
    request: dict[str, Any] = {
        "protocol": AUTH_PROTOCOL,
        "operation": "browser_auth",
        "action": "inspect",
        "expected_identity": identity,
        "budget": min(5, max(0.1, timeout - 1)),
    }
    if identifier is not None and name is None and re.fullmatch(r"[a-f0-9]{32}", identifier):
        request["id"] = identifier
    elif name is not None and identifier is None:
        request["name"] = validate_name(name)
    else:
        raise ValueError("Use one exact managed UUID or name for browser access.")
    if local_port is not None:
        if (
            identifier is None
            or identity is None
            or observed_id is None
            or not re.fullmatch(r"[a-f0-9]{24}", observed_id)
            or type(local_port) is not int
            or not 1 <= local_port <= 65535
        ):
            raise ValueError("Cookie issuance requires a verified managed target and local port.")
        request.update(action="cookie", local_port=local_port, observed_id=observed_id)
    source = (
        b"\n".join(
            files("jupyhop").joinpath(part).read_bytes()
            for part in (
                "_managed_remote.py",
                "_discovery_probe.py",
                "_native_cookie.py",
                "_auth_remote.py",
            )
        )
        + b"\nauth_main(sys.argv[1].encode())\n"
    )
    # A shared source namespace avoids invoking the discovery entry point.
    bootstrap = "import sys; exec(compile(sys.stdin.buffer.read(),'<jupyhop-auth>','exec'), {'__name__':'jupyhop_remote','sys':sys})"
    if len(source) > STDIN_LIMIT:
        raise ProtocolError("Private browser-access source exceeds its SSH size limit.")
    result = connection.run(
        [validate_python(python), "-I", "-B", "-c", bootstrap, json.dumps(request)], stdin=source
    )
    if result.returncode == 255:
        raise ssh_failure(result.stderr)
    if result.returncode:
        raise PrerequisiteError(
            "Private browser access needs an existing Linux Python >=3.11. Check --remote-python."
        )
    return _parse(result.stdout, request)


def password_cookie(port: int, base: str, password: str) -> NativeCookie:
    connection = _Connection("127.0.0.1", port, timeout=1)
    connection.deadline = time.monotonic() + 5
    try:
        connection.request("GET", login_path(base), headers={"Connection": "close"})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError
        xsrf = SimpleCookie()
        headers = [h for h in response.headers.get_all("Set-Cookie", []) if h.startswith("_xsrf=")]
        if len(headers) != 1 or len(headers[0]) > 4096:
            raise ValueError
        xsrf.load(headers[0])
        if set(xsrf) != {"_xsrf"} or not xsrf["_xsrf"].value:
            raise ValueError
        response.close()
        connection.close()
        connection.request(
            "POST",
            login_path(base),
            urlencode({"_xsrf": xsrf["_xsrf"].value, "password": password}),
            {
                "Cookie": "_xsrf=" + xsrf["_xsrf"].coded_value,
                "Content-Type": "application/x-www-form-urlencoded",
                "Connection": "close",
            },
        )
        response = connection.getresponse()
        if response.status != 302 or response.headers.get_all("Location") != [base]:
            raise ValueError
        return NativeCookie(response.headers.get_all("Set-Cookie", []), port, base)
    except (OSError, http.client.HTTPException, CookieError, ValueError):
        raise BrowserAccessError(
            "Jupyter did not issue a cookie for the supplied password."
        ) from None
    finally:
        connection.close()


def verify_cookie(port: int, base: str, cookie: NativeCookie) -> None:
    connection = _Connection("127.0.0.1", port, timeout=1)
    try:
        connection.request(
            "GET",
            base + "api/sessions",
            headers={"Cookie": cookie.request_cookie, "Connection": "close"},
        )
        if connection.getresponse().status == 200:
            return
    except (OSError, http.client.HTTPException, ValueError):
        pass
    finally:
        connection.close()
    raise BrowserAccessError("Jupyter refused the cookie through the verified SSH forward.")
