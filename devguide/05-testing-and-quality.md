# 05 — Testing and quality

## Test levels

**Unit:** CLI parsing, session identifiers, config validation, state transitions, serialization, output redaction, launcher argument construction and error messaging.

**Integration:** real OpenSSH to disposable Linux targets; launch/list/open/stop against Jupyter Server; detect WebSocket kernel connectivity; verify persistence after client SSH disconnection.

**End-to-end:** two clients against one remote host, multiple sessions on one host, simultaneous sessions on two hosts, and one host reachable only via `ProxyJump`.

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
| Authentication | Valid login; invalid token; redacted diagnostics |

Start with Linux clients and Linux remotes. Only advertise other platforms after CI or manual acceptance testing.

## CI and development standards

- Run lint/format checks, type checks for core interfaces, and isolated unit tests on pull requests.
- Run integration tests with disposable SSH/Jupyter environments; never against real lab infrastructure in public CI.
- Enforce tests around process cleanup, signals, concurrency, and authentication.
- Use dependency constraints and reproducible test fixtures.
- Check secret scanning and never put real machine names/IPs or credentials into committed fixtures.

## Definition of done for each milestone

A milestone is complete only when documented behavior is demonstrable, unit and integration tests pass, errors are actionable, security assertions are tested, and the public README describes only shipped functionality.

## Release checklist

Choose and document supported Python/Jupyter/OpenSSH versions, create changelog/release notes, build and install wheel in a clean environment, test the console script, run end-to-end smoke tests, and verify [MIT license](../LICENSE) packaging metadata. Publish to PyPI only when a usable release exists.
