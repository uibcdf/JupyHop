# 10 — Remote runtime and protocol

> **Lifecycle design specification.** M1 implements only the no-install read-only
> [doctor probe and protocol](15-m1-foundations.md). Lifecycle helpers/registries
> are not implemented. The MVP must remain usable without root access, a mandatory
> always-on coordinator, or installing JupyterHub.

## Goal and constraints

A user who can run `ssh workstation` should be able to discover and open a current-user Jupyter Server with minimal additional setup. The implementation must explicitly separate what is needed for **discovery/open (M2)** from what is needed for **managed launch/lifecycle (M3–M4)**.

## Remote execution approaches — decision spike

| Approach | Advantages | Limitations |
| --- | --- | --- |
| SSH invoking existing Python/Jupyter tools | Little or no remote installation for simple discovery | Python/module availability and version variability |
| Minimal versioned remote helper, installed in user space | Stable protocol, reusable validation and state management | Bootstrap, updates, Python compatibility |
| On-demand copy/execution of helper | Client-first install; compatible with bastions | Integrity verification, caching, update/race and remote execution security |

**Preferred investigation order:** first test M2 discovery with existing runtime data and remote commands; if too fragile, introduce a minimal helper. M3/M4 may require a helper even if M2 does not. Avoid making an installed remote package mandatory for the first useful `open` workflow unless a prototype demonstrates the need.

## Bootstrap and runtime detection

1. SSH to the target alias using the user's OpenSSH configuration, respecting host-key verification.
2. Probe available remote Python and Jupyter Server **without modifying the host**.
3. If a helper is required, verify compatible versions; document an explicit user-space install/bootstrap path, integrity checks and cache location.
4. Run as the authenticated remote Unix user; never use `sudo`, modify global SSH configuration or enable systemd linger automatically.
5. Fail with an actionable diagnostic when execution prerequisites are absent; never silently install scientific dependencies or select an unrelated environment.

Specify a minimum Python version after testing; remote Jupyter installation may be in a different environment from the helper. Paths must not depend on activating an interactive shell.

## Protocol contract (proposed)

If a helper is used, its control channel is SSH **stdout** carrying versioned, bounded, machine-readable JSON, with human diagnostics on **stderr**. SSH exit code and a structured status together describe success/failure. M1 freezes only the doctor protocol in [15](15-m1-foundations.md); lifecycle wire schemas remain pending before M3/M4.

Minimum operations: `capabilities`, `discover`, `status`; later `start`, `stop`, and managed-session reconciliation. A record must distinguish `managed`, `unmanaged`, `stale`, `unreachable`, and `unsupported` without conflating them.

Minimum nonsecret fields: protocol/schema version, host-scoped opaque session ID, origin/provenance, display name, remote account context, runtime directory source, server address family/port/base URL, launcher/profile reference when applicable, and validated state. **Never include tokens, passwords, cookies, private keys or token-bearing URLs in generic list/JSON output.** Use an explicitly secured authentication path for opening a server.

## Versioning and compatibility

- Use protocol major/minor version negotiation. Reject incompatible major versions clearly; gracefully handle missing optional minor-version fields.
- Treat remote registry schema and wire protocol versions separately.
- Older clients must not corrupt a newer registry; writes require compatibility checks.
- A client upgrade must not stop running remote servers, replace their environment, or silently reinstall a remote helper.
- Helper deployment must be safe under simultaneous clients: verified file integrity, atomic replacement, no execution from untrusted writable directories.
- Provide a troubleshooting path for mismatched versions and an explicit opt-in update command if a helper is installed.

## Process ownership and remote state

The helper acts only on the current Unix account's JupyHop-managed sessions. User-scoped registry should use an XDG-compatible directory, atomic writes, locking, bounded reads, and restrictive permissions. A PID or a registry file is not enough evidence to stop a process: reconcile PID, start time, launcher/process-manager identity and endpoint. Do not follow attacker-controlled symlinks or parse registry content as executable shell.

Remote session registry is authoritative for **managed** sessions only. Manually started Jupyter servers are discovered from verified Jupyter runtime metadata and must not be silently adopted.

## Failure contracts

- Missing remote Python/Jupyter runtime: report exact unavailable prerequisite; discovery should still probe other supported sources when possible.
- SSH timeout/host key mismatch: preserve remote state and provide an actionable error.
- Helper unavailable/incompatible: diagnostic and safe fallback only where explicitly supported.
- Malformed, oversized or partial JSON: fail closed and do not execute arbitrary output.
- Concurrent bootstrap/update: serialize or use an atomic, integrity-checked install strategy.
- Remote start interrupted: subsequent `list/status` reconciles any possibly launched managed server.
- Remote OS reboot: helper/state may remain, but kernels normally do not.

## M0 spikes and decision records

Prototype direct and ProxyJump commands with a basic manually started Jupyter Server, then with a separate Conda environment. Measure bootstrap complexity, supported runtime metadata and SSH/Jupyter version dependencies. Record the selected helper policy, protocol schema, privileges, upgrade approach and compatibility tests in [07 — Decisions](07-decisions.md).

Related: [architecture](02-architecture.md), [discovery/connectivity](11-discovery-and-connectivity.md), [security](04-security-and-reliability.md), [session lifecycle](09-session-lifecycle-and-auth.md).
