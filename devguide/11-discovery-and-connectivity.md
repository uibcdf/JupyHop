# 11 — Jupyter discovery and SSH connectivity

> **Design specification, not a claim of universal discovery.** JupyHop must report when discovery is incomplete.

M2 implements the supported subset documented in [16](16-m2-existing-servers.md):
private current-user metadata, Linux process/socket checks, IPv4 HTTP, simple
ASCII base paths and attached owned forwards. Coverage is always partial.
IPv6-only, HTTPS, legacy Notebook metadata and complex auth/proxies remain
unsupported; the broader requirements below retain their future release gates.

M3 extends discovery with private registry runtime paths and verified managed
UUIDs/names. A registry entry alone cannot establish managed provenance. Unknown
managed state versions are reported as unavailable; unmanaged search stays
partial. See [17](17-m3-managed-launch.md).

M5's [local preferences/inventory contract](19-m5-scientific-workflows.md) adds
per-alias helper/runtime directories and bounded multi-host listing. These paths
extend partial discovery; profiles do not enumerate all Conda environments.
Each route retains its own success/error record. Same-machine aliases remain
explicit routes to the same remote registry, without guessed LAN/bastion changes.
Real UID tests reject another account's runtime directory and process, even when
the requester knows its UUID, path and port. Archived records are not active
discovery sources. Existing unmanaged servers remain read-only for lifecycle.

## Sources of truth and scope

- **Connectivity:** OpenSSH aliases, configuration and trust store on the **current client**, including `Host`, `Include`, `Match`, `ProxyJump`, user identities and host-key validation. Do not build a second SSH parser or select LAN vs external route through guesswork.
- **Managed servers:** remote per-user JupyHop registry, reconciled against actual process and endpoint.
- **Existing unmanaged servers:** runtime metadata of Jupyter servers accessible to the authenticated remote OS account, augmented by explicitly configured runtime paths. Do not enumerate other users or assume every Conda environment shares one Jupyter runtime directory.
- **Authorization:** SSH reachability of a port does **not** prove the remote server belongs to the account. Validate metadata, address, process/ownership where feasible and require normal Jupyter authentication.

## Proposed discovery algorithm (M2)

1. Establish SSH session to selected alias using the *client's* actual OpenSSH config; preserve the target's resolved Unix identity.
2. Probe supported Jupyter Server/runtime information for that user, including runtime directory locations configured for the available Jupyter environments and user-supplied additional paths.
3. Parse structured metadata with schema/size limits; handle older Jupyter Notebook/Server variations explicitly rather than parsing unstable human-readable output.
4. Verify candidate address (IPv4 `127.0.0.1` or IPv6 `::1` when supported), port, base URL, scheme, liveness and provenance. Reject public/wildcard bindings for the automatic secure-open path unless a separately reviewed policy exists.
5. Deduplicate the same live server reported by multiple runtime dirs, while preserving distinct instances on the same host.
6. Classify as `managed`, `unmanaged`, `stale` or `unsupported`, and return nonsecret data and a **discovery coverage** diagnostic.
7. Present selection if several candidates are valid. Do not guess from port or process ID.
8. Establish a verified local loopback tunnel, then open a suitable URL/login flow without exposing secrets through general logs.

For missing runtime metadata or unrecognized custom base URL/TLS setups, report unsupported or partially discovered; optionally offer a **user-supplied** loopback endpoint subject to validation. This is *not* a license to scan arbitrary localhost ports or adopt unmanaged processes.

## Authentication and URL details

Jupyter Server may use token, password, cookie, custom authentication extension and custom `base_url`. Use the authenticated account's permitted mechanisms to obtain or use credentials, otherwise open the normal login page. Never disable auth. A token-bearing URL is sensitive and can leak into browser history, process command lines, debugging output or clipboard; the secure handoff method requires its own M0 prototype and documented policy. Preserve the actual base path and WebSocket behavior. HTTPS tunneled to `localhost` can have TLS hostname/certificate mismatch; detect and report it rather than automatically turning off TLS verification.

## Tunnels and address families

- Prefer binding local listener to `127.0.0.1` for the MVP; support remote `::1` only after explicit address-family testing. Never assume `localhost` resolves identically on client and server.
- Choose local port dynamically and verify the actual SSH listener with `ExitOnForwardFailure=yes`. Local port prechecks alone are race-prone; retry safely on collisions.
- Do not reuse a listener solely because the port is open. Verify its association with the intended host, remote port and target session. Distinguish tunnel identity from server identity.
- `open` must specify lifecycle: foreground/attached, background with owned handle, or explicit user-selected behavior. A browser launch must not accidentally terminate the tunnel.
- A second `open` may reuse an **owned, verified** healthy tunnel or create a new one; never terminate an unrelated SSH process.
- Tunnel interruption, client suspend/resume and network changes must be detected or reported; optional reconnect must not restart remote Jupyter.
- Browser/WebSocket functionality and large file transfers must be validated through the forward and jump chain.

## Site topology and routing

A lab workstation may be reached directly on LAN or via an external gateway. The *client's* configured SSH alias determines the route. For example, a home client can have `ProxyJump gateway`, while a lab client can use direct LAN SSH. One machine's route is not automatically transferable to another client.

The SSH gateway is a transport/bastion, **not a mandatory JupyHop controller**. Never schedule long-running scientific computation on a login node by default. Reaching machines in the opposite direction (such as home computers behind NAT without inbound access) requires an existing authorized network path and is outside MVP.

## Failure and compatibility cases

| Case | Expected outcome |
| --- | --- |
| SSH host key changes | Fail securely; do not auto-disable verification |
| Bastion unavailable | Target unreachable; no claim about remote session state |
| Multiple server matches | Explicit selection; preserve all distinct server IDs |
| Unreadable custom runtime dir | Partial-discovery warning and supported configuration path |
| Stale metadata or port reuse | Verify liveness/identity; do not forward blindly |
| IPv4 vs IPv6 difference | Use validated matching address family or explain unsupported |
| Custom `base_url` | Preserve URL path and WebSocket routes |
| Remote HTTPS with hostname mismatch | Explain certificate issue; never disable verification by default |
| Rotated token/password | New authorized login, no insecure cache bypass |
| Local port collision | Retry/select another verified local loopback port |
| Existing unrelated local SSH tunnel | Leave it untouched |
| Laptop suspend/resume | Restore only forward if authorized/configured; remote server remains independent |
| Duplicate SSH aliases pointing to same host | Explain identity scoping, avoid accidentally merging unlike accounts |
| Host reboot/remote port reassignment | Revalidate server identity, report lost kernels |
| Manually started server outside supported runtime locations | Incomplete discovery; no false 'none running' conclusion |

## Verification spikes

Test Jupyter Server versions actually available in supported Linux environments, including multiple Conda environments, configured `JUPYTER_RUNTIME_DIR`, generated tokens, passwords, custom base URLs, IPv6 and optional HTTPS. Record the exact supported matrix, limitations and fallback policy. Do not promise compatibility with JupyterHub-managed paths or exotic proxies before testing.

Related: [scenarios](08-scenarios-and-acceptance.md), [session/auth contracts](09-session-lifecycle-and-auth.md), [CLI](03-cli-and-configuration.md).
