# 07 — Design decisions and open questions

Keep explicit decisions separate from hypotheses. Add dates, rationale and rejected alternatives as implementations become concrete.

## Accepted design directions

| ID | Decision | Rationale |
| --- | --- | --- |
| D01 | Project/package/CLI name: JupyHop / `jupyhop` | General-purpose identity |
| D02 | License: MIT | Matches UIBCDF's MolSysMT and MolSysViewer licensing approach |
| D03 | SSH-native, using existing OpenSSH configuration | Reuse proven authentication, ProxyJump and host verification |
| D04 | No mandatory centralized daemon for MVP | Lightweight individual and small-lab use |
| D05 | Each server runs as the authenticating remote OS user | Respect permissions and avoid impersonation |
| D06 | Remote Jupyter binds to loopback and retains authentication | Minimize exposure |
| D07 | Best-effort discovery/opening of authorized current-user unmanaged Jupyter is in MVP; only JupyHop-managed sessions can be stopped | Meets original workflow while preserving ownership boundary |
| D08 | Do not embed site-specific IPs, hostnames or accounts | General reuse and privacy |
| D09 | JupyterHub remains a distinct solution, not a dependency or implementation target | Avoid duplicating multiuser platform features |
| D10 | Separate local tunnel, remote Jupyter Server and kernel lifetimes | Prevent accidental termination or false persistence guarantees |
| D11 | Trust OpenSSH host config for LAN/ProxyJump routing; connectivity is directional | Avoid lab-specific network heuristics |
| D12 | MIT license with the same UIBCDF attribution pattern as MolSysMT/MolSysViewer | Consistent open-source policy |

## Design policy clarifications

- **D07 scope:** best-effort current-user unmanaged discovery/open is part of M2. Exhaustive discovery, unmanaged adoption and lifecycle control are deferred.
- **D06 secrets:** never store unprotected plaintext secrets or emit them in logs; restricted remote-account storage of required credentials remains a separately reviewed option (not approved by default).
- **CLI ambiguity:** `open host` may choose exactly one validated candidate; multiple candidates require explicit selection. `stop` is limited to managed sessions and must never guess when ambiguous.
- **Portability:** the same alias may have different OpenSSH routing on different clients; an alias alone is not a global host identity.

## M0 decisions (2026-11-07)

The dated ADR [M0 validation](13-m0-validation.md) records context, experiments,
alternatives, consequences and security impact. It supersedes pending questions
only within the stated scope:

| ID | Decision | Evidence / boundary |
| --- | --- | --- |
| D13 | No-install stdin Python probe for M1/M2 | Direct/jump experiments; no remote cache or package update |
| D14 | Read-only bounded runtime parsing for M2 | Jupyter list API deletes stale records |
| D15 | Normal token-free login page is the auth baseline | Token/password POST succeeds; browser automation still pending |
| D16 | Attached, fresh owned forward for initial M2 | Independent transports preserve tested kernel state |
| D17 | Capability-dependent supervision; no universal backend selected | tmux works in fixture; systemd context/logout needs further tests |
| D18 | Version 1.0 bounded JSON probe; registry version separate | M1 must test malformed output and major mismatch |
| D19 | Python 3.11–3.14, Linux first; stdlib-only client runtime | 67 tests pass on every supported minor version; CI matrix includes all four |
| D20 | M1 doctor uses batch SSH, strict target trust and no shared master | Bounded process-group cleanup; no hidden prompts; test unknown/changed host keys |

M0 design acceptance is met; later feature acceptance remains pending. See the
[scenario ledger](14-acceptance-ledger.md).

## M2 decisions (2026-11-08)

The [M2 report](16-m2-existing-servers.md) supplies context, alternatives,
security impact and live-test evidence for these decisions:

| ID | Decision | Rationale / consequence |
| --- | --- | --- |
| D21 | Read-only bounded metadata + current UID/PID start/socket-inode verification; partial coverage always | Neither a PID file nor an open port grants ownership; IDs are observations, never lifecycle authority |
| D22 | Token-free normal Jupyter login; IPv4 HTTP and simple ASCII base paths initially | Real browser/form/cookie/WS tests pass; no credential cache, token argv or TLS bypass |
| D23 | One foreground-owned OpenSSH master with a private control socket | Clear configured forwards, add only our forward through mux, verify owned PID, prohibit client fallback and revalidate on the exact connection |

D23 refines D16 without introducing detached/shared tunnel reuse. The no-install
stdin policy D13 is now demonstrated with a stdlib-only helper interpreter and
a Jupyter server in another environment. Lifecycle helper/process manager/state
questions remain M3/M4 decisions, not resolved by M2 discoverability.

## M3 decisions (2026-11-08)

The [M3 report](17-m3-managed-launch.md) records evidence, alternatives, security
review and limits for the launch baseline:

| ID | Decision | Rationale / consequence |
| --- | --- | --- |
| D24 | Dedicated private tmux socket/session for initial launch | Reuses tested user-level process separation; no global tmux/systemd/linger changes; final persistence backend remains M4 |
| D25 | New session password via encrypted stdin, native Argon2 hash in private remote settings | Normal Jupyter login from another client without token argv/URLs or plaintext persistence |
| D26 | Versioned per-host/account registry, UUIDs, atomic writes and flock | Shared HOME isolation, unique names, process/socket/runner provenance and recoverable launch records |
| D27 | Immutable per-session source bootstrap; wire 1.2 separate from registry 1.0 | No remote package install, no implicit migration or replacement of running launchers |
| D28 | Native Jupyter ephemeral port + verified readiness; uncertain starts retain evidence | No guessed port or automatic restart/cleanup; reconciliation remains M4 |

## M4 decisions (2026-11-08)

See [18](18-m4-lifecycle.md) for experiments, alternatives and boundaries.

| ID | Decision | Rationale / consequence |
| --- | --- | --- |
| D29 | Pin Linux pidfd before stop identity checks, graceful SIGTERM only | Avoid PID reuse races; never tmux kill/PID-only fallback/SIGKILL escalation |
| D30 | Prefer Python pidfd API, feature-detect named libc wrappers if absent | Tested Conda builds omit the API; stdlib ctypes needs no package dependency; unavailable capability refuses stop |
| D31 | Wire 1.3, unchanged schema 1.0 with optional boolean stop intent | M3 runners preserve additive intent; no stored-state migration or launcher replacement |
| D32 | Keep private tmux as the supported backend; OS logout policy is external | Independent-client/kernel continuity verified; no user bus in no-PAM SSH fixture; no auto linger/restart/backend switch |
| D33 | Exact UUID confirmation, retain forensic state/settings after stop | Concurrent/lost-reply retry is safe; cleanup/name reuse must preserve possible orphaned-kernel recovery evidence |

## Decisions remaining for their implementation milestones

| Topic | Options / questions | Evidence needed |
| --- | --- | --- |
| Lifecycle rollout extensions | Optional installed helper/migration | M4 source RPC and unchanged M3 runners are verified; no installation is needed |
| Other process managers / site validation | Explicit systemd backend and PAM/linger fixture | M4 tmux is tested; physical site logout policy cannot be inferred from it |
| Registry retirement / migration | Explicit terminal cleanup and name reuse without losing orphaned-kernel evidence | M4 retains bounded records and private settings; no automatic deletion |
| Automatic browser authentication (M2) | Protected token handoff beyond selected normal-login baseline | Real browser cookie/history exposure tests |
| Manually started server discovery | Runtime dir enumeration, supported versions, probe ownership/liveness, custom base URL | Prototype in multiple Conda environments |
| Future port customization | M3 fixes native ephemeral allocation; explicit port policy is separate scope | No manual remote-port coordinator is needed for M3 |
| Local tunnel lifetime | Foreground CLI, detached SSH, or reuse/control socket | Reliable cleanup and reconnection |
| Environment launcher | Explicit Python path, profile command, kernel selection | Safe quoting, reproducibility, cross-env UX |
| Minimum versions | Python, Jupyter Server, OpenSSH, Linux distros | Dependency testing and CI |
| Broader identity reconciliation | Cross-user/multi-host policy and name reuse | M4 continuity/stop are verified; M5/M6 extend acceptance |
| Workdir / launch profiles | Explicit remote working directory, environment Python path and safe quoting | Conda/venv and Unicode-path tests |
| Multi-client forward | Foreground/background tunnel tracking and cleanup | Port collisions, process ownership, WebSocket tests |
| Reboot behavior | Mark stale vs optional user-requested restart | Predictability and policy |
| Runtime/helper rollout | No-install discovery vs minimal helper vs on-demand helper | Security, remote Python requirements, updates, installation UX |
| Lifecycle compatibility/migrations | M3 wire 1.2/schema 1.0 are fixed; incompatible writes fail | State migrations and installed lifecycle upgrades remain M4/M6 |
| URL variants | IPv6/HTTP/HTTPS, base paths and TLS hostname mismatch | Live Jupyter and browser/WebSocket tests |
| Discovery coverage | Multiple Jupyter runtime dirs, deduplication and explicit paths | Multi-Conda environment prototypes |
| Browser/tunnel contract | Attached vs supervised background forward, repeat open, close behavior | UX and recovery tests |

## Architectural decision record format

For substantive changes, record: **Context**, **Decision**, **Consequences**, **Alternatives considered**, **Security impact**, **Test evidence**, and **Date**.

## Deferred scope

Slurm integration, **exhaustive** unmanaged discovery/adoption or control, browser portal, cross-user session sharing and centrally administered profiles. Each requires its own decision and acceptance tests.
