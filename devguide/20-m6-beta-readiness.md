# 20 — M6: beta compatibility, security and release preparation

Date: 2026-11-08. **Local M6 acceptance passed; 0.1.0b1 prepared, unpublished.**
No M7 extension or package publication is included. This report records work,
experiments, decisions, files, tests, acceptance, limits and the next step.

## Work delivered

- Reviewed transport, authentication, ownership, bindings, input quoting,
  filesystem/state safety, compatibility and interrupted-resource cleanup.
- Extended SIGTERM/SIGHUP handling to the entire command, so interrupting an SSH
  probe also unwinds the owned transport rather than leaving it behind.
- Refused a password prompt's echo fallback; protected stdin remains explicit.
- Fixed a reader race with atomic registry updates using bounded reopen, without
  weakening ownership, mode, link or no-follow checks.
- Established a distinct managed-start minimum after native version experiments:
  Jupyter Server >=2.20,<3. Older existing servers remain independently discoverable
  when they have correct private metadata and the supported endpoint/auth shape.
- Added a quickstart, troubleshooting, compatibility/version policy, contribution
  instructions, security reporting policy, release guide and CHANGELOG.
- Prepared version 0.1.0b1/Beta metadata, offline artifact inspection and an
  expanded CI matrix with downloadable distributions and no publishing credentials.

## Experiments and results

**Native Server 2.17.0, Python 3.11.18.** An existing server started with an
explicit fixture port was discovered through ProxyJump, authenticated and executed
a kernel. An unmodified managed port=0 launch failed; a separate native ServerApp
probe showed `app.port == 0` while the actual bound socket had a nonzero port.
The immutable runner cannot checkpoint that false advertised port. This reproduces
a concrete native cause outside the earlier Alpine/QEMU/TCG experiment; it does
not prove every aspect of that VM failure had the same cause.

Upstream Server 2.20 records the fix to read the bound socket's actual port.
Server 2.21.1 separately fixes compatibility with Tornado 6.5.9+. Sources:
[official changelog](https://jupyter-server.readthedocs.io/en/stable/other/changelog.html).
Normal password/token/cookie authentication remains upstream's policy:
[official security documentation](https://jupyter-server.readthedocs.io/en/stable/operators/security.html).

**Refusal, then Server 2.20.0.** With the new preflight, 2.17 existing-server
open/kernel still passes and managed start returns `unsupported_server_version`
before creating a registry or process. The same selected-server experiment passes
start/status/stop/archive on native 2.20.0 with Tornado 6.5.8. No remote port
coordinator, port reservation loop or implicit dependency installation is added.

**Signals before open.** Actual CLI subprocesses receive SIGTERM or SIGHUP while a
private SSH/ProxyJump probe is waiting. The CLI exits 130 and its owned local SSH
child is reaped. Existing open-signal/independent-kernel regressions remain intact.

**Bulk data and sustained channel.** An 8 MiB deterministic fixture file is uploaded
and fetched through Jupyter's contents API over ProxyJump; SHA256 agrees. One
authenticated WebSocket executes 64 sequential requests with 64 KiB stream output
each and checks every response. This is a bounded release smoke, not an hours-long
or physical-WAN throughput benchmark. Only fixture data/kernel are created/deleted.

**Live authentication change.** A private fixture-only control file rotates the
live Jupyter password provider, without HTTP control extensions or restarting the
server. After the first tunnel/client closes, a fresh tunnel keeps the same server
ID/PID; a new login using the old password is denied and the new password succeeds.
JupyHop caches neither. Existing cookie revocation is upstream policy, not a new
JupyHop guarantee or password-management feature.

**Concurrent atomic-read race.** A contended regression on Python 3.12 reported
`unsafe_state` during launch. Investigation found that an atomic record update can
unlink the previously opened inode before its single-link check. A deterministic
unit case uses real atomic replacement between open/check to reproduce this.
Readers now discard that retired descriptor and reopen the current name, at most
three times; repeated replacement returns `registry_busy`. New reads retain every
ownership/mode/link/no-follow/size check. Final four-version regressions pass.

**Legacy and artifacts.** Trusted local M3/M5 sources exercise immutable historical
runners with current status/idempotent stop, preserving their bytes/hash and schema.
Clean-wheel clients and browser reconnection are separate gates below. Root account
creation is not repeated: M5's actual two-UID/auth/lifecycle evidence and verified
cleanup remain applicable; no privilege requirement is introduced to the client.

## Decisions D38–D40

**D38 — Native ephemeral ports set the managed minimum.** Prefer Jupyter's corrected
port=0 implementation to adding a remote allocator for old releases. Reject older
versions before state creation and explain how to select an existing compatible
environment. Discovery is a separate capability: 2.17 existing open is observed,
not silently adopted into managed lifecycle. Recommend 2.21.1; 2.20's exact older
Tornado combination is compatibility evidence, not a blanket old-stack endorsement.
The source-only preflight changes future launches; live runners are not replaced.

**D39 — Interruptions, private input and atomic reads.** SIGTERM/SIGHUP use the same
unwinding path as KeyboardInterrupt during all command phases. Transport finally
blocks reap only their own groups. Remote writes still have unknown outcome after
interruption; reconciliation/retry policies do not change. Convert GetPassWarning
into refusal before fallback input can echo. Reopen atomically retired record
inodes with a three-attempt bound, never consuming unchecked bytes or relaxing
file checks. No background signal watcher, credential cache or forced remote
cleanup is needed.

**D40 — Reviewed beta artifact, separate publication.** Keep zero mandatory Python
dependencies and MIT licensing. Version package and CLI together; verify wheel and
sdist contents/entrypoint/license/version, safe member paths and source inclusion
using stdlib. Build metadata alone does not establish runtime compatibility:
fresh installed clients, browser and server-version experiments remain necessary.
CI has no automatic publishing step. The candidate and its documentation are
reviewable before any registry/tag/release action.

## Internal security review

This is an internal review, not an independent security audit.

| Boundary | Evidence / remaining qualification |
| --- | --- |
| SSH trust and route | Strict target host checking, unknown/changed key tests, native Include/Match/ProxyJump. Local SSH config, ProxyCommand/Match exec and jump configuration remain trusted. |
| Remote shell/input | Separate argv and POSIX remote quoting, executable/name/path validation and actual metacharacter tests. Login shell must be POSIX-compatible. |
| Authentication | Authenticated API/cookie WebSockets, wrong-password denial, token-free open/history, password stdin/hash-only persistence, echo-fallback refusal and live rotation. No credential cache or cookie-revocation promise. |
| Authorization | Real two-UID M5 isolation, registry scope and exact managed UUID; unmanaged/foreign stop/archive refused. A malicious same-UID process/root/authorized host is outside the boundary. |
| Bindings and forwards | IPv4 loopback only, native ephemeral server ports, private owned SSH master verification, collision retry and ignored configured forwarding. IPv6/HTTPS remain explicitly unsupported. |
| State/files | Private ownership/modes, no-follow bounded reads, single-link sensitive files, locks/atomic writes/fsync, schema/hash/provenance checks and unsafe-file tests. Archives retain sensitive recovery evidence. |
| Process control | Open pidfd before identity checks; graceful selected-only SIGTERM, no PID-only or forced-kill fallback, wrong PID/boot/socket refusal. No automatic restart. |
| Resource cleanup | Probe limits/timeouts, command-wide signals, open signal tests, fresh forwards and interrupted start/stop reconciliation. Site policy/physical reboot is not controlled. |
| Output/privacy | Allowlisted bounded JSON, duplicate/type/control rejection, suppressed raw remote errors and secret sentinels; no developer paths, actual fixture identities or key blocks in source/artifacts. |
| Packaging/rollout | MIT, explicit supported Python classifiers, no mandatory dependencies, artifact/source checks; installed helper and automatic migration absent. New clients do not rewrite running launchers. |

## Files changed

Client: cli.py, managed.py, _managed_remote.py, __init__.py and pyproject.toml.
Tests: managed input/version tests and test_m6_release.py. Fixture Jupyter port
selection supports the explicit older-server experiment. Added m6_compatibility.py
and release_check.py; extended CI and MANIFEST. Added CHANGELOG, CONTRIBUTING,
SECURITY and docs/{quickstart,troubleshooting,compatibility,releasing}. Updated
README and current devguide decisions/security/runtime/UX/roadmap/ledger; historical
milestone reports remain unchanged.

## Validation

Product code is frozen for the final suite. The suite has 266 cases: 210 unit and
56 integration. Initial temporary-environment runs omitted the editable client
installation and three CLI subprocess cases failed to import jupyhop; the
preparation was corrected and full affected suites rerun. This setup failure is
not reported as a passing product run.

A final fixture-only correction mocks the preflight's tmux lookup so its unit
test does not depend on an installed backend. The 210-case unit suite was rerun;
the product code and four-version integration results are unchanged. Unit fixture
key preparation still requires ssh-keygen, now explicit in CONTRIBUTING.

| Python / server stack | Full regression | Clean installed wheel |
| --- | --- | --- |
| 3.11.18 / Server 2.20.0, Tornado 6.5.8 | 266 passed | Passed |
| 3.12.16 / Server 2.21.1 | 266 passed | Passed |
| 3.13.18 / Server 2.21.1 | 266 passed | Passed |
| 3.14.10 / Server 2.21.1 | 266 passed | Passed |

Additional gates pass: selected 2.17 refusal/open and 2.20 lifecycle; legacy M3/M5
status/idempotent stop with unchanged runner bytes; actual Chrome/JupyterLab
existing login and managed reconnect to the same live kernel; clean wheel without
local Jupyter in all four versions; Ruff lint/format, mypy and wheel/sdist checks.
Documentation and all 65 scenario IDs remain mapped; M7 Slurm and explicitly
unmeasured physical/site cases are not counted as observed product features.

Observed OS: Ubuntu 26.04.1 LTS, Linux 7.0.0-43-generic, OpenSSH 10.2p1, tmux 3.6,
JupyterLab 4.6.4, ipykernel 7.4.0, Chrome 157.0.8103.38. Newer server environments
use Tornado 6.6. Ruff 0.17.4 and mypy 2.4.1 were installed in the dedicated
development environment with mamba. CI defines four Python versions and
2.17/2.20 comparisons; its YAML/matrices validate locally, but GitHub execution
has not been observed and is not claimed as passed.

Temporary mamba compatibility environments were removed after final wheel tests;
fixture contexts cleaned their servers/kernels/forwards/browser profiles. The
development environment is preserved, with its editable client/metadata updated
to 0.1.0b1. No new test accounts or privileged infrastructure were created in M6.

## Acceptance, limits and next step

Local beta acceptance passes: guided existing-open and managed start/reconnect/
stop work in clean clients without local Jupyter; mandatory scenarios have
observed evidence or explicit supported-scope/manual disposition in the ledger;
the reviewed artifacts contain no real infrastructure details or credentials.
MIT, zero mandatory dependencies, supported-version metadata and safe state/wire
rollout are preserved. Candidate wheel/sdist and separate SHA256 checksums are
available under dist for review, without package publication.

Remaining limits: no physical reboot/PAM/last-logout or real LAN/WAN/suspend test,
hours-long workload, independent external audit, other OS/architecture/free-threaded
matrix, universal 2.x/dependency range, automatic auth handoff, migration, permanent
archive deletion or institutional guarantees. Unknown schema/unsafe identity and
unsupported endpoints fail closed. Existing valid cookies follow Jupyter policy.

Stop for review of the exact beta artifacts and an
optional authorized workstation pilot/remote CI run. Publication is a distinct
maintainer action; M7 remains optional and has not started.
