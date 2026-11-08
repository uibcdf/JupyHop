# 04 — Security and reliability

## Threat model

Jupyter grants code execution as the account running its server. Risks include accidental public exposure, leaked authentication URLs, spoofed SSH hosts, incorrect process ownership, remote command injection, stale PID reuse, privilege escalation, and access across OS accounts.

## Mandatory controls

1. **Transport:** use OpenSSH with normal host-key checking; never turn off `StrictHostKeyChecking` automatically. Respect user-supplied ProxyJump aliases.
2. **Binding:** remote Jupyter binds to loopback only; local forwards also bind to loopback. No blanket firewall changes, no direct public Jupyter ports.
3. **Authentication:** preserve supported Jupyter Server token/password authentication. A tunnel is transport protection, not a reason to disable Jupyter auth.
4. **Authorization:** all remote helper actions run as the authenticated Unix account; no shared service account, sudo, or other-user process enumeration in MVP.
5. **Secrets:** never commit, log, print in diagnostic JSON, or persist Jupyter tokens/URLs containing tokens in plaintext. Use short-lived secure access where needed, and carefully design how a newly connected client obtains authentication to an existing session.
6. **Process safety:** no `pkill jupyter`, PID-only termination, or killing arbitrary unmanaged servers. Validate process identity and managed ownership.
7. **Filesystem:** secure per-user state permissions (directories 0700, secret files 0600 if unavoidable), atomic writes, no symlink-following vulnerabilities.
8. **Input safety:** avoid `shell=True` and shell-formatted untrusted strings; validate session names and launcher paths, handle SSH argument injection.
9. **Privacy:** sanitize help output, tracebacks, logs, telemetry and docs. No phone-home or analytics by default.
10. **Institutional policy:** local policies govern access to hosts and use of bastions; tool must not bypass them.

## Authentication design decision pending

Opening an existing server from a second client requires a legitimate way to authenticate without leaking a token. Evaluate Jupyter Server's supported runtime/API behavior and restrictive remote-only token access before selecting a design. Do not claim this is solved simply by forwarding the port.

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

## Security release gate

Before any stable release, run a security review covering host-key enforcement, auth handling, session ownership, port binding, subprocess quoting, file permissions, logging redaction, and cleanup under signal/connection failure.
