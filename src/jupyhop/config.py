"""Optional local launch/discovery preferences; OpenSSH owns connectivity."""

import os
import re
import stat
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jupyhop.discovery import validate_paths, validate_python
from jupyhop.protocol import _text
from jupyhop.ssh import validate_alias


@dataclass(frozen=True)
class Profile:
    server_python: str
    workdir: str = "~"


@dataclass(frozen=True)
class Host:
    profile: str | None = None
    remote_python: str = "python3"
    runtime_dirs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Config:
    profiles: dict[str, Profile] = field(default_factory=dict)
    hosts: dict[str, Host] = field(default_factory=dict)

    def profile(self, host: str, selected: str | None = None) -> Profile | None:
        name = selected if selected is not None else self.hosts.get(host, Host()).profile
        if name is None:
            return None
        if name not in self.profiles:
            raise ValueError("Unknown launch profile. Define it under [profiles.NAME] in config.")
        return self.profiles[name]

    def discovery_options(
        self, host: str, pythons: list[str] | None, paths: list[str] | None
    ) -> tuple[list[str], list[str]]:
        entry = self.hosts.get(host, Host())
        return (
            pythons or [entry.remote_python],
            validate_paths(list(dict.fromkeys([*entry.runtime_dirs, *(paths or [])]))),
        )


def _table(value: Any, limit: int) -> dict[str, Any]:
    if not isinstance(value, dict) or len(value) > limit:
        raise ValueError
    return value


def parse_config(raw: bytes) -> Config:
    try:
        if len(raw) > 65536:
            raise ValueError
        data = tomllib.loads(raw.decode("utf-8"))
        if (
            set(data) - {"version", "hosts", "profiles"}
            or type(data.get("version")) is not int
            or data["version"] != 1
        ):
            raise ValueError
        profiles = {}
        for name, value in _table(data.get("profiles", {}), 32).items():
            if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", name) is None:
                raise ValueError
            item = _table(value, 2)
            if set(item) - {"server_python", "workdir"}:
                raise ValueError
            python = validate_python(_text(item["server_python"]))
            workdir = _text(item.get("workdir", "~"))
            if workdir.startswith("~") and not (workdir == "~" or workdir.startswith("~/")):
                raise ValueError
            profiles[name] = Profile(python, workdir)
        hosts = {}
        for name, value in _table(data.get("hosts", {}), 16).items():
            validate_alias(name)
            item = _table(value, 3)
            if set(item) - {"profile", "remote_python", "runtime_dirs"}:
                raise ValueError
            profile = item.get("profile")
            if profile is not None and (not isinstance(profile, str) or profile not in profiles):
                raise ValueError
            paths = item.get("runtime_dirs", [])
            if not isinstance(paths, list):
                raise ValueError
            paths = validate_paths([_text(path) for path in paths])
            hosts[name] = Host(
                profile, validate_python(_text(item.get("remote_python", "python3"))), tuple(paths)
            )
        return Config(profiles, hosts)
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise ValueError(
            "Invalid JupyHop config. Use version = 1, [profiles.NAME] with server_python/workdir, and [hosts.SSH_ALIAS] with profile/remote_python/runtime_dirs. SSH settings and credentials are not accepted. Raw TOML was suppressed."
        ) from None


def load_config(path: Path | None = None) -> Config:
    explicit = path is not None
    if path is None:
        base = os.environ.get("XDG_CONFIG_HOME")
        if base and not os.path.isabs(base):
            raise ValueError("XDG_CONFIG_HOME must be absolute.")
        path = (
            Path(base) / "jupyhop/config.toml"
            if base
            else Path.home() / ".config/jupyhop/config.toml"
        )
    try:
        descriptor = os.open(path.expanduser(), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        if not explicit:
            return Config()
        raise ValueError("Explicit JupyHop config file does not exist.") from None
    except OSError:
        raise ValueError(
            "Cannot open JupyHop config; use a readable regular file, not a symlink."
        ) from None
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.getuid()
            or before.st_mode & 0o022
            or before.st_nlink != 1
            or before.st_size > 65536
        ):
            raise ValueError(
                "JupyHop config must be an owned regular single-link file, at most 64 KiB, without group/other write access."
            )
        content = bytearray()
        while len(content) <= 65536:
            chunk = os.read(descriptor, min(4096, 65537 - len(content)))
            if not chunk:
                break
            content.extend(chunk)
        after = os.fstat(descriptor)
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError("JupyHop config changed while being read; retry.")
        return parse_config(bytes(content))
    finally:
        os.close(descriptor)
