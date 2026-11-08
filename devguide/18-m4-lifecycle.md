# 18 — M4: lifecycle and reconnection validation

Date: 2026-11-08. **M4 complete within the acceptance and limits below.** M5 has
not started. This report covers work, experiments, decisions, files, tests,
acceptance, limitations and the recommended next milestone.

## Shipped scope and contracts

```console
jupyhop status workstation
jupyhop status workstation SESSION_ID --json
jupyhop open workstation SESSION_ID
jupyhop stop workstation SESSION_ID
jupyhop stop workstation SESSION_ID --yes --json
```

M4 adds `status HOST [UUID]` and `stop HOST UUID [--yes]` for managed sessions.
Names, unmanaged discovery IDs and bare PIDs never authorize lifecycle actions.
`stop` warns that kernels/computations terminate and requires either a terminal
confirmation or explicit `--yes`. `discover`/`list`/`open` remain read-only.
`status` reconciles verified readiness after a lost launch reply. It does not
automatically launch/restart/adopt a server. A timeout is an unknown observation.

Wire 1.3 adds lifecycle operations and `stopping`/`stopped` observations. Registry
schema stays 1.0: an optional boolean `stop_requested` records intent without
changing existing stored states. M3's immutable runners preserve this additive
field during their normal atomic updates. No runner is overwritten or migrated.
Unknown schema major/newer minor remains a refusal before writes.

Observation states: `ready` means live verified process/listener/auth; `starting`
means a launch intent whose readiness is not yet verified; `stopping` means stop
intent with a still-live recorded identity; `stopped` means stop intent plus
observed process exit; `stale` means previous boot, missing or replaced process;
`unreachable` retains uncertainty when inspection or HTTP is unavailable. A stale
record cannot authorize signalling a replacement process or imply kernel memory
survived. No transparent reboot/crash restoration is offered.

Lifecycle errors use exit 13 when pending/unconfirmed, 11 for missing/unverified
managed authority, 5 for unsafe/incompatible state, and 4 for missing pidfd
capability. Stop transport loss is an unknown outcome, not proof of success.
Default stop waits up to ten seconds for graceful exit within the transport
budget; timeout retains intent and reports pending. No forced recovery option.

## Experiments and decisions (D29–D33)

### Stop by pinned process descriptor

Prototype result: the development Conda Python 3.14 omits `os.pidfd_open` and
`signal.pidfd_send_signal`; the system Python exposes them. The kernel and native
libc support the operations. A disposable `/bin/sleep` child was pinned, sent
SIGTERM, observed exited through its descriptor, and could not be signalled after
exit through that descriptor. No raw architecture-specific syscall numbers are
used. Prefer Python's APIs, otherwise feature-detect libc's named wrappers with
stdlib ctypes; if neither works, fail closed and allow selecting a different
helper Python. No PID-only signal fallback.

The product `PinnedProcess` native-API branch was also exercised under the system
Python against a disposable child, separately from the Conda/libc path. Both
branches observe exit through the pinned descriptor.

Open the descriptor before checking boot/UID/start time, exact runner argv/hash,
private tmux pane PID and recorded listener inode. Persist intent atomically under
the registry lock before sending SIGTERM to that descriptor. Jupyter handles
graceful shutdown and its own kernels. No tmux kill-server, process-group signal,
SIGKILL escalation, or signal to an unmanaged server is used by product code.
Waiting for exit does not retain the global lock. Retry after lost replies is
safe: re-pin/revalidate, or observe that the original process is already gone.

References: [Python pidfd APIs](https://docs.python.org/3.14/library/os.html#os.pidfd_open),
[signal API](https://docs.python.org/3.14/library/signal.html#signal.pidfd_send_signal).
The installed Jupyter Server 2.21.1 `init_signal`/`_signal_stop` source confirms
SIGTERM delegates to native `ServerApp.stop(from_signal=True)`.

### Persistence policy

The candidate backend remains the dedicated per-session tmux server. No daemon,
systemd user-bus construction, linger changes or OS configuration changes are
introduced. Site logout/cgroup policy can kill tmux; a surviving HTTP listener
alone is not evidence of surviving kernel memory. The fixture has no PAM/logind,
so its final SSH disconnect is not a claim about a physical OS's last-login
policy. [systemd's own logind documentation](https://github.com/systemd/systemd/blob/main/man/logind.conf.xml)
describes the relevant process-killing policy. Explicit systemd backend selection
needs a user-manager fixture and site-policy acceptance; no automatic backend
switch is justified by local manager availability alone.

Read-only observation in this environment: local `systemctl --user is-active
default.target` is active, while the disposable remote no-PAM session reports
unavailable. The tested tmux fallback preserves the kernel after all first-client
connections close. This justifies retaining the already proven backend and
avoids installing or changing systemd policy merely to satisfy an abstraction.

### Independent-client reconnection

`experiments.m4_reconnect` passed: two separate client processes, different
generated SSH keys/configs, private local HOME directories and direct/jump routes.
Client A creates a notebook session and kernel, sets a memory marker and starts a
background calculation. It closes HTTP/WebSocket, tunnel and SSH connections and
exits. Client B discovers by UUID, authenticates afresh by password, finds the
same notebook session/kernel/PID and verifies marker 42 plus calculation result.
It then gracefully stops that same server. No old cookie, port, control socket,
password cache or local JupyHop state is transferred. These are independent
authorized software clients on one disposable Linux host, not two physical
machines or network namespaces.

### Failure and compatibility experiments

The integration fixture delays the remote launch reply after process spawn and
checkpoint; SIGINT makes the local transport close its private SSH/ProxyJump
group before receiving that reply. The next client's status promotes the same
starting record to ready; it does not launch a duplicate. A second delay loses
the stop reply after graceful exit. Status observes stopped and repeated stop
remains safe. A unit fault between persisted stop intent and signal also proves
that explicit retry re-pins/revalidates rather than trusting the marker alone.

Two concurrent stops complete or report pending safely. Concurrent same-name
starts retain M3's deterministic reservation. Boot identity and PID/start-time
replacement simulations report stale and send no signal. Substituted unrelated
process identity/socket metadata is refused while both the real server and
unrelated process remain alive. SIGKILL is used **only by a fixture** to simulate
a newly created server crash; product code has no escalation and does not restart.
An initialization failure retains failed status even after its process disappears.

`experiments.m4_compatibility --legacy-ref 729aa30` passed using M3 source from
that trusted local commit. Its immutable runner remains byte-for-byte unchanged,
status verifies it and graceful/idempotent stop works. M3's runner preserves the
optional stop-intent field while writing its existing exited state. Newer schema
minor/major refusal leaves records and running servers unchanged. Rejected
alternatives: changing the stored state machine under old writers, implicit
migration, replacing running launchers, PID-only signals or tmux kill-server.

## Tests and results

Linux, OpenSSH 10.2p1, tmux 3.6, Jupyter Server 2.21.1, ipykernel 7.4.0;
JupyterLab 4.6.4 and Chrome 157.0.8103.38 for browser acceptance.

| Python | Unique automated cases validated | Clean wheel client, no local Jupyter |
| --- | --- | --- |
| 3.11.18 | 205 passed | Passed |
| 3.12.16 | 205 passed | Passed |
| 3.13.18 | 205 passed | Passed |
| 3.14.10 (development) | 205 passed | Passed |

Validation sequence: full regression (204 passed on each version), followed by
the complete M4 integration module (10 passed on each) after adding one extra
simultaneous-forward/kernel case and making interruption close SSH explicitly.
The final unique set is 157 unit plus 48 integration cases; the application code
is unchanged between those successful runs. Older M1–M3 regressions are included.
Compatibility interpreters/dependencies were created temporarily with mamba;
the development 3.14 environment was preserved.

`experiments.browser_smoke --managed --reconnect` passed with default Chrome
sandbox/private profile: normal password login, Lab, cookie WebSocket execution,
no token query in history, then **actual browser and tunnel exit** followed by a
new key/HOME/client login and recovery of that same kernel's memory marker.
The notebook association/background-computation check is also an integration
case; it verifies session ID, kernel ID, server PID and result, not HTTP alone.

Clean-wheel experiments install offline into fresh venvs without local Jupyter
and exercise existing-server access, managed start/open/status, idempotent stop
through ProxyJump and owned-tunnel cleanup. Ruff lint/format, mypy, wheel/sdist,
MIT metadata, relative documentation links and private-path/key scans are checked
locally. GitHub's updated CI matrix has not been observed in this local iteration.
All 65 scenario IDs remain mapped in [14](14-acceptance-ledger.md).

The wheel harness was corrected to remove inherited PYTHONPATH/PYTHONHOME before
creating/installing the clean client. Otherwise pip could see source-tree metadata
and skip the same-version wheel, leaving no installed CLI. The corrected isolated
install and lifecycle smoke passed on all four interpreters.

## Files created or modified

Created `src/jupyhop/lifecycle.py` and `_lifecycle_remote.py`, unit tests in
`tests/test_lifecycle.py`, integration in `tests/integration/test_m4_lifecycle.py`,
`experiments/m4_reconnect.py`, `experiments/m4_compatibility.py` and this report.
Updated managed observations/provenance, discovery wire/parser/selection label,
CLI/errors, earlier unit fixtures, browser/package smoke, CI, README and current
devguide architecture/security/UX/protocol/roadmap/decisions/acceptance references.
Earlier milestone reports remain historical. MIT license and zero mandatory
Python runtime dependencies are unchanged.

## Acceptance and limitations

M4's bounded product acceptance is satisfied: independent authorized clients
recover the same live server/notebook/kernel and memory after closing first-client
connections; simultaneous forwards do not restart it; graceful stop requires
verified managed authority and explicit UUID confirmation; stale/replaced/boot
identity is detected; concurrent starts/stops and lost replies retain recovery
evidence; no credential leaks or automatic scientific-workload restart.

These clients share one physical Linux host but have separate processes, keys,
HOMEs/configs, HTTP authentication and SSH routes. Real host reboot, two physical
clients, PAM/logind final logout/linger/cgroup teardown, long-running scientific
load and two different remote Unix accounts are not tested. Boot-change tests
are simulations, not a claim that a reboot preserved or destroyed an observed
kernel. Site process-killing policy can defeat tmux persistence; no user-manager
provisioning, sudo, linger changes or systemd backend is shipped.

Other limits: Linux pidfd capability is needed for safe stop; absent APIs/wrappers
refuse rather than signal by PID. SIGTERM may take longer than the budget or leave
orphaned resources after a crash; inspect status and native Jupyter state. A
pre-PID request remains unconfirmed starting rather than being silently retried.
One corrupt registry entry still fails managed state closed; unmanaged discovery
remains partial. A server's death alone does not prove every kernel died after
an abnormal crash; the graceful-stop test separately observes its kernel exit.

Records, private hashes and runtime evidence are retained, with the existing
128-record bound and reserved names. No cleanup/name reuse command or automatic
deletion is shipped: deleting connection/recovery data without an orphaned-kernel
policy would exceed the safe stop contract. This is an explicit operational limit
to address before sustained use, not hidden behind a completion claim. Live
credential rotation, profile configuration and broader version migration remain
separate compatibility work.

## Next milestone

**M5 — real scientific and multi-host workflows:** profiles/environment UX,
multiple hosts and actual remote-account isolation, plus explicit registry
retirement/name reuse designed to preserve orphaned-kernel recovery evidence.
Stop here for review; no M5 implementation is started.
