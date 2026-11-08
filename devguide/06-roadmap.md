# 06 — Development roadmap

This is a **dependency-ordered roadmap**, not a promised schedule. Each milestone should produce a small, testable outcome. Do not implement later features until earlier security and lifecycle contracts are credible.

## M0 — Design baseline

**Deliverables:** repository documentation, MIT license, agreed MVP scope, proposed CLI interface, security decisions, process-manager evaluation, session registry schema and a minimal test plan.

**Acceptance:** all MVP commands have unambiguous behavioral contracts, and no unresolved security decision prevents first prototype.

## M1 — SSH and remote prerequisites

**Deliverables:** Python package skeleton and `jupyhop` CLI; host-alias transport; diagnostic command; remote environment detection; structured error handling.

**Acceptance:** directly and via ProxyJump, tool validates SSH and reports whether an appropriate remote Python/Jupyter launcher is present without changing the host.

## M2 — Launch and connect: vertical slice

**Deliverables:** start a managed server under the SSH user's account, bind to remote loopback, wait until ready, establish loopback local forward, open browser or print a safe access instruction.

**Acceptance:** execute a notebook kernel through the forwarded session; no fixed forward ports, public listener, or disabled Jupyter auth. Handle launcher/readiness failures without orphaned privileged resources.

## M3 — Persistent lifecycle and discovery

**Deliverables:** chosen remote process manager; versioned per-user registry; session names/IDs; `list`, `status`, `open`, `stop`; stale state reconciliation.

**Acceptance:** close first client; open from a second authorized client; reconnect to the same running kernel; stop only that managed session. Two concurrent sessions remain independently controllable.

## M4 — Research usability

**Deliverables:** explicit environment launcher profiles, multi-host listing, clear selection UX, headless mode, machine-readable output and robust troubleshooting.

**Acceptance:** two separate remote hosts and multiple launcher profiles function without host-specific code; ambiguous selections and missing environments yield helpful errors.

## M5 — Public beta and documentation

**Deliverables:** quickstart, configuration examples, architecture/security documentation, contribution guide, regression suite, packaging metadata and published release after validation.

**Acceptance:** a new user with working SSH access can complete start/reconnect/stop using documentation alone. Release artifacts contain correct MIT metadata and no private configuration.

## M6 — Optional extensions (separate decisions)

- Slurm launcher and job lifecycle, respecting compute-node allocation.
- Detection of explicitly authorized unmanaged Jupyter servers.
- Optional web UI or machine discovery.
- Shared/team session policy only after independent authorization review.
- macOS/Windows client support after platform testing.

Do not treat M6 as a requirement for a usable first release.

## Milestone dependency chain

`M0 -> M1 -> M2 -> M3 -> M4 -> M5`

Parallelizable work: documentation, CI baseline, packaging, and security tests. Keep the functional vertical slice first.

## Prioritization rule

Prefer eliminating manual port and reconnection work before adding UI, backends, or centralized features. If a proposed feature requires a permanent coordinator, first determine whether it belongs in JupyterHub rather than JupyHop.
