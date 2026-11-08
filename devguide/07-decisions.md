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

## Decisions pending before implementation

| Topic | Options / questions | Evidence needed |
| --- | --- | --- |
| Remote helper deployment | Copy/execute helper on demand vs install package on remote | UX, version compatibility, permissions |
| Process manager | systemd --user, tmux fallback, or another mechanism | Linger/login behavior, portability, process identity; no automatic admin changes |
| Remote state | XDG state directory, versioned JSON, lock strategy | Atomicity, concurrent starts, stale state |
| Existing session authentication | Secure retrieval of owned authentication material; explicit-login fallback for unsupported tokens/passwords | Jupyter Server supported APIs, leakage risks |
| Manually started server discovery | Runtime dir enumeration, supported versions, probe ownership/liveness, custom base URL | Prototype in multiple Conda environments |
| Remote port allocation | Jupyter-assigned port vs helper-managed allocation | Race-free selection and verification |
| Local tunnel lifetime | Foreground CLI, detached SSH, or reuse/control socket | Reliable cleanup and reconnection |
| Environment launcher | Explicit Python path, profile command, kernel selection | Safe quoting, reproducibility, cross-env UX |
| Minimum versions | Python, Jupyter Server, OpenSSH, Linux distros | Dependency testing and CI |
| Session identity | Stable random ID, display name, host association | Collision and cross-client behavior |
| Workdir / launch profiles | Explicit remote working directory, environment Python path and safe quoting | Conda/venv and Unicode-path tests |
| Multi-client forward | Foreground/background tunnel tracking and cleanup | Port collisions, process ownership, WebSocket tests |
| Reboot behavior | Mark stale vs optional user-requested restart | Predictability and policy |
| Runtime/helper rollout | No-install discovery vs minimal helper vs on-demand helper | Security, remote Python requirements, updates, installation UX |
| Wire compatibility | Version negotiation and state schema migrations | Cross-client upgrade and concurrent execution tests |
| URL variants | IPv6/HTTP/HTTPS, base paths and TLS hostname mismatch | Live Jupyter and browser/WebSocket tests |
| Discovery coverage | Multiple Jupyter runtime dirs, deduplication and explicit paths | Multi-Conda environment prototypes |
| Browser/tunnel contract | Attached vs supervised background forward, repeat open, close behavior | UX and recovery tests |

## Architectural decision record format

For substantive changes, record: **Context**, **Decision**, **Consequences**, **Alternatives considered**, **Security impact**, **Test evidence**, and **Date**.

## Deferred scope

Slurm integration, **exhaustive** unmanaged discovery/adoption or control, browser portal, cross-user session sharing and centrally administered profiles. Each requires its own decision and acceptance tests.
