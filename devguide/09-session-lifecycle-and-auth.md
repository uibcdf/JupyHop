# 09 — Session, tunnel, kernel and authentication contracts

**Status:** lifecycle contract with [M4 implementation/evidence](18-m4-lifecycle.md).
Unimplemented extensions and external policy boundaries remain explicit.

M3 implements the [initial launch/state/auth slice](17-m3-managed-launch.md).
M4 adds managed observations/readiness reconciliation and pinned graceful stop;
independent authorized software clients recover the same live kernel.

## Vocabulary

- **Client:** machine invoking JupyHop.
- **SSH connection:** authenticated transport to the remote account, possibly through ProxyJump.
- **Forward/tunnel:** *local*, ephemeral listener that maps one client loopback port to one *remote* loopback Jupyter listener.
- **Jupyter server:** remote HTTP/WebSocket service that manages files and kernels; can be *managed* by JupyHop or *discovered/unmanaged*.
- **Kernel:** separate runtime holding in-memory state; it is not equivalent to a browser tab, notebook file or SSH tunnel.
- **Session identity:** stable managed ID scoped to host and remote OS account; distinguish display name from authority.
- **Browser notebook session:** frontend/kernel association; requires tests against Jupyter APIs to preserve continuity.

## Independent lifetimes

| Resource | Owner | Lifetime | Survives client disconnect? | Survives host reboot? |
| --- | --- | --- | --- | --- |
| SSH control connection | Client/OpenSSH | Until exit/network drop | No | No |
| Local forward | Client/OpenSSH | Until closed | No | No |
| Jupyter Server | Remote OS account / external launcher | Until stopped/crash/reboot | **Yes if independently supervised** | Not automatically |
| Kernel process | Jupyter Server / kernel manager | Until termination/crash/reboot | Yes if server/kernel stays alive | **No in-memory guarantee** |
| Managed registry | Remote current-user file state | Until removed | Yes | Yes, but may be stale |

A *persistent* JupyHop session means independent of the client connection. It **does not** guarantee surviving remote reboot or preserving in-memory kernel state after process exit.

## Server modes

**Managed:** JupyHop created it and maintains lifecycle metadata. Only these are eligible for `stop` in MVP. Create a registry entry atomically with verified process identity, startup timestamp, port/listen address and provenance. Secrets are not put into ordinary registry fields.

**Discovered / unmanaged:** started manually or by another tool; may be listed/opened **only** if the current remote user is authorized and the endpoint can be verified. JupyHop must not stop, restart, or reconfigure it. Discovery coverage may vary by Jupyter version, Jupyter runtime directory and Conda environment.

**Unknown:** a port exists but cannot be verified as an authorized Jupyter endpoint. Do not attach by default.

## Discovery contract

1. SSH into target host as the desired OS account.
2. Locate only readable, supported Jupyter runtime metadata for that account (including configured extra runtime directories).
3. Validate server runtime metadata, address and port, protocol, liveness and ownership as far as permitted; never trust a stale file alone.
4. Classify each candidate: managed, discovered or stale/unsupported.
5. Return nonsecret structured records with source, limits and diagnostics. Never assume all sessions have been found.
6. For a selection, obtain permitted authentication details by a dedicated secure path, not by leaking them in generic `list`.

Multiple server versions, differing runtime dirs, custom base URLs, TLS, and password login require compatibility tests. Unsupported cases should yield an honest diagnostic.

## Local forwarding contract

- Use SSH alias intact; respect configured bastions, host verification and user identities.
- Forward **127.0.0.1:<chosen local port> -> 127.0.0.1:<verified remote port>** in target host's network namespace, with `ExitOnForwardFailure`.
- Handle bind races by checking the live SSH forward, retrying with another local port if needed.
- Preserve WebSocket upgrades and Jupyter's URL base path; never assume root path.
- Distinguish forward ownership from remote server ownership. Closing a tunnel **never** implies stopping remote Jupyter.
- A client may create multiple tunnels (one per session) or reuse an existing verified tunnel, but must not adopt arbitrary matching local listeners.

## Credential/authentication contract (security gate)

M0 selected the normal token-free Jupyter login page as the baseline; protected
automatic browser handoff remains an M2 experiment. See the
[recorded alternatives and risks](13-m0-validation.md). No new credential cache
is approved or implemented by M1.

For new managed servers M3 selects a prompted password sent through encrypted
stdin and stored only as a native Argon2 hash in private remote settings. This
permits normal login from another authorized client without restoring old local
state. Read the threat/tradeoff review in [17](17-m3-managed-launch.md).

A remote Jupyter instance may authenticate through a generated token, configured token, password, or an extension. Tunnel establishment proves SSH authentication but **does not** remove Jupyter authentication.

For managed sessions, select and document a supported strategy that allows an authorized second client to authenticate while keeping secrets out of public output and logs. Options to evaluate include remote-only, permission-restricted credential storage and Jupyter-supported runtime/service APIs. Tokens are secrets and must never become stable identifiers. If there is no safe way to retrieve or use credentials, JupyHop must request explicit login rather than disable authentication.

For discovered servers, obtain credentials only from sources the remote user is legitimately allowed to access; if credentials are unavailable, open the login page and ask the user to authenticate. Never scrape or exfiltrate tokens from another OS account, and never promise that every existing Jupyter server can be auto-opened.

Separate interactive browser opening (where one-time token URLs may be used with careful handling and browser history implications) from logs and JSON API outputs. Study Jupyter cookie/session behavior and base URL translation before finalizing secure URL handling.

## Lifecycle state machines

**Stored launch states (schema 1.0):** requested, starting, ready, failed, exited.
An optional boolean `stop_requested` preserves stop intent across client loss and
old runner updates. **Observations:** starting, ready, stopping, stopped,
unreachable, stale, failed. `stopped` requires intent plus observed process exit;
stale means boot change/missing/replaced process. Unreachable is uncertainty,
not proof of death. `status` promotes starting to ready only after verification.

**Tunnel states:** creating -> ready -> closed/failed. The tunnel may fail while the server remains running.

**Kernel states:** external to JupyHop; report only what the Jupyter Server can verify, never infer from tunnel or server status.

Idempotent stop requires verified ownership and process identity, not PID alone. Concurrent operations use remote locking/atomic registry operations. `start` interruption requires an explicit reconciliation path so the next invocation can find a potentially launched server.

## Process manager decision matrix

| Candidate | Advantages | Caveats |
| --- | --- | --- |
| `systemd --user` | Service supervision, restart policy, journal, process identity | May lack live user manager or permitted linger; linger may require admin |
| `tmux` | Common on remote scientific systems, survives SSH logout | Session naming, reliable lifecycle identification, no reboot survival |
| Controlled detached process | Few external requirements | Process groups, cleanup, log management and portability are harder |

**M4 choice:** private tmux is the supported backend, validated across complete
first-client disconnect and fresh client/kernel reconnection. systemd user-manager
availability on the local host does not provide a bus in the no-PAM SSH fixture.
No automatic restart, linger changes or privilege requirements. Site logind/cgroup
policy can still terminate workloads; no unconditional last-logout guarantee.

## Recovery guarantees

- Client disconnect: reconnect to same Jupyter server and **same running kernel if it survived**.
- Server crash: surface loss of server/kernel, do not claim memory was preserved.
- Remote reboot: registry may persist, but server and kernel are typically gone; offer explicit new start, not transparent state resurrection.
- Multiple clients: use distinct local forwards; avoid changing remote port/server when an existing one is healthy.
- Stop: stopping managed server may terminate kernels and running computations; require clear warning/confirmation policy.

## Additional validity boundaries

A remote loopback port is not evidence of ownership. Unmanaged discovery must have a defined completeness indicator, handle custom runtime directories and URL base paths, and preserve normal Jupyter authorization. Kernels must be verified to survive reconnect tests; a surviving HTTP endpoint is insufficient. See [11](11-discovery-and-connectivity.md).

There is no implicit promise that `open` keeps a tunnel alive after its terminal exits until a documented tunnel ownership/lifecycle policy is selected. See [12](12-user-experience.md). Any versioned helper or stored managed registry must support safe cross-client version negotiation; see [10](10-remote-runtime-and-protocol.md).

## Mandatory design spikes before M3/M4

1. Run a manually launched Jupyter Server in a Conda environment; inspect supported runtime metadata and token/password behavior.
2. Connect from client A then client B to the same running kernel (include WebSockets).
3. Compare systemd user-manager logout/linger behavior with tmux on a disposable Linux host.
4. Simulate local port collisions, stale runtime files, SSH loss during start, server crash and host reboot.
5. Record protocol and serialization details, permissions and security tests as an ADR in [07](07-decisions.md).
