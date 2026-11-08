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
| D07 | Managed sessions first; unmanaged discovery deferred | Clear ownership and safer lifecycle |
| D08 | Do not embed site-specific IPs, hostnames or accounts | General reuse and privacy |
| D09 | JupyterHub remains a distinct solution, not a dependency or implementation target | Avoid duplicating multiuser platform features |

## Decisions pending before implementation

| Topic | Options / questions | Evidence needed |
| --- | --- | --- |
| Remote helper deployment | Copy/execute helper on demand vs install package on remote | UX, version compatibility, permissions |
| Process manager | systemd --user, tmux, or another mechanism | Linger/login behavior, portability, process identity |
| Remote state | XDG state directory, versioned JSON, lock strategy | Atomicity, concurrent starts, stale state |
| Existing session authentication | Secure retrieval of owned authentication material | Jupyter Server supported APIs, leakage risks |
| Remote port allocation | Jupyter-assigned port vs helper-managed allocation | Race-free selection and verification |
| Local tunnel lifetime | Foreground CLI, detached SSH, or reuse/control socket | Reliable cleanup and reconnection |
| Environment launcher | Explicit Python path, profile command, kernel selection | Safe quoting, reproducibility, cross-env UX |
| Minimum versions | Python, Jupyter Server, OpenSSH, Linux distros | Dependency testing and CI |
| Session identity | Stable random ID, display name, host association | Collision and cross-client behavior |
| Reboot behavior | Mark stale vs optional user-requested restart | Predictability and policy |

## Architectural decision record format

For substantive changes, record: **Context**, **Decision**, **Consequences**, **Alternatives considered**, **Security impact**, **Test evidence**, and **Date**.

## Deferred scope

Slurm integration, unmanaged process discovery, browser portal, cross-user session sharing and centrally administered profiles. Each requires its own decision and acceptance tests.
