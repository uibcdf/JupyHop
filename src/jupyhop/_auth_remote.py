"""Selected managed server observation and native cookie issuance over SSH."""

from typing import TYPE_CHECKING

if TYPE_CHECKING or __name__ == "jupyhop._auth_remote":
    import http.client
    import json
    import os
    import pwd
    import re
    import signal
    from typing import Any

    from jupyhop._discovery_probe import (
        Deadline,
        Unsupported,
        _candidate,
        _Connection,
        _deadline,
        _digest,
        _json,
        _read_record,
        listener_inode,
    )
    from jupyhop._managed_remote import (
        _NAME,
        _SID,
        ManagedProblem,
        Registry,
        _load,
        _private_dir,
        boot_id,
        mark_managed,
        runner_matches,
        settings_mode,
    )
    from jupyhop._native_cookie import login_path, native_cookie

AUTH_PROTOCOL = {"major": 1, "minor": 7}
AUTH_MODES = ("token", "password", "legacy-password")
AUTH_ERRORS = {
    "invalid_request",
    "not_managed",
    "name_not_found",
    "not_ready",
    "manual_required",
    "target_changed",
    "unsafe_state",
    "corrupt_state",
    "incompatible_registry",
    "incompatible_settings",
    "credential_unavailable",
    "native_login_failed",
    "response_limit",
    "budget_exceeded",
}
AUTH_LIMIT = 16 * 1024


def _auth_request(request: dict[str, Any]) -> None:
    action = request.get("action")
    required = {"protocol", "operation", "action", "expected_identity", "budget"}
    if action == "inspect":
        required.add("id" if "id" in request else "name")
    elif action == "cookie":
        required.update({"id", "observed_id", "local_port"})
    else:
        raise ManagedProblem("invalid_request")
    protocol = request.get("protocol")
    budget: Any = request.get("budget")
    if (
        set(request) != required
        or protocol != AUTH_PROTOCOL
        or any(type(v) is not int for v in protocol.values())
        or request["operation"] != "browser_auth"
        or type(budget) not in (int, float)
        or not 0.1 <= budget <= 10
    ):
        raise ManagedProblem("invalid_request")
    for key, pattern in (
        ("id", _SID),
        ("name", _NAME),
        ("observed_id", re.compile(r"[a-f0-9]{24}")),
    ):
        if key in request and (
            not isinstance(request[key], str) or not pattern.fullmatch(request[key])
        ):
            raise ManagedProblem("invalid_request")
    if action == "cookie" and (
        request["expected_identity"] is None
        or type(request["local_port"]) is not int
        or not 1 <= request["local_port"] <= 65535
    ):
        raise ManagedProblem("invalid_request")


def _auth_display(path: str) -> str:
    # Display only. Keep terminal controls and filesystem surrogates out of the reply.
    path = "".join(c if c.isprintable() else "?" for c in path)
    encoded = path.encode()
    return path if len(encoded) <= 256 else "…" + encoded[-253:].decode(errors="ignore")


def _auth_issue(record: dict[str, Any], token: str, port: int) -> str:
    base = record["base_url"]
    connection = _Connection("127.0.0.1", record["port"], timeout=1)
    try:
        connection.connect()
        if (
            not runner_matches(record)
            or listener_inode(record["pid"], record["port"]) != record["socket_inode"]
        ):
            raise ManagedProblem("target_changed")
        connection.request(
            "GET",
            login_path(base),
            headers={
                "Host": f"127.0.0.1:{port}",
                "Authorization": "token " + token,
                "Connection": "close",
            },
        )
        response = connection.getresponse()
        if response.status != 302 or response.headers.get_all("Location") != [base]:
            raise ManagedProblem("native_login_failed")
        header, _ = native_cookie(response.headers.get_all("Set-Cookie", []), port, base)
        return header
    except (http.client.HTTPException, TimeoutError, ConnectionError, ValueError):
        raise ManagedProblem("native_login_failed") from None
    finally:
        connection.close()


def _auth_observe(request: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    try:
        with Registry() as registry:
            registry.header()
            if "name" in request:
                matches = [r for r in registry.records() if r["name"] == request["name"]]
                if len(matches) != 1:
                    raise ManagedProblem("name_not_found" if not matches else "corrupt_state")
                record = matches[0]
            else:
                record = registry.record(request["id"])
            sid = record["id"]
            if record["state"] != "ready" or record.get("stop_requested"):
                raise ManagedProblem("not_ready")
            with registry.session(sid) as directory:
                mode = settings_mode(_load(directory, "settings.json"))
            runtime = _private_dir(record["runtime"])
            try:
                filename = f"jpserver-{record['pid']}.json"
                metadata = (
                    _read_record(runtime, filename) if request["action"] == "cookie" else None
                )
                server = mark_managed(
                    _candidate(
                        runtime, filename, record["runtime"], identity["scope"], metadata=metadata
                    ),
                    [record],
                )
                if server["state"] != "ready" or server["origin"] != "managed":
                    raise ManagedProblem("not_ready")
                cookie, error = None, None
                if request["action"] == "cookie":
                    if request["observed_id"] != server["observed_id"]:
                        raise ManagedProblem("target_changed")
                    if mode != "token":
                        error = "manual_required"
                    else:
                        assert metadata is not None
                        token = metadata.get("token")
                        if (
                            not isinstance(token, str)
                            or re.fullmatch(r"[a-f0-9]{64}", token) is None
                        ):
                            raise ManagedProblem("credential_unavailable")
                        cookie = _auth_issue(record, token, request["local_port"])
                        if token in cookie:
                            raise ManagedProblem("native_login_failed")
                    if (
                        registry.record(sid) != record
                        or not runner_matches(record)
                        or listener_inode(record["pid"], record["port"]) != record["socket_inode"]
                    ):
                        raise ManagedProblem("target_changed")
            finally:
                os.close(runtime)
            return {
                "id": sid,
                "identity": identity,
                "auth_mode": mode,
                "context": {
                    "name": record["name"],
                    "project_display": _auth_display(record["workdir"]),
                    "python_display": _auth_display(record["server_python"]),
                },
                "server": server,
                "cookie": cookie,
                "error": error,
            }
    except FileNotFoundError:
        raise ManagedProblem("name_not_found" if "name" in request else "not_managed") from None


def auth_main(raw: bytes) -> None:
    data: dict[str, Any] = dict.fromkeys(
        ("id", "identity", "auth_mode", "context", "server", "cookie", "error")
    )
    try:
        request = _json(raw)
        _auth_request(request)
        signal.signal(signal.SIGALRM, _deadline)
        signal.setitimer(signal.ITIMER_REAL, request["budget"])
        uid = os.getuid()
        identity = {"uid": uid, "user": pwd.getpwuid(uid).pw_name, "scope": _digest(boot_id(), uid)}
        data["identity"] = identity
        expected = request["expected_identity"]
        if expected is not None and (
            not isinstance(expected, dict)
            or type(expected.get("uid")) is not int
            or expected != identity
        ):
            raise ManagedProblem("target_changed")
        data = _auth_observe(request, identity)
    except ManagedProblem as error:
        data["error"] = error.code if error.code in AUTH_ERRORS else "corrupt_state"
    except Deadline:
        data["error"] = "budget_exceeded"
    except (OSError, Unsupported):
        data["error"] = "unsafe_state"
    except (KeyError, TypeError, ValueError, AttributeError, RecursionError):
        data["error"] = "invalid_request"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    envelope = {"protocol": AUTH_PROTOCOL, "operation": "browser_auth", "data": data}
    encoded = json.dumps(envelope, ensure_ascii=True)
    if len(encoded) >= AUTH_LIMIT:
        envelope["data"] = dict.fromkeys(data) | {"error": "response_limit"}
        encoded = json.dumps(envelope)
    print(encoded)
