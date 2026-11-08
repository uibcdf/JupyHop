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

M0 selected normal Jupyter login through a token-free URL as the safe baseline.
No JupyHop credential cache or automatic browser token transfer is implemented.
The following requirements govern future automation; see the
[M0 threat/tradeoff evaluation](13-m0-validation.md).

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
