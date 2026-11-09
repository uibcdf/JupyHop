# 23 — 0.2.0 stabilization evidence

Status: operational 0.2.0 candidate prepared for pre-1.0 stabilization, unpublished.
All real aliases, addresses, users and executable paths stay
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
  and two-hour acceptance passed. Reproducible preflight timeout/exec/JSON failures
  are now correctly classified before any registry/launch, without increasing
  the 8-second bound.
- An installed-client experiment builds the trusted historical 0.1.0 source at
  `21e0dc97161d83088ae6ad850027fa4d17ee4d3c`, installs it without local Jupyter,
  starts a kernel, closes the connection, upgrades that venv to a temporary 0.2.0
  preview, and reconnects concurrent old and independent new clients with separate
  keys/HOMEs/routes. PID/kernel/session/memory/progress and immutable registry/
  runner bytes match. Safe stop/archive pass. The candidate workflow now uses
  the actual built wheel instead of a temporary version preview; final local
  artifact acceptance is recorded below.
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
- Operator CLI open through the same real password route authenticated and
  completed discovery, then reported the ordinary runtime directory missing.
  No compatible server was found in that partial search; no browser/server
  operation on that target is claimed from that result.

## D43 — Obsolete metadata must not hide live endpoints

The site's ordinary runtime directory contained 495 entries, including 110
obsolete server metadata files. No live current-user declared PIDs were found.
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
Native configuration is resolved for a transport-only master; use stable SSH
aliases rather than per-command Match rules that change account/route between RPCs.
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

## Verification

Local CPython 3.14 observes 294 passing tests (225 unit, 69 integration), ruff and
strict mypy. The isolated installed preview upgrade and clean-wheel smoke pass.
The first
[hosted run](https://github.com/uibcdf/jupyhop/actions/runs/42550984022) observes
293 passing tests on every Python, clean-wheel acceptance and both server-version
comparisons. Python 3.11 also passes the installed preview upgrade. The other
three jobs stop before account/password acceptance because the offline baseline
wheel build lacks its global backend. A fresh Python 3.14 venv reproduces that
failure; adding the declared setuptools backend alone makes the build pass.
The dev extra now explicitly includes setuptools>=77. No runtime dependency is
added. The corrected [hosted run](https://github.com/uibcdf/jupyhop/actions/runs/42552049065)
at ed2a80a completes all six jobs: all four Python versions, actual installed
preview upgrades, clean wheels, both server comparisons, normal-sandbox Chrome,
two actual Unix accounts/isolation/reconnection, native Unix SSH passwords and
mandatory privileged fixture cleanup. Password acceptance forces password auth
on the target and verifies direct/jump open, once-per-invocation prompts, native
retry, cancellation, timeout, terminal restoration and headless refusal. Random
fixture passwords stay private and are removed with the generated accounts/client
fixture; ordinary users/services and real scientific accounts are not modified.

## Site-fixture cleanup audit

An OS-only midpoint audit found the owned server and its ipykernel child alive,
without sending Jupyter HTTP/WebSocket requests. It also found four metadata JSON
files and four native HTML redirects left by earlier completed manual fixtures:
tmux HUP shutdown need not remove Jupyter's ordinary runtime files.

The one-off cleanup selected only the recorded exclusive toy-project nonces,
verified absent PIDs, private ownership/mode/single-link files, matching JSON
identity and HTML loopback port/path, close creation timestamps and unchanged
inodes before removal. Native HTML uses /pilot without the trailing slash, so the
guard parses the URL rather than assuming a byte prefix. All eight own artifacts
were removed; normal runtime entries returned to the original 495 plus the four
files belonging to the still-active endurance manual fixtures. No pre-existing
metadata was deleted or modified.

After endurance completed, the same guards removed its two remaining own JSON
records and two native HTML redirects. The ordinary runtime returned to exactly
its original 495 entries. Separate PID/start-identity verification found neither
the owned managed server nor its kernel alive after stop/archive. All experiment
projects, manual servers and client connections were cleaned; inactive managed
archives intentionally retain their normal recovery evidence.

The reproducible driver now places manual metadata/redirects in its exclusive
private runtime and supplies that explicit known path during discovery. Its
integration tests assert the original runtime file names/bytes remain unchanged
on success and definitive preflight failure. This fixture correction adds no
product adoption or automatic unmanaged metadata cleanup feature.

The subsequent [hosted run](https://github.com/uibcdf/jupyhop/actions/runs/42554470299)
at e15ed77 also completes all six jobs with the isolated site runtimes and CLI
start's piped new Jupyter password separate from native terminal SSH input.
That test actor, not JupyHop, types only a synthetic SSH secret. Privileged fixture
cleanup is observed successful after all password cases.

Read-only logind queries on the real endurance target report effective
KillUserProcesses=false and Linger=no for the current user. No policy, linger or
service configuration was changed. This records configured policy, not an actual
forced last-logout experiment.

## Main files changed

| Area | Files |
| --- | --- |
| SSH authentication and resource lifetime | [connection.py](../src/jupyhop/connection.py), [ssh.py](../src/jupyhop/ssh.py), [tunnel.py](../src/jupyhop/tunnel.py), [CLI](../src/jupyhop/cli.py), [fleet](../src/jupyhop/fleet.py) |
| Discovery and preflight fixes | [discovery probe](../src/jupyhop/_discovery_probe.py), [managed runner/RPC](../src/jupyhop/_managed_remote.py), discovery/open and managed tests |
| Reproducible acceptance | [installed upgrade](../experiments/client_upgrade.py), [site pilot](../experiments/site_pilot.py), [Unix password](../experiments/password_smoke.py), [guarded account fixture](../experiments/m5_accounts.py), [instructions](../experiments/stabilization.md) |
| Automated guards | [native terminal integration](../tests/integration/test_ssh_auth.py), [site integration](../tests/integration/test_site_pilot.py), [site cleanup](../tests/test_site_fixture.py), [account guards](../tests/test_account_fixture.py), [pool cleanup](../tests/test_connection.py) |
| Packaging and CI | [pyproject](../pyproject.toml), [workflow](../.github/workflows/checks.yml); README, CHANGELOG, SECURITY, CONTRIBUTING, quickstart, troubleshooting and compatibility |
| Design and acceptance | Architecture/security/CLI guide, roadmap, D43–D45, scenario ledger, [0.2.0 plan](22-02-stabilization.md) and this evidence report |

## Candidate verification

A 7200-second real-site toy workload passed. No Jupyter/tunnel connection to that
workload was held during the interval. A fresh worker, login and forward recovered
the same server PID, notebook/session, kernel identity, memory checksum and
advancing computation; stop/archive and exact process cleanup then passed.
Brief unrelated read-only host/route diagnostics do not establish a controlled
last-logout test.

The actual 0.2.0 wheel passes local clean-client acceptance without local Jupyter:
profiles/fleet, existing access and managed start/open/status/stop/archive through
ProxyJump, with owned-tunnel cleanup. Installed upgrade from the trusted 0.1.0
wheel also passes with the actual candidate, preserving live server/kernel/
session/PID/memory/progress and immutable registry/runner bytes while upgraded,
old and independent new clients coexist. Stop/archive affects only its toy UUID.
Wheel/source inspection verifies numeric version, MIT, CLI entrypoint, Python
classifiers, zero mandatory dependencies, safe archives and complete source/docs.
The wheel's embedded README matches the UTF-8 source; 225 local documentation
links resolve. Rebuilding from the source distribution produces identical wheel
member names and bytes. Checksums accompany artifacts in dist/SHA256SUMS.

The [candidate workflow](https://github.com/uibcdf/jupyhop/actions/workflows/checks.yml?query=branch%3Amain)
now enforces the actual-wheel upgrade on each Python 3.11–3.14, in addition to
the previously observed six-job regression/browser/account/password matrix.
Each candidate's run must be observed independently; prior green runs do not
substitute for its result.

## Acceptance boundary and next work

The scoped Linux functionality, native password/key authentication, discovery,
managed persistence, concurrency, safe lifecycle and two-hour recovery gates have
observed results. The [gate table](22-02-stabilization.md) maps these results to
the supported matrix. Package publication is a separate maintainer action.

Physical home/laptop suspend/network moves, a second physical client and actual
last-logout/reboot policy remain unmeasured. The real password route's doctor
does not by itself demonstrate Jupyter start/kernel operation on that second
target. Do not turn unavailable or unperformed manual cases into passing results.

The recommended next increment is actual-user stabilization of the declared
0.2.0 workflows, including a separate physical home client and broader site/OS
observations when available. Optional M7 features remain outside this increment.
