# 08 — Scenario catalogue and acceptance matrix

**Status:** specification with [per-scenario evidence](14-acceptance-ledger.md).
M1/M2 implement diagnostics and verified read-only existing-server access.
M3 implements managed launch/readiness with the [evidence in 17](17-m3-managed-launch.md).
M4 implements [managed lifecycle and independent-client reconnection](18-m4-lifecycle.md).
Physical topology/site logout policy and additional compatibility scenarios remain
pending as recorded in the ledger; a feasibility spike alone is not acceptance.

## Topology and assumptions

Five illustrative machines: Researcher A's home client (`home-a`), Researcher A's lab workstation (`workstation-a`), Researcher B's home client (`home-b`), Researcher B's lab workstation (`workstation-b`), and an SSH gateway/cluster login node (`gateway`). Only the gateway is reachable from outside the lab via SSH; internal workstations are SSH-reachable via the gateway. A fixed public IP for the gateway is optional and is **not stored in this public guide**. These are fictional generic names, not application defaults.

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
| SCI-04 | workstation-a and workstation-b Jupyter sessions active simultaneously | Multiple forwards and session IDs coexist | M5 |
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

## Additional network, URL and browser scenarios

| ID | Case | Expected behavior | Gate |
| --- | --- | --- | --- |
| NET-09 | Remote Jupyter listening on IPv6 loopback `::1` | Forward supported address family correctly or explicitly reject unsupported transport | M2/M6 |
| NET-10 | Custom Jupyter `base_url` | Preserve paths, static assets, API and WebSocket routes | M2 |
| NET-11 | Remote Jupyter HTTPS / mismatched certificate hostname | Preserve TLS checks; report unsupported or require explicit reviewed mechanism, never silent insecure mode | M2/M6 |
| NET-12 | Laptop suspend and resume | Broken tunnel does not stop remote server; reconnection is explicit or a documented opt-in | M4/M5 |
| NET-13 | Repeated `open` / unrelated local listener | Reuse only verified owned forward or create separate one; never kill unrelated SSH process | M4 |
| NET-14 | Same remote machine via multiple SSH aliases | Do not conflate distinct remote identities or silently duplicate managed server state | M5 |
| NET-15 | Transfer large notebook data / sustained kernel WebSockets | Tunnel and jump host preserve data and kernel communication; failures surface clearly | M5/M6 |

## Additional discovery, authentication and recovery scenarios

| ID | Case | Expected behavior | Gate |
| --- | --- | --- | --- |
| DISC-09 | Custom `JUPYTER_RUNTIME_DIR` in another Conda environment | Use supported configured paths; report incomplete discovery if not visible | M2/M5 |
| DISC-10 | Server metadata missing but server running | Never claim complete absence; offer safe documented explicit endpoint option where supported | M2 |
| DISC-11 | Duplicate metadata for same server | Deduplicate without merging distinct live Jupyter instances | M2 |
| DISC-12 | Token rotation/password change | Require fresh authorized login or credential retrieval, never bypass auth | M2/M4 |
| LIFE-13 | Server restarts and reuses a previous port | Revalidate identity; do not imply old kernel is alive | M4 |
| LIFE-14 | CLI upgraded while remote managed sessions run | Existing work persists; incompatible protocol gives actionable error without data corruption | M4/M6 |
| LIFE-15 | Remote helper versions diverge across two clients | Version negotiation, no destructive automatic update, safe state interpretation | M4/M6 |
| LIFE-16 | `open` command process/terminal exits | Forward lifetime is well-defined; no accidental remote process termination | M4 |
| LIFE-17 | SSH start interrupted after process spawn | Discover/reconcile pending managed record; no duplicated untracked service | M4 |

## Usability and configuration scenarios

| ID | Case | Expected behavior | Gate |
| --- | --- | --- | --- |
| UX-01 | User has only working SSH alias and one discoverable Jupyter Server | `open host` works without mandatory JupyHop configuration | M2 |
| UX-02 | No servers; discovery was incomplete | Distinguish unknown from empty result and explain next action | M2 |
| UX-03 | Multiple server candidates | TTY selection, or non-interactive ambiguity error; never guess | M2 |
| UX-04 | `stop host` with multiple managed sessions | Require explicit identification/confirmation; never arbitrarily stop one | M4 |
| UX-05 | Headless computer with no browser | Provide useful no-browser flow without leaking credentials in diagnostics | M2 |
| UX-06 | Remote environment lacks JupyHop helper | Supported no-install discovery path or clear safe bootstrap instruction | M1/M2 |
| UX-07 | Local and remote helper incompatible versions | Actionable diagnostic and safe upgrade path | M4/M6 |
| UX-08 | Remote directory contains spaces, Unicode or tilde | Predictable validated remote path resolution, no argument injection | M5 |

## Acceptance workflow

For each row define a test fixture, command invocation, expected state changes, observable assertions and failure artifacts **without secrets**. Release gates in the table are minimum targets, not permission to skip earlier security controls. The first end-to-end success metric is **home-a -> workstation-a (existing manual Jupyter) with SSH jump and automatic browser access, followed by disconnect/reconnect**; kernel continuity is an M4 test, not guaranteed by the first M2 prototype.
