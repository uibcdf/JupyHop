# 02 — Architecture

## Proposed system

M1 implements the local package/CLI, bounded OpenSSH execution and read-only
doctor probe. M2 adds read-only runtime discovery, process/socket ownership
checks and foreground-owned forwarding/open. See [16](16-m2-existing-servers.md).
Neither an installed remote helper nor a managed registry is needed by M2.

M3 adds an immutable per-session runner, private tmux launch and a versioned
per-host/account registry. See [17](17-m3-managed-launch.md) for the exact state,
auth and bootstrap contract. M4 adds [managed status/reconciliation, pinned
graceful stop and independent-client kernel continuity](18-m4-lifecycle.md).

```text
Client machine
  jupyhop CLI
    |-- reads SSH host aliases
    |-- remote command execution via OpenSSH
    |-- local SSH forwarding (lifecycle owned by client)
    |-- opens authenticated localhost URL
    |
    +--> SSH direct or ProxyJump --> Remote Linux host (current OS user)
                                        |-- JupyHop remote helper
                                        |-- per-user session registry
                                        |-- user-level process manager
                                        +-- Jupyter Server (127.0.0.1) --> kernels
```

No central service or inter-user privileged daemon is required.

## Component responsibilities

**Local CLI:** parse commands, resolve user-facing host/session selections, invoke SSH, select a free local port and establish forwarding, open browser, and report failures.

**SSH transport:** delegate authentication, host verification, proxy jumps, and crypto settings to OpenSSH. Use subprocess argument arrays rather than shell-interpolated user input.

**Remote source RPC:** start/status/stop owned processes, plus read-only discovery
of current-user Jupyter Servers. Versioned stdlib source travels through SSH
stdin; no installed helper package. Lifecycle RPC is wire 1.3.

**Process manager:** private tmux per session; no automatic restart. The tested
no-PAM SSH context has no user manager. OS logout/cgroup policy remains an
external prerequisite; no linger or bus configuration is changed. A systemd
backend needs its own acceptance fixture before being offered.

**Session registry:** host/account-scoped XDG state (default below
`~/.local/state/jupyhop/`) with private permissions, locking and atomic updates.
Stable random IDs record endpoint/process/runner identity. Entries are untrusted
until identity is verified. Terminal records/settings are retained within the
128-record bound; cleanup/name reuse is not yet implemented.

## State, ownership, and discovery

Remote host is the source of truth for managed sessions; clients keep only optional local convenience state. Existing manually launched Jupyter servers may be discovered via supported current-user Jupyter runtime metadata, and must remain read-only for lifecycle operations. Discovery is not exhaustive across independent Jupyter runtime directories/environments. Use the authenticated SSH identity as the remote principal. Neither session IDs nor PID files alone establish ownership. Handle stale entries after crashes and distinguish managed/unmanaged processes.

A **managed observation** is `starting`, `ready`, `unreachable`, `stopping`,
`stopped`, `failed` or `stale`. Stored schema 1.0 launch states and additive stop
intent remain separate from observations; see [18](18-m4-lifecycle.md).

## Network and forwarding

Jupyter binds to remote `127.0.0.1` and a dynamically allocated remote port. The client creates a local forward bound to local loopback. OpenSSH should report failures promptly (`ExitOnForwardFailure=yes`). Avoid a naive 'check free port, then use it' race; verify the actual tunnel listener and resolve collisions safely. Two clients can connect to the same remote session through distinct local ports.

SSH forwarding and WebSocket traffic must be tested with JupyterLab, kernels, and ProxyJump. The lifecycle of the client tunnel, remote Jupyter server and kernel are independent. A forward closing must not stop the server; a host reboot cannot preserve in-memory kernel state. See [09](09-session-lifecycle-and-auth.md).

## Environments

Separate the environment running the JupyHop helper from the environment running Jupyter. A user-selected `--workdir` must be validated and interpreted on the remote machine, never the client. Support literal whitespace/Unicode paths and define remote tilde expansion. A configured remote launcher (e.g. absolute environment Python plus `-m jupyterlab`) can avoid relying on interactive shell initialization. Explicitly check whether Jupyter Server and the selected kernels are installed.

## Platform assumptions

Initial supported target: Linux remote hosts with OpenSSH and Python. Client support target: Linux first, other desktop platforms after testing. Avoid assuming a specific shell, Conda path, hostname, port range, or hospital network.

## Extendability boundaries

Define a transport interface and a launcher/process-manager interface only when there are at least two real implementations or clear tests demonstrating the need. A future Slurm backend is responsible for job submission, cancellation, node allocation and forwarding through cluster topology; it must not treat a login node as the compute node.

## Reference scenarios

The topology, LAN vs bastion routing, concurrent clients, manually launched Jupyter, and failure expectations are specified in [08 — Scenario catalogue](08-scenarios-and-acceptance.md). Implementations must treat reachability as directional and rely on the actual client's OpenSSH configuration, not assumptions about network location.

## Remote runtime and compatibility

Choose the minimal M2 remote probing method before requiring helper installation. For M3/M4, document a user-space bootstrap, versioned protocol and safe upgrade path; a new client must not corrupt old remote state or terminate active kernels. See [10](10-remote-runtime-and-protocol.md).

## Open architecture questions

See [07 — Decisions](07-decisions.md), [11 — Discovery and connectivity](11-discovery-and-connectivity.md), and [12 — UX](12-user-experience.md): remote helper bootstrap, process manager (systemd --user vs tmux fallback), registry schema, Jupyter auth URL handling, local tunnel lifecycle, and concurrency model. No process manager may require automatic elevation or enabling linger.
