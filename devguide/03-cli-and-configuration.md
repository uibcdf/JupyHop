# 03 — CLI and configuration specification

> Proposed commands: not implemented and subject to refinement.

## Proposed commands

```console
jupyhop start workstation --env research --workdir '~/projects/analysis' --name analysis
jupyhop list
jupyhop list workstation
jupyhop status workstation analysis
jupyhop open workstation analysis
jupyhop stop workstation analysis
jupyhop doctor workstation
jupyhop discover workstation
```

Design `start` to print session ID and browser URL only when requested/appropriate; avoid emitting token-bearing URLs in logs, CI, telemetry, or shell history. When multiple sessions exist, commands must request an explicit session ID/name or show an interactive choice; automation uses `--session` or equivalent.

## Behavioral contract

- `start`: validate host and launcher, create one remote owned session, wait for readiness, register state, optionally open tunnel/browser. On partial failure, report whether the remote process remains running.
- `list`: show both owned managed sessions and discoverable current-user unmanaged servers, clearly labeled by origin. Aggregate from explicitly configured hosts where feasible and report incomplete discovery; never expose secrets.
- `status`: check liveness and distinguish stale registry from temporarily unreachable host.
- `discover`: inspect supported current-user Jupyter runtime metadata, validate live server endpoints, and label unmanaged/stale entries; this is best-effort, not a promise to scan every environment.
- `open`: verify the selected managed **or** authorized discovered server, create a fresh local SSH forward, and open the authenticated localhost endpoint; do not restart a healthy server. If credentials cannot safely be obtained, open the login page for explicit authentication.
- `stop`: stop only a selected **JupyHop-managed** server; refuse unmanaged servers, confirm remote process identity to avoid PID reuse hazards, then clean up owned state. Warn that kernel work may be terminated.
- `doctor`: diagnose SSH access, remote helper, Jupyter availability, process-manager support and network forwarding.

## SSH host configuration

Use ordinary `~/.ssh/config` aliases, such as:

```sshconfig
Host gateway
    HostName gateway.example.org
    User researcher

Host workstation
    HostName 192.168.1.100
    User researcher
    ProxyJump gateway
```

Do not parse or reimplement all of OpenSSH's config syntax. Invoke `ssh` with the alias and let OpenSSH resolve `Include`, `Match`, `ProxyJump`, keys and host verification.

## JupyHop configuration (proposed)

Optional local file: `~/.config/jupyhop/config.toml`. It can define friendly groups, defaults, timeouts and named *launch profiles*. SSH host connectivity remains in SSH config.

```toml
[defaults]
browser = true

[profiles.research]
# Illustrative, not a finalized config schema.
remote_python = "/home/researcher/envs/research/bin/python"
```

Avoid local configuration as the authoritative inventory for running sessions. Per-user managed session state belongs on remote hosts and must be reconnectable from another client.

## CLI UX conventions

Use clear exit codes, actionable error messages, optional JSON output for scripting, `--no-browser` for headless machines, and `--help` on every command. Non-interactive commands must never block on an unseen prompt. A safe default is to preserve sessions on tunnel failure or CLI interruption. Explicitly distinguish remote server status from local tunnel status; a client may reconnect through a new local port. Do not assume that a local SSH config alias resolves to the same route on different computers.

## Remote working directories and launchers

`--workdir` selects a directory **on the remote host**. Specify tilde handling, validation, nonexistence and permission errors, and safe argument passing for spaces/Unicode. An environment profile must resolve to a real remote Jupyter-capable Python executable; do not depend implicitly on `.bashrc` or shell aliases. Server environment and notebook kernel environments may differ. The `--env` option is a profile selector, not necessarily a Conda environment name.

## Packaging plan

Python package and executable: `jupyhop`. Use `pyproject.toml` and a console-script entry point; target a documented minimum Python version chosen after dependency review. Avoid importing JupyterLab as a mandatory **local** dependency when remote launching is sufficient.
