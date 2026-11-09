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

## M5 decisions (2026-11-08)

Context, experiments and limits: [19](19-m5-scientific-workflows.md).

| ID | Decision | Rationale / consequence |
| --- | --- | --- |
| D34 | Optional bounded TOML v1 with named Python/workdir profiles and per-alias helper/runtime preferences | Stdlib-only parsing, explicit CLI precedence, no shell activation/credentials/SSH duplication; owned nonwritable config and isolated test defaults |
| D35 | Sequential inventory of up to 16 explicit/configured aliases, per-route errors, list JSON v1 | Simple bounded requests, no SSH parser/topology inference/cache; original single-host discover remains stable; ambiguous open needs explicit choice |
| D36 | Archive inactive directories atomically, retain forensic settings/runtime files, release active name/budget | Resolves 128-entry operational bound without deleting orphaned-kernel recovery data or scientific files; refuse live/uncertain identities; RPC 1.4, schema unchanged |
| D37 | Operator-provisioned temporary real accounts and a separate loopback sshd for isolation acceptance | Actual UID/auth boundaries are verified; privileged fixture is separate from the non-root product; namespace restriction/VM attempt did not establish acceptance |

## M6 decisions (2026-11-08)

Experiments, internal review and release limits: [20](20-m6-beta-readiness.md).

| ID | Decision | Rationale / consequence |
| --- | --- | --- |
| D38 | Managed start requires Server >=2.20,<3; existing-open remains a separate capability | Native 2.17 advertises zero for a nonzero bound port; 2.20 fixes this upstream. Refuse before registry creation instead of introducing an allocator; recommend tested 2.21.1. |
| D39 | Command-wide SIGTERM/SIGHUP unwind; refuse getpass echo fallback; bounded retry of atomically replaced reads | Close owned transport during any phase, preserve unknown remote-write outcome and private input; reopen retired inodes without relaxing file/UID/mode/link checks. |
| D40 | Prepare reviewed candidate artifacts and explicit compatibility/security/release policy; publication stays separate | Stdlib artifact/version/license/entrypoint/source checks supplement clean-wheel/browser tests; no mandatory dependencies or automated upload to package registries. |
| D41 | Package versions and release tags use only x.y.z; current candidate 0.1.0 | Explicit maintainer preference: no prefixes or suffixes. Pre-1.0 uses 0.y.z; the artifact inspector enforces the format. Wire/state contracts stay independent and building creates no tag. |

## Decisions remaining for their implementation milestones

| Topic | Options / questions | Evidence needed |
| --- | --- | --- |
| Lifecycle rollout extensions | Optional installed helper/migration | M4 source RPC and unchanged M3 runners are verified; no installation is needed |
| Other process managers / site validation | Explicit systemd backend and PAM/linger fixture | M4 tmux is tested; physical site logout policy cannot be inferred from it |
| Archive deletion / migration | Explicit retention/deletion policy and orphaned-kernel recovery | M5 archive/name reuse is verified; permanent deletion and migration remain unimplemented |
| Automatic browser authentication extension | Protected token handoff beyond selected normal-login baseline | Normal password/token login and cookie WebSocket tests pass; automatic credential handoff needs separate exposure review |
| Broader manually started server discovery | Additional versions/authentication/runtime layouts | M2 current-user metadata, explicit paths/interpreters, ownership and simple base paths are verified; coverage remains partial |
| Future port customization | M3 fixes native ephemeral allocation; explicit port policy is separate scope | No manual remote-port coordinator is needed for M3 |
| Background/shared tunnel extension | Detached SSH or verified reuse/control socket | Foreground owned cleanup, independent forwards and reconnection are verified through M5; no background mode is needed |
| Additional environment behavior | Activation hooks or kernel-selection UX | M5 executable/workdir profiles are verified; arbitrary shell activation is intentionally absent |
| Broader version/platform matrix | Extend the explicit beta observations | M6 fixes Python 3.11–3.14 and managed Server >=2.20,<3; unknown OS/dependency combinations require new evidence |
| Broader identity reconciliation | Additional shared-filesystem/site identity policies | M5 verifies actual UID isolation, duplicate aliases, changed routes and archived-name reuse; broader site coverage remains M6 |
| Broader scientific filesystem cases | Long network-filesystem workloads and special activation policy | M5 Conda/venv, relative/tilde/symlink/Unicode paths verified; broader site matrix remains M6 |
| Physical reboot/site logout policy | Controlled reboot and PAM/cgroup acceptance | Changed boot identity is detected as stale; physical reboot and last-logout behavior remain unmeasured |
| Installed helper extension | Optional installation/update strategy | Source-only bootstrap is verified without remote installation; an installed helper has no demonstrated need |
| Lifecycle compatibility/migrations | Schema 1.0 and per-operation wire minors are fixed; incompatible writes fail | M6 tests M3/M5 runners without migration; future stored-schema changes require a separate migration decision |
| Broader URL variants | IPv6, HTTPS and TLS hostname mismatch | IPv4 HTTP/simple ASCII base paths and browser WebSockets pass; additional variants require live tests |
| Broader discovery coverage | Additional Conda layouts and legacy runtime formats | Explicit multiple runtime dirs/interpreters and deduplication pass; exhaustive inventory is outside MVP |
| Browser/tunnel edge cases | Suspend/resume and CLI upgrade during an attached session | Browser/tunnel closure and independent reconnect pass; physical client transitions remain unmeasured |

## Architectural decision record format

For substantive changes, record: **Context**, **Decision**, **Consequences**, **Alternatives considered**, **Security impact**, **Test evidence**, and **Date**.

## Deferred scope

Slurm integration, **exhaustive** unmanaged discovery/adoption or control, browser portal, cross-user session sharing and centrally administered profiles. Each requires its own decision and acceptance tests.
