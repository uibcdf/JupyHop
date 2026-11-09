# 23 — 0.2.0 stabilization evidence

Status: in progress. Package metadata remains 0.1.0; 0.2.0 is the target, not a
published release. All real aliases, addresses, users and executable paths stay
in private operator evidence outside the repository. Role labels below do not
identify institutional infrastructure.

## Completed work and observed results

- A real authorized Linux target was reached with the existing SSH configuration.
  Its stdlib-only system Python works for discovery even though doctor correctly
  reports Jupyter absent in that interpreter. Existing Conda environments provide
  the server; no scientific environment was installed or modified.
- Two externally launched, authenticated toy Jupyter servers, 2.17.0 on Python
  3.12.11 and 2.21.1 on Python 3.14.7, were discovered and opened through automatic
  forwards. Their normal password login was required. Managed launch used an
  existing 2.21.1 environment with ipykernel 7.4.0. The target is x86_64 Ubuntu
  26.04.1 LTS, kernel 7.0.0-38-generic, glibc 2.43.
- A short real-site managed test recovered the same server PID, notebook/session,
  kernel PID/ID, in-memory checksum and progressing toy computation from a fresh
  process and login after closing all first-worker connections. Only that UUID
  was stopped/archived. The marked temporary manual servers/projects were removed.
- The first fixture attempt used a temporary JUPYTER_DATA_DIR without preserving
  the ordinary runtime directory; the corrected fixture explicitly selects that
  runtime. This was an experiment setup error, not a discovery result.
- A subsequent managed attempt failed before creating a registry/session record.
  The original underlying exception was not captured and is not claimed solved.
  Read-only status and directory inspection established no registered launch;
  only its marked toy directories were then removed. Later short acceptance
  passed. Reproducible preflight timeout/exec/JSON failures are now correctly
  classified before any registry/launch, without increasing the 8-second bound.
- An installed-client experiment builds the trusted historical 0.1.0 source at
  `21e0dc97161d83088ae6ad850027fa4d17ee4d3c`, installs it without local Jupyter,
  starts a kernel, closes the connection, upgrades that venv to a temporary 0.2.0
  preview, and reconnects concurrent old and independent new clients with separate
  keys/HOMEs/routes. PID/kernel/session/memory/progress and immutable registry/
  runner bytes match. Safe stop/archive pass. This preview must be repeated with
  the final actual 0.2.0 wheel before final distribution acceptance.
- Native terminal authentication passed direct and ProxyJump tests using an
  encrypted fixture key. Ctrl-C, SIGTERM and authentication timeout restore
  terminal echo and leave no owned SSH/proxy process. CLI open prompts once per
  hop and reuses the authenticated private master for discovery, forwarding and
  identity revalidation. Losing its socket fails closed instead of reconnecting.
- The operator completed read-only doctor on a second actual target through a
  real three-machine SSH route, entering that account's SSH password only in the
  native OpenSSH prompt. JSON reported the correct non-root identity and system
  Python 3.14.4, with tmux and systemd user support. Missing Jupyter packages in
  that system Python are an environment selection result, not an SSH failure.

## D43 — Obsolete metadata must not hide live endpoints

The site's ordinary runtime directory contained 495 entries, including 110
obsolete server metadata files. There were no live declared PIDs at inventory.
The earlier probe stopped as soon as its 64-record diagnostic sample filled,
which could hide a later live server or another known runtime path.

Keep the existing 512-entry per-directory scan, 64-candidate sample, time and
output-byte limits. Continue the bounded scan when the sample fills; a verified
ready endpoint replaces a non-ready sample. Sort verified endpoints ahead of
diagnostics before final byte truncation. Preserve complete=false/entry_limit,
all file/UID/socket/authentication checks and every original metadata file.

The regression creates 110 synthetic obsolete records and live servers in the
default and an additional runtime, opens the later server through ProxyJump and
checks metadata bytes and credential redaction. Increasing limits or deleting
obsolete user metadata was unnecessary and was not selected.

## D45 — Native SSH passwords and keys are both required

The maintainer explicitly requires both authentication scenarios for 0.2.0.
Requiring a new key as the only workaround would not meet that requirement.

Use an invocation-owned foreground OpenSSH master in a fresh private directory.
Authentication occurs before RPC/Jupyter credentials are written, with OpenSSH
reading its controlling terminal. Python does not read, cache or pass the SSH
password. Each route authenticates once per CLI invocation; probes and forwards
use only its verified master PID/control socket, with ProxyCommand=false on mux
clients to prohibit fallback. No arbitrary existing/shared master is adopted.
Keep strict host trust, no agent/X11 forwarding, no configured extra forwards,
ControlPersist=no and ForkAfterAuthentication=no.

Interactive SSH keeps the caller's terminal/process group so native prompts work;
cleanup terminates only the owned direct OpenSSH child, whose proxy teardown is
observed in terminal tests. Noninteractive owned masters retain separate process
groups. CLI pool creation is lazy, so validation/stop confirmation still precedes
any SSH request. At most 16 routes are retained until the invocation ends. A
borrowed tunnel cancels only its explicit forward; the invocation closes masters.

With no controlling terminal, or explicit --batch, require noninteractive
authentication. The terminal auth deadline defaults to 120 seconds and is bounded
by --ssh-auth-timeout (1–600); --timeout keeps its existing probe/network bounds.
Jupyter's separate --password-stdin never supplies an SSH password. MFA variants
are not individually demonstrated. Wire and registry contracts do not change.

Alternatives rejected: Python/sshpass credential capture, persistent password
storage, mandatory key provisioning, arbitrary shared sockets, background ssh -f,
and separate fresh authentication for every RPC/forward. Native private control
connections preserve the existing ownership/revalidation model with fewer prompts.
Primary references: [OpenSSH ssh](https://man.openbsd.org/ssh.1) and
[ssh_config](https://man.openbsd.org/ssh_config.5).

## Verification and remaining gates

Observed local CPython 3.14 checks before the final fixture-password additions:
288 tests pass (220 unit, 68 integration); ruff and strict mypy pass. The isolated
installed preview upgrade passes. Hosted CI is being extended for the upgrade
and native Unix-password acceptance on its disposable generated accounts; a new
hosted result is not yet claimed.

A 7200-second real-site toy workload is in progress, with no Jupyter/tunnel
connection to that workload during the hold. Brief unrelated read-only host/
route diagnostics do not establish a controlled last-logout test. Completion,
reconnection and cleanup remain pending until observed.

Remaining: finish endurance and final CI, review/rebuild actual 0.2.0 artifacts
and repeat installed-wheel acceptance; reconcile all current docs/contracts.
Physical home/laptop suspend/network moves, a second physical client and actual
last-logout/reboot policy remain unmeasured. The real password route's doctor
does not by itself demonstrate Jupyter start/kernel operation on that second
target. Do not turn unavailable or unperformed manual cases into passing results.
