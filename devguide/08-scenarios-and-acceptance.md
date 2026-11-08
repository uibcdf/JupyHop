# 08 — Scenario catalogue and acceptance matrix

**Status:** specification; no scenario is claimed implemented. This is the acceptance contract for the real-world use cases motivating JupyHop. Each scenario must be mapped to a test ID before the corresponding milestone is considered complete.

## Topology and assumptions

Five illustrative machines: Diego's home client (Aleph), Diego's lab workstation (Nauta), Liliana's home client, Liliana's lab workstation (Spika), and the lab SSH gateway/cluster login node (Ixtlilton). Only the gateway is reachable from outside the lab via SSH; internal workstations are SSH-reachable via the gateway. The gateway has a fixed public IP. These are **illustrative site-specific facts, not application defaults**; tests use fictional names and addresses.

The tool must not assume that all hosts are connected to each other. **Reachability is directional**: a client can control a remote host only when OpenSSH can establish an authorized connection from that client. Remote access *to a home machine* is not guaranteed and requires an existing permitted route (VPN, reverse tunnel, additional jump host, etc.) outside MVP.

## Connectivity cases

| ID | Origin -> target | Required outcome | Release gate |
| --- | --- | --- | --- |
| NET-01 | Home client -> own lab workstation via jump host | Discover/connect without hand-written forwarding | M2 |
| NET-02 | Home client -> other lab workstation, **authorized SSH account** | Respect the SSH identity and OS permissions | M2 |
| NET-03 | Lab workstation -> another lab workstation via LAN | Direct route **if SSH config resolves one**; do not force a jump | M2 |
| NET-04 | Home client -> gateway itself | Connect directly to user-owned Jupyter, if permitted | M2 |
| NET-05 | Both home clients -> their separate lab machines | Independent sessions and forwards | M5 |
| NET-06 | Client -> host unreachable / jump unavailable | Explain failure; do not stop remote servers or claim they have stopped | M2 |
| NET-07 | Client moves between external and internal networks | Honor current OpenSSH config; no hidden dependency on a previous tunnel | M5 |
| NET-08 | Client -> home machine without inbound route | Explain unsupported connectivity, no implied magic relay | M0 |

**Important:** OpenSSH host alias and its route are the source of truth. Different client devices may have different SSH configs. A stale or misconfigured ProxyJump cannot be repaired by JupyHop automatically.

## Server discovery and opening

| ID | Case | Expected behavior | Gate |
| --- | --- | --- | --- |
| DISC-01 | One manually launched current-user Jupyter Server | Discover and open if runtime metadata and authentication are accessible | M2 |
| DISC-02 | Several Jupyter servers / ports on one host | List distinct candidates; require explicit choice, no guessing | M2 |
| DISC-03 | Session running in another Conda/venv | Probe supported runtime directories and report coverage; allow explicit configured paths | M2/M5 |
| DISC-04 | Runtime directory absent, customized or inaccessible | Report incomplete discovery, optionally accept explicit URL/port **only after validation** | M2 |
| DISC-05 | Stale Jupyter runtime file or dead process | Validate actual liveness and ownership, flag stale instead of connecting blindly | M2 |
| DISC-06 | Unmanaged Jupyter server found | Connect only; **stop is forbidden unless explicitly adopted through a separately designed authorization process** | M2 |
| DISC-07 | Jupyter password/custom auth | Preserve authentication and provide a supported, non-leaking login flow | M2 |
| DISC-08 | JupyterHub-managed server or nonstandard proxy path | Not universally supported; detect limitations and document rather than assume compatibility | M2 |

Discovery is **best-effort** and limited to the authenticated remote user's accessible runtime information. Neither arbitrary-process scanning nor cross-user enumeration is part of MVP. Test Jupyter Server's supported runtime APIs and file formats rather than parsing human-readable CLI text alone; verify that observed listen address is loopback and endpoint is live before forwarding.

## Lifecycle, concurrency and execution

| ID | Case | Expected behavior | Gate |
| --- | --- | --- | --- |
| LIFE-01 | Launch managed server | Correct host, OS identity, launcher, directory, loopback binding, authentication | M3 |
| LIFE-02 | Close browser or local SSH tunnel | Remote server and existing kernel continue if machine remains alive | M4 |
| LIFE-03 | Reconnect from a different authorized client | Same server and, when alive, same kernel state | M4 |
| LIFE-04 | Two local tunnels to same remote server | Independent loopback ports, no session restart | M4 |
| LIFE-05 | Explicit stop of a managed session | Stop only verified owned process; warn about possible kernel termination | M4 |
| LIFE-06 | Remote host reboot | Detect stale sessions; do not claim kernel memory survived | M4 |
| LIFE-07 | SSH drops during start/stop | Reconcile remote state, avoid orphaned resources and accidental duplicates | M4 |
| LIFE-08 | Two concurrent starts with same name | Deterministic conflict/lock, registry not corrupted | M4 |
| LIFE-09 | Two distinct Jupyter instances use same requested port | Detect collision, pick safe free port or fail, never misroute | M3/M4 |
| LIFE-10 | Two users on one remote Unix host | Separate state, credentials, and OS-account permissions | M5 |
| LIFE-11 | Multiple kernel sessions on one Jupyter server | Browser reconnect does not silently create/restart a kernel | M4 |
| LIFE-12 | Jupyter crashes while tunnel stays connected | Report loss and offer explicit recovery, not silent kernel resurrection | M4 |

## Research workflow cases

| ID | Case | Expected behavior | Gate |
| --- | --- | --- | --- |
| SCI-01 | Choose a Conda/venv executable | Launch a matching remote Jupyter environment without sourcing untrusted shell profiles | M5 |
| SCI-02 | Launch from a project work directory | Remote path validated; spaces, Unicode, ~, symlinks handled predictably | M5 |
| SCI-03 | Run computation for hours | Browser disconnect does not kill computation; restart of OS is not checkpoint recovery | M4 |
| SCI-04 | Nauta and Spika Jupyter sessions active simultaneously | Multiple forwards and session IDs coexist | M5 |
| SCI-05 | Notebook on Slurm compute node | Deferred to optional backend, not assumed available in MVP | M7 |

## Cross-cutting error and security cases

| ID | Case | Expected behavior |
| --- | --- | --- |
| SEC-01 | SSH host key mismatch | Fail; never automatically disable host-key verification |
| SEC-02 | Token not recoverable / password required | Explain and use explicit authentication; never turn auth off |
| SEC-03 | Token-bearing URL in output | Redact logs, JSON, diagnostics; user-visible opening uses protected handling |
| SEC-04 | User tries to stop another user's process | Deny |
| SEC-05 | Port occupied on local client | Allocate another port and verify tunnel readiness |
| SEC-06 | Browser unavailable / headless client | Provide a safe, explicit no-browser pathway |
| SEC-07 | Remote registry stale or hostile | Validate metadata and ownership before using or deleting it |
| SEC-08 | SSH command/path injection attempts | Treat inputs as data, reject unsafe values |

## Acceptance workflow

For each row define a test fixture, command invocation, expected state changes, observable assertions and failure artifacts **without secrets**. Release gates in the table are minimum targets, not permission to skip earlier security controls. The first end-to-end success metric is **Aleph -> Nauta (existing manual Jupyter) with SSH jump and automatic browser access, followed by disconnect/reconnect**; kernel continuity is an M4 test, not guaranteed by the first M2 prototype.
