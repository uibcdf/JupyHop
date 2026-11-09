# 03 — CLI and configuration specification

> `doctor` ships in M1; `discover`, `list HOST` and foreground `open` ship in M2.
> M3 adds `start` and managed provenance; see [the current exact contract](17-m3-managed-launch.md).
> M4 adds `status HOST [UUID]` and `stop HOST UUID [--yes]`;
> [the current lifecycle contract](18-m4-lifecycle.md) supersedes proposals below.
> M5 adds `--env`, optional TOML v1, `list [HOST ...]`, hostless `open` and
> `archive HOST UUID`; see [the current M5 contract](19-m5-scientific-workflows.md).

M3 now implements `start` using `--server-python`, `--workdir`, `--name`,
`--password-stdin`, `--no-open` and the attached browser/no-browser flow. Its
[exact contract](17-m3-managed-launch.md) supersedes proposed `start` examples
below. Named `--env` profiles and multi-host inventory ship in M5; name-based
session resolution remains unimplemented. Discovery/list/open distinguish origin.

`status` observes managed records and reconciles interrupted launch readiness.
`stop` accepts only an exact managed UUID, confirms kernel termination (or
requires `--yes`), and sends SIGTERM through a verified pinned descriptor. It
retains records/settings. Explicit `archive` moves inactive records/evidence,
releases the active name/budget, and preserves possible orphaned-kernel data.
Automatic deletion remains unimplemented.

## Implemented commands

```console
jupyhop start workstation --env research --workdir '~/projects/analysis' --name analysis
jupyhop list
jupyhop list workstation
jupyhop status workstation SESSION_ID
jupyhop open workstation SESSION_ID
jupyhop stop workstation SESSION_ID
jupyhop archive workstation SESSION_ID
jupyhop list workstation-a workstation-b --json
jupyhop open
jupyhop doctor workstation
jupyhop discover workstation
```

Design `start` to print session ID and browser URL only when requested/appropriate; avoid emitting token-bearing URLs in logs, CI, telemetry, or shell history. For `open host`: zero candidates means no result (with coverage diagnostic); one validated candidate may be opened directly; multiple candidates require a TTY selection or explicit ID. For `stop`: never infer which managed session to terminate when ambiguous, and refuse unmanaged candidates. Noninteractive callers require explicit IDs. See [12](12-user-experience.md).

## Behavioral contract

- `start`: validate host and launcher, create one remote owned session, wait for readiness, register state, optionally open tunnel/browser. On partial failure, report whether the remote process remains running.
- `list`: show both owned managed sessions and discoverable current-user unmanaged servers, clearly labeled by origin. Aggregate from explicitly configured hosts where feasible and report incomplete discovery; never expose secrets.
- `status`: check liveness and distinguish stale registry from temporarily unreachable host.
- `discover`: inspect supported current-user Jupyter runtime metadata, validate live server endpoints, and label unmanaged/stale entries; this is best-effort, not a promise to scan every environment.
- `open`: verify the selected managed **or** authorized discovered server, create a fresh local SSH forward, and open the authenticated localhost endpoint; do not restart a healthy server. If credentials cannot safely be obtained, open the login page for explicit authentication.
- `stop`: stop only a selected **JupyHop-managed** server; refuse unmanaged servers,
  verify the pinned process identity and warn about kernel termination. Retain
  owned state; explicit archive requires observed inactivity and moves evidence.
- `archive`: exact managed UUID plus confirmation/--yes; refuse live/unconfirmed
  identities, preserve evidence and release the active name/budget. No deletion.
- `doctor`: diagnose SSH access, remote helper, Jupyter availability, process-manager support and network forwarding.

## SSH host configuration

Use ordinary `~/.ssh/config` aliases, such as:

```sshconfig
Host gateway
    HostName gateway.example.org
    User researcher

Host workstation
    HostName workstation.example.org
    User researcher
    ProxyJump gateway
```

Do not parse or reimplement all of OpenSSH's config syntax. Invoke `ssh` with the alias and let OpenSSH resolve `Include`, `Match`, `ProxyJump`, keys and host verification.

Native SSH password/passphrase prompts are supported when a controlling terminal
is available. --batch or headless operation requires noninteractive access.
--ssh-auth-timeout bounds terminal authentication (default 120 seconds, 1–600);
--timeout keeps the separate probe/network bounds. No SSH-password argument or
JupyHop credential cache exists; --password-stdin is only the new Jupyter password.
An invocation reuses only its own verified foreground master per route, including
for the forward's final identity check. See [D45](23-02-stabilization-evidence.md).

## JupyHop configuration v1

Optional `$XDG_CONFIG_HOME/jupyhop/config.toml` (default
`~/.config/jupyhop/config.toml`) or per-command `--config FILE`. It must be an
owned regular single-link file, at most 64 KiB, without group/other write access;
final symlinks are refused. Missing defaults are optional; an explicit missing
file is an error. Unknown keys/schema and malformed TOML fail before SSH, without
echoing raw content. No credentials, host addresses, users or shell commands.

```toml
version = 1
[profiles.research]
server_python = "/absolute/remote/env/bin/python"
workdir = "~/project"
[hosts.workstation]
profile = "research"
remote_python = "python3"
runtime_dirs = ["~/custom-runtime"]
```

Avoid local configuration as the authoritative inventory for running sessions. Per-user managed session state belongs on remote hosts and must be reconnectable from another client.

At most 32 profiles and 16 hosts. CLI server Python/workdir override selected
profile values; explicit `--env` overrides the host's default profile. Helper
Python is separate: CLI overrides host `remote_python`, then defaults to python3.
CLI runtime paths are merged with per-host paths (maximum 16). Environment
activation hooks and named host groups are not implemented.

`list` has a stable local version-1 inventory envelope containing per-host success
or error reports, even for one host; this replaces its M2 single-host alias shape.
Use `discover HOST` for that original report. List exit 0 means every selected
host was inspected, 14 means some failed, 3 means all failed; discovery remains
partial. Sequential per-host deadlines bound each request. Hostless open uses
configured aliases; ambiguity requires TTY selection or explicit `open HOST ID`.

## CLI UX conventions

Use clear exit codes, actionable error messages, optional JSON output for scripting, `--no-browser` for headless machines, and `--help` on every command. Non-interactive commands must never block on an unseen prompt. A safe default is to preserve sessions on tunnel failure or CLI interruption. Explicitly distinguish remote server status from local tunnel status; a client may reconnect through a new local port. Do not assume that a local SSH config alias resolves to the same route on different computers.

## Remote working directories and launchers

`--workdir` selects a directory **on the remote host**. Specify tilde handling, validation, nonexistence and permission errors, and safe argument passing for spaces/Unicode. An environment profile must resolve to a real remote Jupyter-capable Python executable; do not depend implicitly on `.bashrc` or shell aliases. Server environment and notebook kernel environments may differ. The `--env` option is a profile selector, not necessarily a Conda environment name.

## Tunnel process and compatibility UX

`open` owns a fresh foreground SSH forward; repeated opens have independent ports
and processes. Ctrl-C, SIGTERM or terminal hangup closes that forward without
stopping remote Jupyter. Browser/tunnel closure and independent reconnect are
tested; suspend/resume and CLI upgrade during an attached session remain future
acceptance cases. Simple ASCII `base_url` works; IPv6-only and HTTPS are currently
unsupported. Never disable TLS/SSH checks as a fallback. See
[11](11-discovery-and-connectivity.md).

## Packaging plan

Python package and executable: `jupyhop`. M1 implements `pyproject.toml` and a
console-script entry point, with Python 3.11–3.14 support and zero mandatory
Python runtime dependencies. JupyterLab is not a mandatory local dependency.
