# 12 — User experience and CLI contract

> **Session UX contract.** [M2](16-m2-existing-servers.md) implements existing-server
> discovery/open with normal Jupyter login and attached foreground tunnels.
> M3 adds managed launch; [M4](18-m4-lifecycle.md) adds status/stop/reconnection.

M3 implements [managed start/readiness](17-m3-managed-launch.md) with password
prompt/protected stdin, explicit server Python/workdir, no-open and attached
browser flows. M4 implements managed status and verified stop with exact UUIDs;
M5 adds named executable/workdir profiles, multi-host inventory/selection and
inactive-record archive. Name-based session resolution remains unimplemented.

M6's [quickstart](../docs/quickstart.md), [troubleshooting](../docs/troubleshooting.md)
and [compatibility policy](../docs/compatibility.md) give the beta's current user
workflow. Private password prompts refuse echo fallback. SIGTERM/SIGHUP closes
owned transport during probes as well as attached open; interrupted remote writes
still require reconciliation. No port or tunnel configuration is added to the
normal existing-server flow.

## Two levels of experience

### Simple mode: open an existing server

Prerequisites: the user already has a working OpenSSH alias; the current remote OS account has an authorized Jupyter Server whose runtime information is discoverable.

```console
jupyhop open workstation
```

Expected: connect using OpenSSH, find validated candidates, choose only if ambiguous, establish a local loopback forward and open an authenticated browser view. If auth requires a password, ask the user to log in normally; if discovery is incomplete, say so clearly.

No mandatory TOML config, manually selected port range, server daemon or admin
account is required in the supported case. The helper needs an existing Linux
Python >=3.11 and `/proc`; managed launch additionally needs tmux and a selected
Jupyter Server 2 environment. No promise of zero remote prerequisites is made.

### Advanced mode: launch and manage

```console
jupyhop start workstation --server-python /absolute/env/bin/python --workdir '~/projects/project-a' --name analysis
jupyhop list workstation
jupyhop status workstation SESSION_ID
jupyhop open workstation SESSION_ID
jupyhop stop workstation SESSION_ID
jupyhop archive workstation SESSION_ID
jupyhop list workstation-a workstation-b --json
jupyhop doctor workstation
```

`--server-python` selects an existing remote Python; workdir is validated remotely.
Named `--env` profiles use optional TOML v1; CLI values override profile defaults.
`list` without aliases uses configured hosts; hostless `open` selects across those
routes. Ambiguity requires a terminal or explicit `open HOST ID`. Stop warns about terminating kernels and needs
confirmation or explicit `--yes`. It cannot select by name, PID or unmanaged ID.
The server kernel list can differ from its launcher environment. Never silently
install or activate arbitrary environments.

Archive needs the same exact-UUID confirmation policy and proof of inactivity.
It moves private evidence without deleting data, releases the active name and
record budget, and never stops orphaned kernels. Unconfirmed/live state is refused.
List JSON uses a version-1 per-host envelope and exit 14 for partial host failures;
`discover HOST` retains the original single-host report. No route repair/relay is
attempted, and one failed host does not hide results from reachable aliases.

## Selection and ambiguity rules

- **Zero candidates:** distinguish complete empty result from incomplete discovery/unreachable host; provide diagnosis and next steps.
- **One valid candidate:** `open host` may select it automatically.
- **Multiple candidates:** interactive picker on a TTY; noninteractive calls return an ambiguity error with safe identifiers, not a random selection.
- **Unmanaged candidate:** open if authorized; refuse `stop`.
- **`stop host`:** always require an exact managed UUID and confirmation (or
  explicit `--yes`); never infer a selection, even for a single server.
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

A new Linux user with working SSH access should be able to complete M2 discovery/open with only the documented prerequisites. Additional tests: one vs multiple servers, two accounts, two clients, duplicate aliases, browser not installed, SSH passphrase prompt, custom base URL, resume from laptop suspend, and simultaneous workstation-a/workstation-b sessions with no fixed local port allocation.

## Documentation deliverables

Quickstart (existing servers first), how-to start persistent managed sessions, SSH/ProxyJump examples, environment/workdir profiles, session ownership and explicit stop rules, security limits, troubleshooting, migration from fixed `LocalForward` configurations, and known unsupported situations.

See [CLI specification](03-cli-and-configuration.md), [scenario matrix](08-scenarios-and-acceptance.md) and [roadmap](06-roadmap.md).
