# 06 — Development roadmap

**Status:** planning. Dependency-ordered milestones, **not** a release timeline. Each milestone has an independently demonstrable vertical slice; security is a gate at every stage. Never advertise proposed CLI syntax as implemented.

See [product scope](01-product-scope.md), [scenario matrix](08-scenarios-and-acceptance.md), [lifecycle/authentication contracts](09-session-lifecycle-and-auth.md), and [open decisions](07-decisions.md). Existing tests and public docs must track shipped behavior.

## M0 — Complete the design baseline

**Outputs:** explicit CLI contracts, managed vs discovered server classification, security/authentication threat model, session/tunnel/kernel lifetimes, network reachability assumptions, supported Jupyter discovery strategy, remote workdir semantics, proposed process-manager evaluation and requirements-to-test mapping.

**Acceptance:** every essential scenario in [08](08-scenarios-and-acceptance.md) has a release gate, no hidden assumption that all machines connect both ways, and no unresolved security ambiguity blocks M1–M2 prototypes. Record architecture decisions and uncertainties transparently.

## M1 — SSH foundations and diagnostics

**Outputs:** initial package and command entrypoint; reuse OpenSSH host aliases and ProxyJump; safe remote command invocation; `doctor` checks for SSH, Jupyter Server, Python and relevant runtime dirs; actionable failures.

**Acceptance:** connect directly to a disposable Linux target and via a jump host. Respect host-key verification and selected remote OS account. No remote service/SSH config rewrite or elevated permission required.

## M2 — Discover and open an existing Jupyter server

**Outputs:** best-effort, current-user discovery using supported Jupyter runtime information; candidate verification; `discover`/`list` and `open`; dynamic loopback-only SSH forwarding; browser/no-browser UX; explicit password/login fallback; labeling of unsupported runtime directories and base URL variants.

**Acceptance:** an already-running, manually started Jupyter Server on a host reachable through ProxyJump can be opened and used without manually selecting local ports. Multiple candidates are distinguishable. Failed discovery is reported as incomplete, not as proof of absence. Invalid auth is never bypassed; unmanaged `stop` is refused.

**Scope limit:** discovered servers are read-only for lifecycle actions. Discovering arbitrary user processes or all Conda environments is not promised. Initial kernel continuity after reconnection is tested separately in M4.

## M3 — Managed launch and readiness

**Outputs:** `start` launches a current-user Jupyter Server on remote loopback, selects safe remote port, verifies readiness/auth, registers stable session ID/owner/provenance, and connects through SSH. Specify remote helper installation/bootstrap and remote workdir/launcher contract.

**Acceptance:** execute a kernel through the forwarded server; launch failure produces accurate status and recoverable records; no public listener, shared privileged daemon, arbitrary shell injection, or disabled Jupyter auth. Two managed sessions can coexist without identity collision.

## M4 — Persistent lifecycle, reconciliation and reconnection

**Outputs:** choose and validate user-process supervision (`systemd --user` when feasible, tested fallback if necessary); remote per-user registry with atomic locks; `status`, `list`, `open`, `stop` managed sessions; local tunnel lifecycle; safe reauth from another client; collision/race/failure handling.

**Acceptance:** close browser and tunnel, then connect from an **independent authorized client** to the same live server and kernel without losing in-memory state; remote reboot is detected as lost state (not automatic kernel restoration). Concurrent starts, stale records, interrupted stop, and token redaction pass tests. Only verified managed processes can be stopped.

## M5 — Real-world scientific and multi-host workflows

**Outputs:** remote environment profiles (Conda/venv/system Python), validated `--workdir`, multi-host listing and selection, multiple simultaneous independent local forwards, clearer error and headless/JSON UX, testing across LAN/direct and external/ProxyJump routes, account isolation.

**Acceptance:** both lab workstations operate simultaneously from a home client; two separate remote Unix users cannot see/stop each other's managed sessions; a researcher can start in a selected project directory/environment, disconnect and reconnect without manually finding a port. If a route does not exist, explain rather than silently create an unsafe path.

## M6 — Public beta, compatibility and release

**Outputs:** test matrix, security review, docs with actual commands, quickstart, troubleshooting, contribution instructions, package metadata and MIT license, clean install/build, CI for supported platforms, versioned state/protocol compatibility strategy, release notes.

**Acceptance:** a new user with legitimate OpenSSH access can complete discovered-open and managed-start/reconnect/stop guided by docs. Automated and documented manual acceptance cases cover mandatory scenario IDs; no real lab IP/credentials in fixtures or release artifacts. PyPI release only after clean install and end-to-end tests.

## M7 — Optional extensions (separate scope decisions)

- **Slurm launcher:** submit/cancel within scheduler allocations and route to compute nodes; never run compute workloads by default on the login/bastion node.
- **Enhanced discovery:** support explicit additional runtime paths or selected older server variants and safe, opt-in adoption policy.
- **Web interface or coordinator:** justify against central JupyterHub rather than replicate identity/routing functions.
- **Cross-user collaboration:** requires explicit sharing and authorization design.
- **Additional client platforms:** macOS and Windows only when tested and documented.

## Dependency and risk strategy

`M0 → M1 → M2 → M3 → M4 → M5 → M6`. M7 is optional.

Some M2 discovery probes and M4 supervision/authentication spikes should be performed early in M0 to avoid discovering a fundamental blocker after implementing the CLI. Documentation, lint, package skeleton, and unit tests may proceed in parallel, but must not claim maturity ahead of implementation.

## Prioritization rule

Solve **open an existing Jupyter from another computer** first; then automate **managed launch**, then prove **persistent recovery of the same live kernel**. Do not add a central portal, remote host auto-discovery, scheduler integration or a generalized web service before those workflows are stable.
