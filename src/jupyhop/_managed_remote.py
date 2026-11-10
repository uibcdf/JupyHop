"""Versioned per-user launch state. Also sent as source to remote Python.

No writes occur on import or during discovery. Only the explicit start RPC
creates records. Explicit lifecycle RPCs reconcile or stop them. Password hashes live in a separate private Jupyter settings
file, never in records or responses. This module has no daemon or installed API.
"""

import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING or __name__ == "jupyhop._managed_remote":
    from jupyhop._discovery_probe import Unsupported, _candidate, listener_inode, process_identity

SCHEMA = {"major": 1, "minor": 0}
_SID = re.compile(r"[a-f0-9]{32}\Z")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
_STATES = {"requested", "starting", "ready", "failed", "exited"}


def _known_schema(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and type(value.get("major")) is int
        and type(value.get("minor")) is int
        and value == SCHEMA
    )


class ManagedProblem(Exception):
    def __init__(self, code: str):
        self.code = code


def state_root() -> str:
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    if not os.path.isabs(base) or len(base) > 512 or ".." in Path(base).parts:
        raise ManagedProblem("unsafe_state")
    identity = None
    for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            with open(path, encoding="ascii") as stream:
                candidate = stream.read(128).strip()
            if re.fullmatch(r"[0-9a-fA-F]{32}", candidate):
                identity = candidate.lower()
                break
        except OSError:
            continue
    if identity is None:
        raise ManagedProblem("host_identity_unavailable")
    scope = hashlib.sha256((identity + ":" + str(os.getuid())).encode()).hexdigest()[:24]
    return os.path.join(base, "jupyhop", "hosts", scope)


def _private_dir(path: str, create: bool = False) -> int:
    if not os.path.isabs(path) or ".." in Path(path).parts:
        raise ManagedProblem("unsafe_state")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in Path(path).parts[1:]:
            try:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ManagedProblem("unsafe_state")
        return fd
    except BaseException:
        os.close(fd)
        raise


def _checked_file(fd: int) -> None:
    info = os.fstat(fd)
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
        or info.st_nlink != 1
    ):
        raise ManagedProblem("unsafe_state")


def _read(directory: int, name: str, limit: int = 16384) -> bytes:
    for _ in range(3):
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        try:
            try:
                _checked_file(fd)
            except ManagedProblem:
                # A concurrent atomic update can unlink the inode between open
                # and fstat. Reopen the current name; never relax link/mode/UID
                # checks or accept bytes from the retired inode.
                if os.fstat(fd).st_nlink == 0:
                    continue
                raise
            info = os.fstat(fd)
            if info.st_size > limit:
                raise ManagedProblem("corrupt_state")
            data = bytearray()
            while len(data) <= limit:
                chunk = os.read(fd, min(4096, limit + 1 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
            after = os.fstat(fd)
            if len(data) > limit or (info.st_size, info.st_mtime_ns) != (
                after.st_size,
                after.st_mtime_ns,
            ):
                raise ManagedProblem("corrupt_state")
            return bytes(data)
        finally:
            os.close(fd)
    raise ManagedProblem("registry_busy")


def _load(directory: int, name: str) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ManagedProblem("corrupt_state")
            result[key] = value
        return result

    value = json.loads(_read(directory, name), object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ManagedProblem("corrupt_state")
    return value


def _write(directory: int, name: str, value: bytes, *, exclusive: bool = False) -> None:
    temporary = ".write-" + uuid.uuid4().hex
    try:
        if exclusive:
            fd = os.open(
                name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory
            )
        else:
            fd = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(value)
                stream.flush()
                os.fsync(stream.fileno())
            if not exclusive:
                os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
            os.fsync(directory)
        finally:
            if not exclusive:
                try:
                    os.unlink(temporary, dir_fd=directory)
                except FileNotFoundError:
                    pass
    except OSError:
        raise ManagedProblem("state_write_failed") from None


def _save(directory: int, name: str, value: dict[str, Any], *, exclusive: bool = False) -> None:
    _write(directory, name, json.dumps(value, ensure_ascii=True).encode(), exclusive=exclusive)


def boot_id() -> str:
    with open("/proc/sys/kernel/random/boot_id", encoding="ascii") as stream:
        return stream.read(64).strip()


def validate_record(value: dict[str, Any], sid: str) -> dict[str, Any]:
    if not _known_schema(value.get("schema")):
        raise ManagedProblem("incompatible_registry")
    if (
        not _SID.fullmatch(sid)
        or value.get("id") != sid
        or type(value.get("owner_uid")) is not int
        or value.get("owner_uid") != os.getuid()
        or not isinstance(value.get("name"), str)
        or not _NAME.fullmatch(value["name"])
        or value.get("state") not in _STATES
        or value.get("manager") != "tmux"
    ):
        raise ManagedProblem("corrupt_state")
    for key in ("runtime", "workdir", "server_python", "socket"):
        item = value.get(key)
        if (
            not isinstance(item, str)
            or not os.path.isabs(item)
            or len(item) > 4096
            or any(ord(c) < 32 for c in item)
        ):
            raise ManagedProblem("corrupt_state")
    if value.get("base_url") != "/jupyhop/" + sid + "/" or value.get("boot_id") is None:
        raise ManagedProblem("corrupt_state")
    for key in ("pid", "port"):
        item = value.get(key)
        if item is not None and (
            type(item) is not int or item <= 0 or key == "port" and item > 65535
        ):
            raise ManagedProblem("corrupt_state")
    for key in ("process_start", "socket_inode"):
        item = value.get(key)
        if item is not None and (
            not isinstance(item, str) or not item.isascii() or not item.isdigit() or len(item) > 32
        ):
            raise ManagedProblem("corrupt_state")
    digest = value.get("runner_sha256")
    if not isinstance(digest, str) or re.fullmatch(r"[a-f0-9]{64}", digest) is None:
        raise ManagedProblem("corrupt_state")
    if value.get("error") not in (None, "launch_failed", "server_initialization_failed"):
        raise ManagedProblem("corrupt_state")
    if "stop_requested" in value and type(value["stop_requested"]) is not bool:
        raise ManagedProblem("corrupt_state")
    return value


class Registry:
    def __init__(self, root: str | None = None, *, create: bool = False):
        self.default_root = root is None
        self.root = root or state_root()
        self.create = create
        self.fd = -1
        self.sessions = -1

    def __enter__(self) -> "Registry":
        if self.default_root:
            for parent in (os.path.dirname(os.path.dirname(self.root)), os.path.dirname(self.root)):
                descriptor = _private_dir(parent, self.create)
                os.close(descriptor)
        self.fd = _private_dir(self.root, self.create)
        try:
            try:
                existing = _load(self.fd, "registry.json")
            except FileNotFoundError:
                existing = None
            if existing is not None and (
                not _known_schema(existing.get("schema")) or existing.get("producer") != "jupyhop"
            ):
                raise ManagedProblem("incompatible_registry")
            if self.create:
                try:
                    os.mkdir("sessions", 0o700, dir_fd=self.fd)
                except FileExistsError:
                    pass
            self.sessions = _private_dir(os.path.join(self.root, "sessions"))
            return self
        except BaseException:
            self.__exit__()
            raise

    def __exit__(self, *args: object) -> None:
        for fd in (self.sessions, self.fd):
            if fd >= 0:
                os.close(fd)
        self.fd = self.sessions = -1

    @contextmanager
    def lock(self) -> Iterator[None]:
        fd = os.open(
            ".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=self.fd
        )
        try:
            _checked_file(fd)
            deadline = time.monotonic() + 3
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise ManagedProblem("registry_busy") from None
                    time.sleep(0.05)
            try:
                self.header(create=self.create)
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def header(self, *, create: bool = False) -> None:
        try:
            header = _load(self.fd, "registry.json")
        except FileNotFoundError:
            if not create or os.listdir(self.sessions):
                raise ManagedProblem("corrupt_state") from None
            _save(
                self.fd, "registry.json", {"schema": SCHEMA, "producer": "jupyhop"}, exclusive=True
            )
            return
        if not _known_schema(header.get("schema")) or header.get("producer") != "jupyhop":
            raise ManagedProblem("incompatible_registry")

    @contextmanager
    def session(self, sid: str) -> Iterator[int]:
        if not _SID.fullmatch(sid):
            raise ManagedProblem("corrupt_state")
        fd = _private_dir(os.path.join(self.root, "sessions", sid))
        try:
            yield fd
        finally:
            os.close(fd)

    def records(self) -> list[dict[str, Any]]:
        self.header()
        records = []
        with os.scandir(self.sessions) as entries:
            for index, entry in enumerate(entries):
                if index >= 128 or not _SID.fullmatch(entry.name):
                    raise ManagedProblem("state_limit_or_corruption")
                with self.session(entry.name) as fd:
                    value = validate_record(_load(fd, "record.json"), entry.name)
                    if value["runtime"] != os.path.join(
                        self.root, "sessions", entry.name, "runtime"
                    ):
                        raise ManagedProblem("corrupt_state")
                    if (
                        hashlib.sha256(_read(fd, "launch.py", 96 * 1024)).hexdigest()
                        != value["runner_sha256"]
                    ):
                        raise ManagedProblem("corrupt_state")
                    records.append(value)
        return records

    def update(self, sid: str, changes: dict[str, Any]) -> dict[str, Any]:
        with self.lock(), self.session(sid) as fd:
            value = validate_record(_load(fd, "record.json"), sid)
            value.update(changes)
            validate_record(value, sid)
            _save(fd, "record.json", value)
            return value


def managed_context() -> tuple[list[dict[str, Any]], list[str]]:
    try:
        with Registry() as registry:
            return registry.records(), []
    except FileNotFoundError:
        return ([], ["managed_state_unavailable"]) if os.path.lexists(state_root()) else ([], [])
    except (ManagedProblem, OSError, ValueError, TypeError, KeyError):
        return [], ["managed_state_unavailable"]


def runner_matches(record: dict[str, Any]) -> bool:
    """Process + private manager evidence, independent of HTTP availability."""
    try:
        if (
            record["boot_id"] != boot_id()
            or process_identity(record["pid"]) != record["process_start"]
        ):
            return False
        root = os.path.dirname(record["runtime"])
        with open(f"/proc/{record['pid']}/cmdline", "rb") as stream:
            arguments = stream.read(16385).split(b"\0")[:-1]
        expected = [record["server_python"], "-I", "-B", os.path.join(root, "launch.py"), root]
        if arguments != [os.fsencode(value) for value in expected]:
            return False
        directory = _private_dir(os.path.dirname(record["socket"]))
        os.close(directory)
        info = os.stat(record["socket"], follow_symlinks=False)
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            return False
        result = subprocess.run(
            [
                "tmux",
                "-S",
                record["socket"],
                "display-message",
                "-p",
                "-t",
                record["id"] + ":0.0",
                "#{pane_pid}",
            ],
            capture_output=True,
            timeout=2,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == str(record["pid"]).encode()
    except (OSError, Unsupported, ManagedProblem, subprocess.TimeoutExpired, ValueError, TypeError):
        return False


def observed_state(record: dict[str, Any]) -> str:
    if record["boot_id"] != boot_id():
        return "stale"
    if record["pid"] is None:
        return "failed" if record["state"] == "failed" else "starting"
    try:
        current = process_identity(record["pid"])
    except (FileNotFoundError, ProcessLookupError):
        return (
            "stopped"
            if record.get("stop_requested")
            else "failed"
            if record["state"] == "failed"
            else "stale"
        )
    except (OSError, Unsupported, ValueError):
        return "unreachable"
    if current != record["process_start"]:
        return "stale"
    if record.get("stop_requested"):
        return "stopping"
    return "failed" if record["state"] == "failed" else "unreachable"


def mark_managed(candidate: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    candidate["observed_id"] = candidate["id"]
    candidate["name"] = None
    for record in records:
        if (
            candidate["state"] == "ready"
            and record["boot_id"] == boot_id()
            and record["state"] in {"starting", "ready"}
            and candidate["pid"] == record["pid"]
            and candidate.get("_process_start") == record["process_start"]
            and candidate.get("_socket_inode") == record["socket_inode"]
            and candidate["port"] == record["port"]
            and candidate["base_url"] == record["base_url"]
            and runner_matches(record)
        ):
            candidate.update({"id": record["id"], "origin": "managed", "name": record["name"]})
            if record.get("stop_requested"):
                candidate.update({"state": "stopping", "reason": "managed_stopping"})
            break
    candidate.pop("_process_start", None)
    candidate.pop("_socket_inode", None)
    return candidate


def missing_managed(records: list[dict[str, Any]], found: set[str]) -> list[dict[str, Any]]:
    values = []
    for record in records:
        if record["id"] in found:
            continue
        state = observed_state(record)
        values.append(
            {
                "id": record["id"],
                "observed_id": None,
                "name": record["name"],
                "origin": "managed",
                "state": state,
                "reason": "managed_" + state,
                "pid": record["pid"],
                "port": record["port"],
                "address": None,
                "base_url": record["base_url"],
                "version": None,
                "sources": [record["runtime"]],
            }
        )
    return values


_SOURCES: list[str] = globals().get("_SOURCES", [])  # client-owned RPC bootstrap

_PREFLIGHT = """import json,sys,importlib.util
try:
    from jupyter_server import __version__
    from jupyter_server.auth import passwd
    from jupyter_client.kernelspec import KernelSpecManager
    request=json.load(sys.stdin)
    version=__version__.split('.')
    if len(version)<2 or version[0]!='2' or not version[1].isdigit() or int(version[1])<20:
        sys.exit(5)
    if sys.version_info < (3,11) or not KernelSpecManager().find_kernel_specs():
        sys.exit(4)
    print(json.dumps({'hash':passwd(request['password']), 'lab':importlib.util.find_spec('jupyterlab') is not None}))
except Exception:
    sys.exit(4)
"""


def _socket_path(sid: str) -> str:
    runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    if runtime and len(os.fsencode(runtime)) <= 50:
        try:
            descriptor = _private_dir(runtime)
            os.close(descriptor)
        except (OSError, ManagedProblem):
            runtime = ""
    else:
        runtime = ""
    base = os.path.join(runtime, "jupyhop") if runtime else f"/tmp/jupyhop-{os.getuid()}"
    descriptor = _private_dir(base, True)
    os.close(descriptor)
    result = os.path.join(base, sid + ".sock")
    if os.path.lexists(result):
        raise ManagedProblem("id_conflict")
    return result


def _runner_source() -> bytes:
    # Code is immutable client-owned source, not any registry/metadata content.
    return (
        "import sys\nnamespace={'__name__':'jupyhop_runner'}\n"
        + "sources="
        + repr(_SOURCES)
        + "\n"
        + "namespace['_SOURCES']=sources\n"
        + "for source in sources: exec(compile(source,'<jupyhop-runner>','exec'),namespace)\n"
        + "namespace['run_server'](sys.argv[1])\n"
    ).encode()


def _validated_request(request: dict[str, Any]) -> tuple[str, str, str, str, str]:
    if request.get("protocol") != {"major": 1, "minor": 2}:
        raise ManagedProblem("incompatible_registry")
    sid, name = request.get("id"), request.get("name")
    if (
        not isinstance(sid, str)
        or not _SID.fullmatch(sid)
        or not isinstance(name, str)
        or not _NAME.fullmatch(name)
    ):
        raise ManagedProblem("invalid_request")
    password = request.pop("password", None)
    if (
        not isinstance(password, str)
        or not 8 <= len(password) <= 1024
        or any(ord(c) < 32 or ord(c) == 127 for c in password)
    ):
        raise ManagedProblem("invalid_request")
    path = request.get("workdir")
    if (
        not isinstance(path, str)
        or not path
        or len(path) > 4096
        or path.startswith("~")
        and not (path == "~" or path.startswith("~/"))
        or any(ord(c) < 32 for c in path)
    ):
        raise ManagedProblem("invalid_workdir")
    home = os.path.expanduser("~")
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(home, path)
    path = os.path.realpath(path)
    if not os.path.isdir(path) or not os.access(path, os.R_OK | os.X_OK):
        raise ManagedProblem("invalid_workdir")
    python = request.get("server_python")
    if (
        not isinstance(python, str)
        or any(ord(c) < 32 for c in python)
        or not (python == "python3" or os.path.isabs(python))
    ):
        raise ManagedProblem("missing_python")
    python = shutil.which(python) or ""
    if not python or not os.path.isabs(python):
        raise ManagedProblem("missing_python")
    return sid, name, password, path, python


def _prepare(request: dict[str, Any]) -> dict[str, Any]:
    sid, name, password, workdir, python = _validated_request(request)
    if sys.version_info < (3, 11) or not sys.platform.startswith("linux"):
        raise ManagedProblem("server_prerequisites")
    manager = shutil.which("tmux")
    if manager is None:
        raise ManagedProblem("missing_tmux")
    try:
        result = subprocess.run(
            [python, "-I", "-B", "-c", _PREFLIGHT],
            input=json.dumps({"password": password}).encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=8,
            check=False,
        )
        if result.returncode == 5:
            raise ManagedProblem("unsupported_server_version")
        if result.returncode or len(result.stdout) > 4096:
            raise ManagedProblem("server_prerequisites")
        checked = json.loads(result.stdout)
        if not isinstance(checked, dict):
            raise ManagedProblem("server_prerequisites")
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError, RecursionError):
        # This phase cannot create a registry or spawn a server. Do not turn a
        # known environment-check failure into an unknown launch outcome.
        raise ManagedProblem("server_prerequisites") from None
    finally:
        del password
    password_hash = checked.get("hash")
    if (
        not isinstance(password_hash, str)
        or not password_hash.startswith("argon2:")
        or len(password_hash) > 1024
        or type(checked.get("lab")) is not bool
    ):
        raise ManagedProblem("server_prerequisites")
    runner = _runner_source()
    with Registry(create=True) as registry:
        with registry.lock():
            records = registry.records()
            if any(value["name"] == name for value in records):
                raise ManagedProblem("name_conflict")
            if len(records) >= 128:
                raise ManagedProblem("registry_full")
            if os.path.lexists(os.path.join(registry.root, "archive", sid)):
                raise ManagedProblem("id_conflict")
            try:
                os.mkdir(sid, 0o700, dir_fd=registry.sessions)
            except FileExistsError:
                raise ManagedProblem("id_conflict") from None
            root = os.path.join(registry.root, "sessions", sid)
            socket_path = _socket_path(sid)
            record = {
                "schema": SCHEMA,
                "id": sid,
                "name": name,
                "owner_uid": os.getuid(),
                "boot_id": boot_id(),
                "state": "requested",
                "created": datetime.now(UTC).isoformat(),
                "manager": "tmux",
                "socket": socket_path,
                "runtime": os.path.join(root, "runtime"),
                "workdir": workdir,
                "server_python": python,
                "base_url": "/jupyhop/" + sid + "/",
                "pid": None,
                "process_start": None,
                "socket_inode": None,
                "port": None,
                "runner_sha256": hashlib.sha256(runner).hexdigest(),
                "error": None,
            }
            with registry.session(sid) as fd:
                _write(fd, "launch.py", runner, exclusive=True)
                for directory in ("runtime", "config"):
                    os.mkdir(directory, 0o700, dir_fd=fd)
                _write(fd, "server.log", b"", exclusive=True)
                _save(
                    fd,
                    "settings.json",
                    {"password_hash": password_hash, "lab": checked["lab"]},
                    exclusive=True,
                )
                _save(fd, "record.json", record, exclusive=True)
        environment = dict(os.environ)
        environment.pop("TMUX", None)
        environment.pop("TMUX_PANE", None)
        launched = subprocess.run(
            [
                manager,
                "-f",
                "/dev/null",
                "-S",
                socket_path,
                "new-session",
                "-d",
                "-s",
                sid,
                "-c",
                "/",
                python,
                "-I",
                "-B",
                os.path.join(root, "launch.py"),
                root,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=environment,
            timeout=4,
            check=False,
        )
        if launched.returncode:
            return registry.update(sid, {"state": "failed", "error": "launch_failed"})
        return record


def run_server(root: str) -> None:
    """Executed by this session's immutable runner in the chosen server Python."""
    from importlib import import_module

    sid = os.path.basename(root)
    registry_root = os.path.dirname(os.path.dirname(root))
    try:
        with Registry(registry_root) as registry, registry.session(sid) as fd:
            registry.header()
            record = validate_record(_load(fd, "record.json"), sid)
            if record["boot_id"] != boot_id() or record["state"] not in {"requested", "starting"}:
                raise ManagedProblem("corrupt_state")
            if (
                hashlib.sha256(_read(fd, "launch.py", 96 * 1024)).hexdigest()
                != record["runner_sha256"]
            ):
                raise ManagedProblem("corrupt_state")
            log = os.open("server.log", os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW, dir_fd=fd)
            _checked_file(log)
            os.dup2(log, 1)
            os.dup2(log, 2)
            os.close(log)
            settings = _load(fd, "settings.json")
            password_hash = settings.get("password_hash")
            if not isinstance(password_hash, str) or not password_hash.startswith("argon2:"):
                raise ManagedProblem("corrupt_state")
            started = process_identity(os.getpid())
            registry.update(
                sid, {"state": "starting", "pid": os.getpid(), "process_start": started}
            )
            os.environ["JUPYTER_RUNTIME_DIR"] = record["runtime"]
            os.environ["JUPYTER_CONFIG_DIR"] = os.path.join(root, "config")
            for key in ("JUPYTER_TOKEN", "JUPYTER_TOKEN_FILE"):
                os.environ.pop(key, None)
            os.chdir(record["workdir"])
            server_class = import_module("jupyter_server.serverapp").ServerApp
            config_class = import_module("traitlets.config").Config

            class ManagedServer(server_class):  # type: ignore[misc,valid-type]
                @property
                def config_file_paths(self) -> list[str]:
                    return [os.path.join(root, "config")]

            config = {
                "ServerApp": {
                    "ip": "127.0.0.1",
                    "port": 0,
                    "port_retries": 0,
                    "open_browser": False,
                    "root_dir": record["workdir"],
                    "base_url": record["base_url"],
                    "default_url": "/lab" if settings["lab"] else "/",
                    "log_level": "CRITICAL",
                    "identity_provider_class": "jupyter_server.auth.identity.PasswordIdentityProvider",
                    "jpserver_extensions": {"jupyterlab": True} if settings["lab"] else {},
                    "allow_remote_access": False,
                    "trust_xheaders": False,
                    "disable_check_xsrf": False,
                },
                "PasswordIdentityProvider": {
                    "hashed_password": password_hash,
                    "password_required": True,
                    "token": "",
                },
            }
            app = ManagedServer.instance(config=config_class(config))
            app.initialize([], find_extensions=False)

            def checkpoint() -> None:
                try:
                    inode = listener_inode(os.getpid(), app.port)
                    registry.update(sid, {"port": int(app.port), "socket_inode": inode})
                except Exception:
                    app.io_loop.stop()

            app.io_loop.add_callback(checkpoint)
            app.start()
            registry.update(sid, {"state": "exited"})
    except BaseException:
        try:
            with Registry(registry_root) as registry:
                registry.update(sid, {"state": "failed", "error": "server_initialization_failed"})
        except Exception:
            pass


def start_main(request: dict[str, Any]) -> None:
    value = request.get("id")
    sid = value if isinstance(value, str) and _SID.fullmatch(value) else ""
    response: dict[str, Any] = {
        "id": sid,
        "state": "failed",
        "error": None,
        "identity": None,
        "server": None,
        "record_path": None,
    }
    try:
        deadline = time.monotonic() + max(1, request["budget"])
        record = _prepare(request)
        response["record_path"] = os.path.join(
            state_root(), "sessions", record["id"], "record.json"
        )
        response["state"] = record["state"]
        while time.monotonic() < deadline:
            with Registry() as registry:
                records = registry.records()
                record = next(r for r in records if r["id"] == sid)
                if record["state"] in {"failed", "exited"}:
                    response.update(
                        {"state": "failed", "error": record["error"] or "launch_failed"}
                    )
                    break
                if record["pid"] and record["port"] and record["socket_inode"]:
                    runtime = _private_dir(record["runtime"])
                    try:
                        scope = hashlib.sha256(
                            json.dumps((boot_id(), os.getuid()), separators=(",", ":")).encode()
                        ).hexdigest()[:24]
                        candidate = _candidate(
                            runtime, f"jpserver-{record['pid']}.json", record["runtime"], scope
                        )
                        candidate = mark_managed(candidate, records)
                    finally:
                        os.close(runtime)
                    if candidate["state"] == "ready" and candidate["origin"] == "managed":
                        registry.update(sid, {"state": "ready", "error": None})
                        import pwd

                        response.update(
                            {
                                "state": "ready",
                                "identity": {
                                    "uid": os.getuid(),
                                    "user": pwd.getpwuid(os.getuid()).pw_name,
                                    "scope": scope,
                                },
                                "server": candidate,
                            }
                        )
                        break
            time.sleep(0.1)
        else:
            response.update({"state": "starting", "error": "readiness_timeout"})
    except ManagedProblem as error:
        response["error"] = error.code
    except Exception:
        response.update({"state": "starting", "error": "launch_unknown"})
    print(
        json.dumps(
            {"protocol": {"major": 1, "minor": 2}, "operation": "start", "data": response},
            ensure_ascii=True,
        )
    )
