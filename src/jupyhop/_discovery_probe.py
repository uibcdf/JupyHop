"""Standalone, read-only Linux probe sent through SSH; no JupyHop installation.

Do not print exceptions or runtime records: they can contain credentials.
Only explicitly selected runtime directories and their declared PIDs are read.
"""

import hashlib
import http.client
import importlib
import json
import os
import pwd
import re
import signal
import socket
import stat
import sys
import time
from pathlib import PurePosixPath
from typing import Any

MAX_FILE = 16 * 1024
MAX_RECORDS = 64
_FILE = re.compile(r"(jpserver|nbserver)-(\d+)\.json\Z")
_BASE = re.compile(r"/[A-Za-z0-9_./~-]*\Z")
_VERSION = re.compile(r"2\.[0-9][A-Za-z0-9.!+_-]{0,62}\Z")


class Deadline(Exception):
    pass


class Unsupported(Exception):
    pass


def _deadline(signum: int, frame: Any) -> None:
    raise Deadline


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key, value in pairs:
        if key in data:
            raise ValueError
        data[key] = value
    return data


def _constant(value: str) -> None:
    raise ValueError


def _json(raw: bytes) -> Any:
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_constant)


def valid_base(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) <= 512
        and bool(_BASE.fullmatch(value))
        and value.endswith("/")
        and "//" not in value
        and not any(part in (".", "..") for part in value.split("/"))
    )


def _digest(*values: Any) -> str:
    return hashlib.sha256(json.dumps(values, separators=(",", ":")).encode()).hexdigest()[:24]


def _directory(path: str) -> int:
    """Open every path component without following symlinks; pin the directory."""
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in PurePosixPath(path).parts[1:]:
            newer = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = newer
        info = os.fstat(descriptor)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise Unsupported
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read_record(directory: int, name: str) -> dict[str, Any]:
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
            or info.st_nlink != 1
            or info.st_size > MAX_FILE
        ):
            raise Unsupported
        raw = bytearray()
        while len(raw) <= MAX_FILE:
            chunk = os.read(descriptor, min(4096, MAX_FILE + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        after = os.fstat(descriptor)
        if len(raw) > MAX_FILE or (info.st_size, info.st_mtime_ns) != (
            after.st_size,
            after.st_mtime_ns,
        ):
            raise Unsupported
        value = _json(bytes(raw))
        if not isinstance(value, dict):
            raise ValueError
        return value
    finally:
        os.close(descriptor)


def _small(path: str, limit: int = 65536) -> bytes:
    with open(path, "rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise Unsupported
    return data


def process_identity(pid: int) -> str:
    root = f"/proc/{pid}"
    if os.stat(root).st_uid != os.getuid():
        raise Unsupported
    status = _small(root + "/status").decode("ascii", errors="replace")
    uid_line = next(line for line in status.splitlines() if line.startswith("Uid:"))
    if any(int(value) != os.getuid() for value in uid_line.split()[1:]):
        raise Unsupported
    fields = _small(root + "/stat").decode("ascii", errors="replace").rsplit(")", 1)[1].split()
    if fields[0] == "Z":
        raise ProcessLookupError
    if os.readlink(root + "/ns/net") != os.readlink("/proc/self/ns/net"):
        raise Unsupported
    return str(int(fields[19]))  # starttime is field 22; suffix begins at field 3.


def listener_inode(pid: int, port: int) -> str:
    """Join the candidate PID's descriptors with kernel TCP tables, not a scan."""
    inodes = set()
    with os.scandir(f"/proc/{pid}/fd") as entries:
        for index, entry in enumerate(entries):
            if index >= 4096:
                raise Unsupported
            try:
                link = os.readlink(entry.path)
            except FileNotFoundError:
                continue
            if link.startswith("socket:[") and link.endswith("]"):
                inodes.add(link[8:-1])
    matches = []
    for table, loopback in (("tcp", "0100007F"), ("tcp6", "00000000000000000000000001000000")):
        try:
            raw = _small(f"/proc/{pid}/net/{table}", 1024 * 1024).decode("ascii")
        except FileNotFoundError:
            continue
        for line in raw.splitlines()[1:]:
            values = line.split()
            if len(values) < 10 or values[3] != "0A" or values[9] not in inodes:
                continue
            address, encoded_port = values[1].split(":")
            if int(encoded_port, 16) != port:
                continue
            if address != loopback:
                raise Unsupported  # includes wildcard/public binding in either family
            if table == "tcp":
                matches.append(values[9])
    if len(matches) != 1:
        raise Unsupported
    return matches[0]


class _DeadlineSocket(socket.socket):
    """Bound total reads, including a peer that keeps trickling header bytes."""

    def __init__(self) -> None:
        super().__init__(socket.AF_INET, socket.SOCK_STREAM)
        self.deadline = time.monotonic() + 2
        self.settimeout(1)

    def recv_into(self, buffer: Any, nbytes: int = 0, flags: int = 0) -> int:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        self.settimeout(min(1, remaining))
        return super().recv_into(buffer, nbytes, flags)


class _Connection(http.client.HTTPConnection):
    def connect(self) -> None:
        channel = _DeadlineSocket()
        try:
            channel.connect(("127.0.0.1", self.port))
            self.sock = channel
        except BaseException:
            channel.close()
            raise


def endpoint(port: int, base: str) -> str:
    connection = _Connection("127.0.0.1", port, timeout=1)
    try:
        connection.request("GET", base + "api", headers={"Connection": "close"})
        response = connection.getresponse()
        if response.status != 200:
            raise Unsupported
        raw = response.read(4097)
        if len(raw) > 4096:
            raise Unsupported
        version = _json(raw).get("version")
        if not isinstance(version, str) or not _VERSION.fullmatch(version):
            raise Unsupported
    finally:
        connection.close()
    connection = _Connection("127.0.0.1", port, timeout=1)
    try:
        connection.request("GET", base + "api/status", headers={"Connection": "close"})
        if connection.getresponse().status != 403:
            raise Unsupported  # refuse unprotected/unknown auth configurations
    finally:
        connection.close()
    return version


def _candidate(directory: int, name: str, path: str, scope: str) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": _digest(scope, path, name),
        "origin": "unmanaged",
        "state": "unsupported",
        "reason": "invalid_metadata",
        "pid": None,
        "port": None,
        "address": None,
        "base_url": None,
        "version": None,
        "sources": [path],
    }
    try:
        match = _FILE.fullmatch(name)
        assert match is not None
        if match[1] != "jpserver":
            record["reason"] = "legacy_metadata"
            return record
        info = _read_record(directory, name)
        pid, port, base = info.get("pid"), info.get("port"), info.get("base_url")
        if (
            type(pid) is not int
            or pid <= 0
            or pid != int(match[2])
            or type(port) is not int
            or not 1 <= port <= 65535
            or not valid_base(base)
        ):
            return record
        record["pid"], record["port"] = pid, port
        assert isinstance(base, str)
        if info.get("secure") is not False or info.get("sock") not in ("", None):
            record["reason"] = "https_or_unix_socket"
            return record
        if info.get("hostname") not in ("127.0.0.1", "localhost"):
            record["reason"] = "unsupported_address"
            return record
        record["reason"] = "unverified_process_or_listener"
        started = process_identity(pid)
        inode = listener_inode(pid, port)
        record["state"], record["reason"] = "unreachable", "endpoint_unavailable"
        version = endpoint(port, base)
        if process_identity(pid) != started or listener_inode(pid, port) != inode:
            raise Unsupported
        record.update(
            {
                "id": _digest(scope, pid, started, inode, port, base),
                "state": "ready",
                "reason": "verified",
                "address": "127.0.0.1",
                "base_url": base,
                "version": version,
                "_process_start": started,
                "_socket_inode": inode,
            }
        )
    except (FileNotFoundError, ProcessLookupError):
        record["state"], record["reason"] = "stale", "process_or_file_gone"
    except Unsupported:
        record["state"] = "unsupported"
        if record["reason"] == "endpoint_unavailable":
            record["reason"] = "unsupported_jupyter_or_auth"
    except (
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        StopIteration,
        AttributeError,
        RecursionError,
    ):
        record["state"] = "unsupported"
    except (OSError, http.client.HTTPException):
        # Permission failures and refused HTTP endpoints do not establish death.
        if record["state"] != "unreachable":
            record["reason"] = "unverified_process_or_listener"
    return record


def _paths(explicit: list[str]) -> list[tuple[str, str]]:
    default, source = "", "jupyter-core"
    try:
        default = importlib.import_module("jupyter_core.paths").jupyter_runtime_dir()
    except ImportError:
        source = "linux-default"
        data = os.environ.get("JUPYTER_DATA_DIR") or os.path.join(
            os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "jupyter"
        )
        default = os.environ.get("JUPYTER_RUNTIME_DIR") or os.path.join(data, "runtime")
    paths = [(default, source)] + [(os.path.expanduser(path), "explicit") for path in explicit]
    return list(dict.fromkeys(paths))


def discover(request: dict[str, Any], report: dict[str, Any]) -> None:
    if sys.version_info < (3, 11) or not sys.platform.startswith("linux"):
        raise Unsupported
    boot = _small("/proc/sys/kernel/random/boot_id", 64).decode("ascii").strip()
    scope = _digest(boot, os.getuid())
    report["identity"] = {
        "uid": os.getuid(),
        "user": pwd.getpwuid(os.getuid()).pw_name,
        "scope": scope,
    }
    records, managed_issues = (
        globals()["managed_context"]() if "managed_context" in globals() else ([], [])
    )
    report["issues"].extend(managed_issues)
    paths = _paths(request["runtime_dirs"]) + [(r["runtime"], "managed") for r in records]
    for path, source in list(dict.fromkeys(paths)):
        entry = {"path": path, "source": source, "status": "unsafe"}
        report["paths"].append(entry)
        if not os.path.isabs(path) or len(path) > 1024 or ".." in PurePosixPath(path).parts:
            continue
        try:
            directory = _directory(path)
        except FileNotFoundError:
            entry["status"] = "missing"
            continue
        except (OSError, Unsupported):
            continue
        try:
            entry["status"] = "ok"
            with os.scandir(directory) as entries:
                for index, item in enumerate(entries):
                    if index >= 512:
                        entry["status"] = "limited"
                        for issue in ("scan_limit", "entry_limit"):
                            if issue not in report["issues"]:
                                report["issues"].append(issue)
                        break
                    if _FILE.fullmatch(item.name):
                        candidate = _candidate(directory, item.name, path, scope)
                        if "mark_managed" in globals():
                            candidate = globals()["mark_managed"](candidate, records)
                        if len(report["servers"]) < MAX_RECORDS:
                            report["servers"].append(candidate)
                        else:
                            # A full diagnostic sample must not prevent finding
                            # a live server later in this or another runtime.
                            for issue in ("sample_limit", "entry_limit"):
                                if issue not in report["issues"]:
                                    report["issues"].append(issue)
                            if candidate["state"] == "ready":
                                for position in range(MAX_RECORDS - 1, -1, -1):
                                    if report["servers"][position]["state"] != "ready":
                                        report["servers"][position] = candidate
                                        break
        finally:
            os.close(directory)
    if records:
        report["servers"].extend(
            globals()["missing_managed"](records, {s["id"] for s in report["servers"]})
        )
    # Preserve verified endpoints if the final byte bound truncates diagnostics.
    report["servers"].sort(key=lambda server: server["state"] != "ready")


def main() -> None:
    report: dict[str, Any] = {
        "identity": None,
        "complete": False,
        "paths": [],
        "servers": [],
        "issues": [],
    }
    signal.signal(signal.SIGALRM, _deadline)
    try:
        request = _json(sys.argv[1].encode())
        signal.setitimer(signal.ITIMER_REAL, request["budget"])
        discover(request, report)
    except Deadline:
        report["issues"].append("time_limit")
    except Exception:
        report["issues"].append("probe_failed")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    if report["identity"] is None:
        print("Discovery needs Linux /proc and Python >=3.11.", file=sys.stderr)
        sys.exit(4)
    envelope = {"protocol": {"major": 1, "minor": 6}, "operation": "discover", "data": report}
    while len(json.dumps(envelope).encode()) > 60 * 1024:
        if report["servers"]:
            report["servers"].pop()
        elif report["paths"]:
            report["paths"].pop()
        else:
            break
        if "output_limit" not in report["issues"]:
            report["issues"].append("output_limit")
    print(json.dumps(envelope, ensure_ascii=True))


if __name__ == "__main__":
    main()
