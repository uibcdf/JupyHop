# 02 — Architecture

## Proposed system

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

**Remote helper (design pending):** start/list/status/stop owned JupyHop processes, plus best-effort discovery of authorized unmanaged Jupyter Servers and emit machine-readable, versioned output. It runs with the existing remote user's permissions.

**Process manager (design pending):** keep servers running after SSH closes. Compare `systemd --user` (user service availability, linger constraints) with `tmux` or a controlled detached process strategy. Do not assume `loginctl enable-linger` is allowed.

**Session registry:** store minimal metadata on remote per-user storage so a different laptop can discover it. Candidate: `~/.local/state/jupyhop/` with restrictive permissions and atomic updates; use stable random session IDs and record host-local server address, process identity and start time. Registry entries are untrusted until the process/endpoint is verified.

## State, ownership, and discovery

Remote host is the source of truth for managed sessions; clients keep only optional local convenience state. Existing manually launched Jupyter servers may be discovered via supported current-user Jupyter runtime metadata, and must remain read-only for lifecycle operations. Discovery is not exhaustive across independent Jupyter runtime directories/environments. Use the authenticated SSH identity as the remote principal. Neither session IDs nor PID files alone establish ownership. Handle stale entries after crashes and distinguish managed/unmanaged processes.

A **managed server** has states such as `starting`, `running`, `unreachable`, `stopping`, `stopped`, and `stale`. Define state transitions, timeouts and idempotent recovery before implementation.

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
