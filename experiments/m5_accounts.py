"""Temporary real Unix accounts and a private loopback sshd for M5 acceptance.

prepare: unprivileged, only creates private temporary keys/metadata.
provision/cleanup: explicitly run with sudo and native Linux Python >=3.11.
Never changes the normal SSH configuration or service. Root-owned state in /run
binds cleanup to the generated names, exact UIDs/homes and pinned daemon identity.
"""

import argparse
import base64
import fcntl
import grp
import json
import os
import pwd
import re
import select
import signal
import socket
import stat
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT_BASE = Path("/tmp")
RUN_BASE = Path("/run")
PREFIX = "jupyhop-m5-accounts-"


def _directory(path, owner):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    info = os.fstat(descriptor)
    if info.st_uid != owner or info.st_mode & 0o077:
        os.close(descriptor)
        raise RuntimeError("Fixture directory has unexpected ownership or permissions")
    return descriptor


def _lock(folder):
    descriptor = os.open(folder / "lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != 0
            or info.st_nlink != 1
            or info.st_mode & 0o077
        ):
            raise RuntimeError("Unsafe root fixture lock")
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read(path, owner, limit=16384):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != owner
            or info.st_nlink != 1
            or info.st_mode & 0o022
            or info.st_size > limit
        ):
            raise RuntimeError("Unsafe fixture metadata/key file")
        result = os.read(descriptor, limit + 1)
        if len(result) > limit:
            raise RuntimeError("Fixture file exceeds its limit")
        return result
    finally:
        os.close(descriptor)


def _write(path, value, *, owner=None):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        if owner is not None:
            os.fchown(descriptor, *owner)
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)


def _json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RuntimeError("Duplicate fixture metadata field")
            result[key] = value
        return result

    return json.loads(raw, object_pairs_hook=unique)


def _root(path):
    root = Path(path).absolute()
    token = root.name.removeprefix(PREFIX)
    if (
        root.parent != ROOT_BASE
        or root.name != PREFIX + token
        or re.fullmatch(r"[a-f0-9]{12}", token) is None
    ):
        raise RuntimeError("Use the exact private /tmp fixture path produced by prepare")
    return root, token


def _run(args):
    result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError(
            "Fixture command failed: " + Path(args[0]).name + "; raw output suppressed"
        )
    return result.stdout


def _public(path, owner):
    fields = _read(path, owner).decode("ascii").strip().split()
    if len(fields) != 3 or fields[0] != "ssh-ed25519" or fields[2] != "fixture":
        raise RuntimeError("Only generated ed25519 fixture keys are accepted")
    base64.b64decode(fields[1], validate=True)
    return " ".join(fields)


def prepare():
    if os.geteuid() == 0:
        raise RuntimeError("Run prepare as your ordinary development user, without sudo")
    token = uuid.uuid4().hex[:12]
    root = ROOT_BASE / (PREFIX + token)
    root.mkdir(mode=0o700)
    for name in ("hostkey", "a", "b"):
        _run(
            [
                "/usr/bin/ssh-keygen",
                "-q",
                "-t",
                "ed25519",
                "-N",
                "",
                "-C",
                "fixture",
                "-f",
                str(root / name),
            ]
        )
    _write(root / "prepared.json", json.dumps({"version": 1, "token": token}).encode())
    return root


def _prepared(root):
    root, token = _root(root)
    info = root.lstat()
    descriptor = _directory(root, info.st_uid)
    os.close(descriptor)
    data = _json(_read(root / "prepared.json", info.st_uid))
    if data != {"version": 1, "token": token} or type(data.get("version")) is not int:
        raise RuntimeError("Unexpected fixture metadata")
    for name in ("hostkey", "a", "b"):
        _public(root / (name + ".pub"), info.st_uid)
        private = _read(root / name, info.st_uid)
        if not private.startswith(b"-----BEGIN OPENSSH PRIVATE KEY-----"):
            raise RuntimeError("Unexpected fixture key format")
    return root, token, info.st_uid, info.st_gid


def _privileged():
    if os.geteuid() != 0:
        raise RuntimeError("This action requires sudo; prepare/check do not")
    if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
        raise RuntimeError(
            "Use native Linux /usr/bin/python3 with pidfd support, not the Conda interpreter"
        )


def _start(pid):
    return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]


def _save_state(folder, value):
    temporary = folder / ("state-" + uuid.uuid4().hex + ".json")
    _write(temporary, json.dumps(value).encode())
    os.replace(temporary, folder / "state.json")
    descriptor = _directory(folder, 0)
    os.fsync(descriptor)
    os.close(descriptor)


def _account(entry, token):
    try:
        account = pwd.getpwnam(entry["name"])
    except KeyError:
        return None
    if (
        account.pw_uid == 0
        or account.pw_dir != "/home/" + entry["name"]
        or account.pw_gecos != "JupyHop M5 " + token
        or (entry["uid"] is not None and account.pw_uid != entry["uid"])
    ):
        raise RuntimeError("Account identity changed; cleanup refuses to modify it")
    home = Path(account.pw_dir)
    if home.is_symlink() or home.exists() and home.stat().st_uid != account.pw_uid:
        raise RuntimeError("Fixture home identity changed; refusing cleanup")
    return account


def provision(path):
    _privileged()
    root, token, uid, gid = _prepared(path)
    folder = RUN_BASE / (PREFIX + token)
    users = [
        {"name": "jht_" + token + "_" + suffix, "uid": None, "gid": None} for suffix in ("a", "b")
    ]
    for entry in users:
        try:
            pwd.getpwnam(entry["name"])
        except KeyError:
            pass
        else:
            raise RuntimeError("Generated account already exists; nothing was changed")
        try:
            grp.getgrnam(entry["name"])
        except KeyError:
            pass
        else:
            raise RuntimeError("Generated group already exists; nothing was changed")
    folder.mkdir(mode=0o700)
    lock = _lock(folder)
    state = {
        "version": 1,
        "token": token,
        "root": str(root),
        "owner_uid": uid,
        "owner_gid": gid,
        "users": users,
        "pid": None,
        "start": None,
    }
    try:
        _save_state(folder, state)
        _write(folder / "hostkey", _read(root / "hostkey", uid))
        for suffix, entry in zip(("a", "b"), users, strict=True):
            _run(
                [
                    "/usr/sbin/useradd",
                    "--create-home",
                    "--user-group",
                    "--no-log-init",
                    "--shell",
                    "/bin/sh",
                    "--password",
                    "*",
                    "--comment",
                    "JupyHop M5 " + token,
                    entry["name"],
                ]
            )
            account = _account(entry, token)
            entry.update({"uid": account.pw_uid, "gid": account.pw_gid})
            _save_state(folder, state)
            home = Path(account.pw_dir)
            home.chmod(0o700)
            ssh = home / ".ssh"
            ssh.mkdir(mode=0o700, exist_ok=True)
            if ssh.is_symlink() or not ssh.is_dir():
                raise RuntimeError("Unexpected SSH directory in the new fixture home")
            ssh.chmod(0o700)
            os.chown(ssh, account.pw_uid, account.pw_gid)
            authorized = ssh / "authorized_keys"
            _write(
                authorized,
                (
                    'restrict,port-forwarding,from="127.0.0.1" '
                    + _public(root / (suffix + ".pub"), uid)
                    + "\n"
                ).encode(),
                owner=(account.pw_uid, account.pw_gid),
            )
            project = home / "project"
            project.mkdir(mode=0o700)
            os.chown(project, account.pw_uid, account.pw_gid)
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        config = folder / "sshd_config"
        _write(
            config,
            f"""Port {port}
ListenAddress 127.0.0.1
HostKey {folder}/hostkey
PidFile {folder}/sshd.pid
AuthorizedKeysFile .ssh/authorized_keys
AllowUsers {" ".join(entry["name"] for entry in users)}
PasswordAuthentication no
KbdInteractiveAuthentication no
UsePAM no
PermitRootLogin no
StrictModes yes
AllowTcpForwarding local
AllowAgentForwarding no
X11Forwarding no
PermitUserRC no
PrintMotd no
LogLevel ERROR
""".encode(),
        )
        Path("/run/sshd").mkdir(mode=0o755, exist_ok=True)
        _run(["/usr/sbin/sshd", "-t", "-f", str(config)])
        with (folder / "sshd.log").open("wb") as log:
            os.chmod(folder / "sshd.log", 0o600)
            process = subprocess.Popen(
                ["/usr/sbin/sshd", "-D", "-e", "-f", str(config)],
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
        state.update({"pid": process.pid, "start": _start(process.pid), "port": port})
        _save_state(folder, state)
        time.sleep(0.3)
        if process.poll() is not None:
            raise RuntimeError("Private sshd failed to start; no normal SSH service was touched")
        public = _public(root / "hostkey.pub", uid)
        _write(root / "known_hosts", f"[127.0.0.1]:{port} {public}\n".encode(), owner=(uid, gid))
        client = "\n".join(
            f"Host account-{suffix}\n    HostName 127.0.0.1\n    Port {port}\n    User {entry['name']}\n    IdentityFile {root / suffix}\n"
            for suffix, entry in zip(("a", "b"), users, strict=True)
        )
        client += f"\nHost *\n    IdentitiesOnly yes\n    UserKnownHostsFile {root}/known_hosts\n    GlobalKnownHostsFile /dev/null\n    StrictHostKeyChecking yes\n    BatchMode yes\n    ConnectTimeout 5\n"
        _write(root / "ssh_config", client.encode(), owner=(uid, gid))
        ready = {"version": 1, "users": users, "ssh_config": str(root / "ssh_config"), "port": port}
        _write(root / "ready.json", json.dumps(ready).encode(), owner=(uid, gid))
        print("Created two temporary users: " + ", ".join(entry["name"] for entry in users))
        print("Private loopback sshd ready; client configuration: " + str(root / "ssh_config"))
    except BaseException:
        print("Provision failed; rolling back only this fixture", file=sys.stderr)
        os.close(lock)
        lock = -1
        cleanup(root)
        raise
    finally:
        if lock >= 0:
            os.close(lock)


def _signal(pid, expected_uid, number, expected_start=None):
    try:
        descriptor = os.pidfd_open(pid, 0)
    except ProcessLookupError:
        return
    try:
        try:
            if Path(f"/proc/{pid}").stat().st_uid != expected_uid or (
                expected_start is not None and _start(pid) != expected_start
            ):
                raise RuntimeError("Process identity changed; refusing to signal it")
            signal.pidfd_send_signal(descriptor, number, None, 0)
        except (FileNotFoundError, ProcessLookupError):
            pass
        if expected_start is not None:
            if not select.select([descriptor], [], [], 2)[0]:
                signal.pidfd_send_signal(descriptor, signal.SIGKILL, None, 0)
                if not select.select([descriptor], [], [], 2)[0]:
                    raise RuntimeError(
                        "Private fixture sshd has not exited; root state was retained"
                    )
    finally:
        os.close(descriptor)


def cleanup(path):
    _privileged()
    root, token = _root(path)
    folder = RUN_BASE / (PREFIX + token)
    if not folder.exists():
        raise RuntimeError(
            "No sealed root fixture state exists; no accounts/processes were touched"
        )
    descriptor = _directory(folder, 0)
    os.close(descriptor)
    lock = _lock(folder)
    try:
        _cleanup_locked(root, token, folder)
    finally:
        os.close(lock)


def _cleanup_locked(root, token, folder):
    state = _json(_read(folder / "state.json", 0))
    expected = ["jht_" + token + "_" + suffix for suffix in ("a", "b")]
    if (
        type(state.get("version")) is not int
        or state.get("version") != 1
        or state.get("token") != token
        or state.get("root") != str(root)
        or [u.get("name") for u in state.get("users", [])] != expected
    ):
        raise RuntimeError("Root fixture state does not match the exact generated identities")
    allowed = {"state.json", "hostkey", "sshd_config", "sshd.pid", "sshd.log", "lock"}
    for entry in folder.iterdir():
        if (
            entry.name not in allowed
            and re.fullmatch(r"state-[a-f0-9]{32}\.json", entry.name) is None
        ):
            raise RuntimeError("Unexpected root fixture file; preserve state for manual inspection")
    accounts = [_account(entry, token) for entry in state["users"]]
    if state["pid"] is not None:
        _signal(state["pid"], 0, signal.SIGTERM, state["start"])
    uids = {account.pw_uid for account in accounts if account is not None}
    for number in (signal.SIGTERM, signal.SIGKILL):
        for proc in Path("/proc").iterdir():
            if proc.name.isdecimal():
                try:
                    owner = proc.stat().st_uid
                    if owner in uids:
                        _signal(int(proc.name), owner, number)
                except (FileNotFoundError, ProcessLookupError):
                    pass
        time.sleep(1)
    for account in accounts:
        if account is not None:
            _account(next(e for e in state["users"] if e["name"] == account.pw_name), token)
            _run(["/usr/sbin/userdel", "--remove", account.pw_name])
    for entry in state["users"]:
        try:
            group = grp.getgrnam(entry["name"])
        except KeyError:
            continue
        if (
            entry["gid"] is None
            or group.gr_gid != entry["gid"]
            or group.gr_mem
            or any(p.pw_gid == group.gr_gid for p in pwd.getpwall())
        ):
            raise RuntimeError("Fixture group identity/membership changed; refusing group removal")
        _run(["/usr/sbin/groupdel", entry["name"]])
    # Fixed files only; no recursive root deletion of a user-controlled tree.
    for entry in folder.iterdir():
        if entry.name.startswith("state-") and entry.name.endswith(".json"):
            entry.unlink()
    for name in ("hostkey", "sshd_config", "sshd.pid", "sshd.log", "lock", "state.json"):
        (folder / name).unlink(missing_ok=True)
    folder.rmdir()
    print("Removed only the two generated accounts/homes and the private sshd")
    print("You can now remove your temporary keys with: rm -rf -- " + str(root))


def check(path):
    root, _, uid, _ = _prepared(path)
    if os.getuid() != uid:
        raise RuntimeError("Run check as the user who prepared the fixture, without sudo")
    ready = _json(_read(root / "ready.json", uid))
    for suffix, entry in zip(("a", "b"), ready["users"], strict=True):
        result = _run(
            ["/usr/bin/ssh", "-F", str(root / "ssh_config"), "account-" + suffix, "id -u"]
        )
        if int(result) != entry["uid"] or entry["uid"] == 0:
            raise RuntimeError("SSH account identity does not match the fixture")
    print("PASS: two distinct non-root SSH accounts, offline-pinned host key, loopback only")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "provision", "check", "cleanup"))
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            print("Prepared private keys/metadata: " + str(prepare()))
            return
        if args.root is None:
            parser.error("--root is required for this action")
        {"provision": provision, "check": check, "cleanup": cleanup}[args.action](args.root)
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        print("Fixture action failed: " + str(error), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
