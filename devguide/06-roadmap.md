# 06 — Development roadmap

**Status:** M0–M4 complete; M5 acceptance verified, operator fixture cleanup
pending; M6 onward planned. Dependency-ordered milestones,
**not** a release timeline. Each milestone has an independently demonstrable
vertical slice; security is a gate at every stage. Never advertise proposed CLI
syntax as implemented.

See [product scope](01-product-scope.md), [scenario matrix](08-scenarios-and-acceptance.md), [lifecycle/authentication contracts](09-session-lifecycle-and-auth.md), [remote runtime](10-remote-runtime-and-protocol.md), [discovery/connectivity](11-discovery-and-connectivity.md), [UX](12-user-experience.md), and [open decisions](07-decisions.md). Existing tests and public docs must track shipped behavior.

## M0 — Complete the design baseline

**Completed 2026-11-07:** [validation/ADR](13-m0-validation.md) and
[scenario ledger](14-acceptance-ledger.md). This closes the design baseline;
browser, logout, reboot and lifecycle feature gates remain in their own milestones.

**Outputs:** explicit CLI contracts, managed vs discovered server classification, security/authentication threat model, session/tunnel/kernel lifetimes, network reachability assumptions, supported Jupyter discovery strategy, remote workdir semantics, proposed process-manager evaluation, remote-helper bootstrap/compatibility approach, tunnel process lifetime, simple/advanced user flows and requirements-to-test mapping.

**Acceptance:** every essential scenario in [08](08-scenarios-and-acceptance.md) has a release gate, no hidden assumption that all machines connect both ways, and no unresolved security ambiguity blocks M1–M2 prototypes. Record architecture decisions and uncertainties transparently.

## M1 — SSH foundations and diagnostics

**Completed 2026-11-07:** [implementation, tests and limits](15-m1-foundations.md).
Only source installation and read-only `doctor` ship. No M2 session command is
implemented.

**Outputs:** initial package and command entrypoint; reuse OpenSSH host aliases and ProxyJump; safe remote command invocation; `doctor` checks for SSH, Jupyter Server, Python and relevant runtime dirs; actionable failures.

**Acceptance:** connect directly to a disposable Linux target and via a jump host. Respect host-key verification and selected remote OS account. No remote service/SSH config rewrite or elevated permission required.

## M2 — Discover and open an existing Jupyter server

**Completed 2026-11-08:** [implementation, acceptance and limits](16-m2-existing-servers.md).
Normal login is the authentication baseline; no credential handoff/cache or
managed lifecycle is implemented. Stop after M2 for review before M3.

**Outputs:** best-effort, current-user discovery using supported Jupyter runtime information (including multiple environment paths where known); candidate verification; `discover`/`list` and `open`; dynamic loopback-only SSH forwarding; browser/no-browser UX; explicit password/login fallback; labeling of unsupported runtime directories and base URL variants.

**Acceptance:** an already-running, manually started Jupyter Server on a host reachable through ProxyJump can be opened and used without manually selecting local ports. Multiple candidates are distinguishable. Failed discovery is reported as incomplete, not as proof of absence. Invalid auth is never bypassed; unmanaged `stop` is refused. One-server `open host` works with no mandatory JupyHop TOML file where prerequisites are discoverable. State clear limitations for IPv6, custom base paths, and HTTPS.

**Scope limit:** discovered servers are read-only for lifecycle actions. Discovering arbitrary user processes or all Conda environments is not promised. Initial kernel continuity after reconnection is tested separately in M4.

## M3 — Managed launch and readiness

**Completed 2026-11-08:** [launch contract, tests and limits](17-m3-managed-launch.md).
Private tmux is the initial launch backend; full logout/linger, reconciliation,
stop and cross-client live-kernel guarantees remain M4. Stop here for review.

**Outputs:** `start` launches a current-user Jupyter Server on remote loopback, selects safe remote port, verifies readiness/auth, registers stable session ID/owner/provenance, and connects through SSH. Specify remote helper installation/bootstrap and remote workdir/launcher contract.

**Acceptance:** execute a kernel through the forwarded server; launch failure produces accurate status and recoverable records; no public listener, shared privileged daemon, arbitrary shell injection, or disabled Jupyter auth. Two managed sessions can coexist without identity collision.

## M4 — Persistent lifecycle, reconciliation and reconnection

**Completed 2026-11-08:** [contract, experiments, acceptance and limits](18-m4-lifecycle.md).
Private tmux is the supported backend, subject to site logout/cgroup policy.
Independent clients and Chrome/tunnel closure preserve the same tested live
kernel; pidfd stop, lost replies, concurrent stops and boot-identity simulations
are verified. Physical reboot/PAM policy and automatic cleanup are not claimed.
Stop here for review before M5.

**Outputs:** choose and validate user-process supervision (`systemd --user` when feasible, tested fallback if necessary); remote per-user registry with atomic locks; `status`, `list`, `open`, `stop` managed sessions; local tunnel lifecycle; safe reauth from another client; collision/race/failure handling.

**Acceptance:** close browser and tunnel, then connect from an **independent authorized client** to the same live server and kernel without losing in-memory state; remote reboot is detected as lost state (not automatic kernel restoration). Concurrent starts, stale records, interrupted stop, and token redaction pass tests. Only verified managed processes can be stopped.

## M5 — Real-world scientific and multi-host workflows

**Acceptance verified 2026-11-08:** [profiles, two-target kernels, archive, real
Unix accounts, tests and limits](19-m5-scientific-workflows.md). Operator cleanup
of the explicitly provisioned account fixture is pending. Stop before M6.

**Outputs:** remote environment profiles (Conda/venv/system Python), validated `--workdir`, multi-host listing and selection, multiple simultaneous independent local forwards, clearer error and headless/JSON UX, testing across LAN/direct and external/ProxyJump routes, account isolation.

The demonstrated active-registry bound/name reuse need is addressed by explicit
nondeleting archive of inactive evidence, not automatic scientific-resource cleanup.

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
