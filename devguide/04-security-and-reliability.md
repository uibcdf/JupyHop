# 04 — Security and reliability

## Threat model

Jupyter grants code execution as the account running its server. Risks include accidental public exposure, leaked authentication URLs, spoofed SSH hosts, incorrect process ownership, remote command injection, stale PID reuse, privilege escalation, and access across OS accounts.

## Mandatory controls

1. **Transport:** use OpenSSH with normal host-key checking; never turn off `StrictHostKeyChecking` automatically. Respect user-supplied ProxyJump aliases.
2. **Binding:** remote Jupyter binds to loopback only; local forwards also bind to loopback. No blanket firewall changes, no direct public Jupyter ports.
3. **Authentication:** preserve supported Jupyter Server token/password authentication. A tunnel is transport protection, not a reason to disable Jupyter auth.
4. **Authorization:** all remote helper actions run as the authenticated Unix account; no shared service account, sudo, or other-user process enumeration in MVP.
5. **Secrets:** never commit, log, or expose Jupyter tokens/URLs containing tokens, passwords, private keys, or cookies in ordinary diagnostics/JSON. **No unprotected plaintext credential persistence.** If persistence is necessary, permit only a separately reviewed, remote-account-restricted design (e.g. mode 0600, appropriate lifetime and cleanup) after documenting threats and tradeoffs; do not treat filesystem permissions as encryption. Establish how a second authorized client authenticates.
6. **Process safety:** no `pkill jupyter`, PID-only termination, or killing arbitrary unmanaged servers. Validate process identity and managed ownership.
7. **Filesystem:** secure per-user state permissions (directories 0700, secret files 0600 if unavoidable), atomic writes, no symlink-following vulnerabilities.
8. **Input safety:** avoid `shell=True` and shell-formatted untrusted strings; validate session names and launcher paths, handle SSH argument injection.
9. **Privacy:** sanitize help output, tracebacks, logs, telemetry and docs. No phone-home or analytics by default.
10. **Institutional policy:** local policies govern access to hosts and use of bastions; tool must not bypass them.

## Authorization boundary for unmanaged discovery

JupyHop may inspect only Jupyter runtime data available to the authenticated remote Unix user. A discovered server is not automatically managed: users may connect if verified and authorized, but `stop`/restart must refuse it. Do not assume that a port or PID identifies an authorized Jupyter process. SSH tunnels must preserve remote and local loopback binding, supported base paths, and Jupyter authentication.

## Authentication baseline and pending browser automation

SSH authentication is delegated to native OpenSSH terminal prompts or keys/agent.
Python never reads or stores the SSH password. --batch/headless is noninteractive.
Invocation-private foreground control sockets carry only that invocation's RPCs
and explicit forwards, with PID verification and no network fallback if lost.
Normal signal/timeout cleanup is tested with native controlling terminals and
ProxyJump. Individual MFA configurations still need separate evidence. See
[D45 and its alternatives](23-02-stabilization-evidence.md).

M0 selected normal Jupyter login through a token-free URL as the safe baseline.
No JupyHop credential cache or automatic browser token transfer is implemented.
M2 validates current UID/process/socket ownership and uses explicit login with
verified IPv4 loopback forwarding. Read the
[implemented controls and remaining limits](16-m2-existing-servers.md).
The following requirements govern future automation; see the
[M0 threat/tradeoff evaluation](13-m0-validation.md).

M3's [reviewed new-session policy](17-m3-managed-launch.md) uses a separately
chosen password over encrypted stdin and a native Argon2 hash in private remote
settings (0600 under 0700 directories). No plaintext password cache or token
handoff is introduced. Registry provenance and compatible schema are verified
before managed state is trusted or written. M4 allows stop only after explicit
UUID confirmation and pinned identity checks; see [18](18-m4-lifecycle.md).
The Linux pidfd is opened before identity checks and receives graceful SIGTERM.
No PID-only fallback, tmux kill, SIGKILL escalation or credential retrieval is
used. An interrupted stop retains intent; retry revalidates it. State/settings
are retained rather than risk deleting recovery evidence for orphaned kernels.

M5's [archive policy](19-m5-scientific-workflows.md) moves only a verified inactive
session directory under the same private registry. It releases the active name
and record budget, preserves hashes/connection evidence and never deletes files
or stops orphaned kernels. A live PID/start identity, a live runner at the exact
state path, any live private tmux pane or an unconfirmed pre-PID launch blocks
retirement. Compatibility, ownership, no-symlink parsing and locking still apply.

Optional local TOML is bounded, owned, single-link and not writable by group/other;
raw parse errors and unknown fields are suppressed. It accepts no credentials or
shell fragments. OpenSSH owns connectivity. Tests isolate XDG configuration from
the developer's preferences. Two actual temporary Unix accounts have separately
verified discovery/read/open/stop/archive isolation and Jupyter login rejection.
The explicitly privileged account fixture is development tooling; the product
never creates users, requires sudo or modifies a normal SSH service.

Opening an existing server from a second client requires a legitimate way to authenticate without leaking a token. It must support a fall back to interactive login for servers whose credentials cannot be safely retrieved. Jupyter-auth URLs must not appear in shell history, diagnostics, JSON results or general logs; the browser flow has its own exposure considerations. Evaluate Jupyter Server's supported runtime/API behavior and restrictive remote-only token access before selecting a design. Do not claim this is solved simply by forwarding the port.

## Separate lifetimes

Client SSH connection, local tunnel, remote Jupyter Server and kernel process are different resources. A failed forward must not stop a server. Reconnecting to an alive server does not guarantee a kernel survived a server crash. No design promises in-memory kernel recovery across a host reboot. Process-manager selection must consider `systemd --user` session/linger limitations and tmux fallback; never enable lingering or request sudo implicitly.

## Failure and recovery matrix

| Event | Required behavior |
| --- | --- |
| Client SSH tunnel closes | Remote server stays up; reconnect creates a new tunnel |
| Client port unavailable | Choose a different local port without touching remote state |
| Remote process exits | Mark session stopped/stale; do not pretend it is running |
| Host temporarily unreachable | Report unreachable, not stopped; retain registry |
| Host reboot | Detect stale sessions; optionally offer explicit restart, never silently do so |
| Two simultaneous starts | Prevent session-name collisions and inconsistent registry updates |
| Stop interrupted | Reconcile actual process state on next query |
| Authentication fails | Do not disable Jupyter authentication as a workaround |
| ProxyJump fails | Surface SSH error and preserve remote state |
| Malformed remote output | Fail safely without interpreting it as shell code |

## Reliability requirements

Session start/stop should be idempotent where possible; use bounded readiness checks and meaningful timeouts. Keep process lifetime separate from tunnel lifetime. Document behavior on host reboot (persistence does not automatically mean auto-restart after reboot).

## Versioning, helpers and client-boundary checks

If a remote helper is needed, it must have authenticated/verified bootstrap, compatible control protocol, and safe updates that do not restart scientific workloads. Tunnel listeners must be verified as JupyHop-owned before reuse/cleanup. Custom HTTPS and IPv6 must fail safely if unsupported. See [10](10-remote-runtime-and-protocol.md) and [11](11-discovery-and-connectivity.md).

## Security release gate

Before any stable release, run a security review covering host-key enforcement, auth handling, session ownership, port binding, subprocess quoting, file permissions, logging redaction, and cleanup under signal/connection failure.

M6's [internal review and evidence](20-m6-beta-readiness.md) covers these boundaries
for the beta. Command-wide SIGTERM/SIGHUP unwinds owned probes as well as forwards;
password prompts refuse echo fallback. Atomic record replacement has a bounded
reopen path; no bytes from an unlinked inode are accepted and all checks apply
again. This is not an independent audit. The installed client, local OpenSSH
configuration, chosen remote Python and authenticated account are trusted; root
and malicious same-UID processes are outside this boundary. See
[SECURITY](../SECURITY.md) for reporting and [compatibility](../docs/compatibility.md)
for the supported scope. Publication is separate from preparing tested artifacts.
