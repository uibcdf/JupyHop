# 12 — User experience and CLI contract

> **Planned UX, not implemented commands.** The main quality bar is fewer steps than managing Jupyter and SSH tunnels manually.

## Two levels of experience

### Simple mode: open an existing server

Prerequisites: the user already has a working OpenSSH alias; the current remote OS account has an authorized Jupyter Server whose runtime information is discoverable.

```console
jupyhop open workstation
```

Expected: connect using OpenSSH, find validated candidates, choose only if ambiguous, establish a local loopback forward and open an authenticated browser view. If auth requires a password, ask the user to log in normally; if discovery is incomplete, say so clearly.

No mandatory TOML config, manually selected port range, server daemon or admin account should be required in the common case. The exact remote Python/helper prerequisite is an M0 spike, not a promise that absolutely no remote setup is needed.

### Advanced mode: launch and manage

```console
jupyhop start workstation --env research --workdir '~/projects/project-a' --name analysis
jupyhop list workstation
jupyhop status workstation analysis
jupyhop open workstation analysis
jupyhop stop workstation analysis
jupyhop doctor workstation
```

`--env` refers to a documented remote launch profile; the remote working directory is validated on the remote machine. The server kernel list can differ from its launcher environment. Never silently install or activate arbitrary environments.

## Selection and ambiguity rules

- **Zero candidates:** distinguish complete empty result from incomplete discovery/unreachable host; provide diagnosis and next steps.
- **One valid candidate:** `open host` may select it automatically.
- **Multiple candidates:** interactive picker on a TTY; noninteractive calls return an ambiguity error with safe identifiers, not a random selection.
- **Unmanaged candidate:** open if authorized; refuse `stop`.
- **`stop host` with multiple managed sessions:** never guess. Require ID/name or an explicit user selection with confirmation.
- **Name collisions:** display session ID and host/account context; refuse unsafe ambiguous resolution.
- **Idempotent open:** never restart an already-running remote server just to create a tunnel.
- **Missing browser:** `--no-browser` provides a documented headless method without printing secrets in generic diagnostics.
- **Network change:** clearly indicate whether SSH cannot reach the target; don't pretend remote server is stopped.

## Tunnel lifecycle UX — design decision

The user must know whether `jupyhop open` blocks to keep a forward alive, detaches a managed local forward, or uses a control socket. Define `jupyhop tunnels` / `jupyhop close` only if necessary after testing. A browser open must not implicitly kill a foreground tunnel or leave untracked background tunnels. Explain precisely the effect of terminal close, Ctrl-C, laptop suspend and repeated opens. Never close unrelated SSH processes.

## Diagnostics and scripting

- Stable exit codes for: bad input; SSH unreachable/host trust failure; remote prerequisites missing; zero/incomplete discovery; ambiguous selection; authentication required; forward failure; incompatible protocol; permission denial.
- Human-readable errors with concrete recovery suggestions, and bounded optional structured `--json` output with no credentials.
- Progress and diagnostics go to stderr; machine-readable stdout remains parseable.
- `doctor` distinguishes client SSH failure from remote Jupyter missing, runtime path unsupported, no process manager and version mismatch.
- Noninteractive mode must never block on an invisible selection or confirmation prompt.
- On interrupted start, report that remote session state may require reconciliation rather than claiming it stopped.

## Zero-config principle and advanced config

OpenSSH remains the source of truth for hosts and authentication. An optional user config (`~/.config/jupyhop/config.toml`) is for friendly groups, defaults, explicit extra runtime directories and launch profiles, not another SSH database. Do not require duplicate host IPs or credentials.

State stored on a client is convenience-only; the remote current-user managed registry is authoritative for managed servers so that another client can reconnect. Custom session discovery settings must be documented for another client to reproduce if they are only stored locally.

## Usability tests

A new Linux user with working SSH access should be able to complete M2 discovery/open with only the documented prerequisites. Additional tests: one vs multiple servers, two accounts, two clients, duplicate aliases, browser not installed, SSH passphrase prompt, custom base URL, resume from laptop suspend, and simultaneous Nauta/Spika sessions with no fixed local port allocation.

## Documentation deliverables

Quickstart (existing servers first), how-to start persistent managed sessions, SSH/ProxyJump examples, environment/workdir profiles, session ownership and explicit stop rules, security limits, troubleshooting, migration from fixed `LocalForward` configurations, and known unsupported situations.

See [CLI specification](03-cli-and-configuration.md), [scenario matrix](08-scenarios-and-acceptance.md) and [roadmap](06-roadmap.md).
