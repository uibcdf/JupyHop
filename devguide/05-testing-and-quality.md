# 05 — Testing and quality

## Test levels

**Unit:** CLI parsing, session identifiers, config validation, state transitions, serialization, output redaction, launcher argument construction and error messaging.

**Integration:** real OpenSSH to disposable Linux targets; launch/list/open/stop against Jupyter Server; detect WebSocket kernel connectivity; verify persistence after client SSH disconnection; discover manually started Jupyter Server through supported current-user runtime metadata.

**End-to-end:** two clients against one remote host, a manually started current-user Jupyter in a different Conda environment, multiple sessions on one host, simultaneous sessions on two hosts, and one host reachable only via `ProxyJump`.

**Security:** tests for token redaction, localhost-only binding, unsafe names, SSH option injection, per-user state isolation, stale PID handling, malicious/symlinked state files and lifecycle permission checks.

## Minimum matrix

| Dimension | Cases |
| --- | --- |
| Connection | Direct SSH; ProxyJump |
| Session count | Zero; one; multiple |
| Remote reachability | Online; disconnected; rebooted |
| Client network | Single client; two reconnecting clients |
| State | Healthy; starting; stale; invalid |
| Environment | System Python; venv/Conda executable path |
| Forwarding | Free port; collision; interrupted tunnel |
| Authentication | Valid login; invalid token; password login; unavailable token; redacted diagnostics |
| Origin | Managed server; manually launched discoverable server; unsupported runtime directory |
| Lifetime | Browser disconnect; tunnel disconnect; server crash; kernel state continuity; host reboot |
| Users | Two distinct Unix users; no cross-account list/stop |
| Work directory | Remote project dir; spaces; Unicode; missing dir |
| Routing | Lab LAN vs external SSH ProxyJump selected by client SSH config |
| Network/addressing | IPv4 loopback; optional IPv6 loopback; unavailable jump host; suspend/resume |
| URL behavior | Custom base URL; HTTP/WebSocket paths; HTTPS and certificate mismatch |
| Credential rotation | Changed token/password; unavailable credentials; safe login fallback |
| Local tunnel lifecycle | Repeat open; unrelated local listener; Ctrl-C; terminal close; stale forwards |
| Versioning | Client/helper major mismatch; older state schema; concurrent bootstrap/update |
| Transfer | Large-file traffic and sustained WebSocket connection through jump host |

Start with Linux clients and Linux remotes. Only advertise other platforms after CI or manual acceptance testing.

## CI and development standards

- Run lint/format checks, type checks for core interfaces, and isolated unit tests on pull requests.
- Run integration tests with disposable SSH/Jupyter environments; never against real lab infrastructure in public CI.
- Enforce tests around process cleanup, signals, concurrency, and authentication.
- Use dependency constraints and reproducible test fixtures.
- Check secret scanning and never put real machine names/IPs or credentials into committed fixtures.

## Scenario traceability

All behavior must be traceable to [08 — Scenario catalogue](08-scenarios-and-acceptance.md) and [09 — Session contracts](09-session-lifecycle-and-auth.md). Record which IDs are automated and which require manual testing, supported platforms and observed results. **M2 must prove discovery/opening of an already-running authorized Jupyter server through a jump host; M4 must separately prove same live kernel across disconnect/reconnect.** Never infer kernel persistence from a merely available HTTP endpoint.

## Required evidence before the MVP is considered complete

Create a traceability ledger mapping every mandatory scenario ID in [08](08-scenarios-and-acceptance.md) to a test name, expected result, observed status, supported version and security assertion. Maintain a known-limitations list for unsupported or partially discoverable Jupyter configurations. Add a usability smoke test starting with only a working SSH alias and a manually launched Jupyter Server. See [10](10-remote-runtime-and-protocol.md), [11](11-discovery-and-connectivity.md), and [12](12-user-experience.md).

## Definition of done for each milestone

A milestone is complete only when documented behavior is demonstrable, unit and integration tests pass, errors are actionable, security assertions are tested, and the public README describes only shipped functionality.

## Release checklist

Choose and document supported Python/Jupyter/OpenSSH versions, create changelog/release notes, build and install wheel in a clean environment, test the console script, run end-to-end smoke tests, and verify [MIT license](../LICENSE) packaging metadata. Publish to PyPI only when a usable release exists.
