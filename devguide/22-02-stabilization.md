# 22 — 0.2.0 operational stabilization

Status: operational candidate 0.2.0 prepared for pre-1.0 stabilization; see
[observed evidence](23-02-stabilization-evidence.md). Numeric x.y.z naming follows
the maintainer policy. This increment follows M6 and precedes optional M7 work.
Package publication and unperformed physical-client/site cases are not claimed.

## Objective and supported boundary

Deliver a usable pre-1.0 version whose declared workflows pass both automated
regression and an authorized real-site pilot, with actionable recovery and a
repeatable installation/upgrade path. Completion means all required gates below
have observed results for the declared support matrix; it is not a promise about
every SSH/Jupyter/operating-system combination or absence of all possible bugs.

The baseline is Linux client/remote, CPython client 3.11–3.14, remote helper
Python >=3.11, verified IPv4 loopback HTTP Jupyter endpoints, ordinary Jupyter
login and private tmux for managed launch. Managed Server >=2.20,<3 and pidfd
stop requirements remain separate from existing-server access. See
[compatibility](../docs/compatibility.md).

**Confirmed scope:** the maintainer requires both native SSH password prompts and
keys/agent for 0.2.0. Invocation-private connections now delegate terminal input
to OpenSSH and reuse only their own verified master. Headless/--batch operation
requires noninteractive authentication. Terminal, real-route and Unix
password-fixture evidence are tracked in [the stabilization report](23-02-stabilization-evidence.md).
Interactive MFA variants still require their own evidence; none is assumed passed.

Client operating systems beyond Linux, IPv6/HTTPS and unusual authentication
setups need explicit scope/evidence decisions. Do not implicitly add them to a
Linux/IPv4 support claim or advertise them before testing.

## Existing baseline

- M0–M6 acceptance is recorded within the documented boundaries. Hosted CI observes
  270 tests per Python 3.11–3.14,
  clean-wheel clients without local Jupyter, Chrome, two actual Unix UIDs,
  server-version comparisons and fixture cleanup.
- Existing/discovered servers are read-only for lifecycle. Only exact verified
  managed UUIDs can authorize stop; archive preserves inactive recovery evidence.
- Separate clients, browser/tunnel closure, normal reauthentication and the same
  surviving kernel/session/memory are demonstrated on disposable loopback targets.
- Signals, lost replies, port/identity conflicts, partial discovery, password
  rotation and bounded data/WebSocket traffic are covered. Physical network/site
  transitions were not part of that baseline; the subsequent two-hour real-site
  endurance result is recorded in the stabilization report.
- Immutable historical runners and installed 0.1.0-to-0.2.0 preview clients are
  observed with the same live kernel. Final packaging uses the actual 0.2.0 wheel;
  its local/hosted checks accompany candidate preparation.

Detailed evidence: [M6 local report](20-m6-beta-readiness.md),
[hosted CI follow-up](21-m6-github-ci.md) and
[the 65-scenario ledger](14-acceptance-ledger.md).

## Required acceptance gates

| Gate | Required demonstration | Current state |
| --- | --- | --- |
| Support and authentication contract | Freeze client/remote OS, Python/server versions, SSH auth and supported endpoints; clearly diagnose unsupported prerequisites | Linux CPython 3.11–3.14; native terminal passwords/passphrases and keys/agent; endpoint and MFA limits documented |
| Real existing-server open | Discover/open manually launched current-user servers in selected Conda runtimes; preserve normal login and automate forwarding | Real two-environment direct open/login; automated Jupyter/password ProxyJump; real three-machine SSH/password doctor and honest empty discovery. Positive Jupyter open on the second actual target remains unobserved |
| Real managed workflow | Start in an existing Python/project; disconnect and recover the same server/kernel/session/memory; stop/archive only its new UUID | Real Linux target passes short and 7200-second recovery; independent key/HOME/client processes pass in CI. A second physical client remains a separate manual observation |
| Endurance and route recovery | A bounded multi-hour toy workload survives disconnection; alternate configured routes do not create duplicate managed servers | 7200 seconds and final memory/progress/identity pass; direct/jump/changed-route mechanisms pass. Physical home/network/suspend transitions remain unmeasured |
| Site persistence and failure truth | Observe configured site policy and safe disconnect behavior; process loss and changed credentials must be reported truthfully | Effective KillUserProcesses=false/Linger=no recorded without changes; real SSH closure/endurance and simulated reboot/stale/error cases pass. Forced last logout/physical reboot are not claimed |
| Installed upgrade | Installed 0.1.0 baseline to actual 0.2.0 candidate, concurrent old/new clients, same live kernel and immutable runner/registry | Actual 0.2.0 wheel passes locally with upgraded, concurrent old and independent new clients; the candidate workflow enforces this on all four Python versions |
| Usability and regression | Fresh-client instructions, actionable errors and CLI/JSON/exit contracts match the declared supported matrix | 294 tests per Python and six successful hosted jobs; real operator password diagnostics; fresh clients without local Jupyter |
| Distribution | Matching numeric version, MIT, CLI entrypoint, no mandatory Python deps, complete safe wheel/sdist and clean installation | Local 0.2.0 artifact inspection, checksums and actual-wheel clean install/upgrade pass; publication is separate |

These gates reuse the existing NET, DISC, LIFE, SCI, SEC and UX scenarios rather
than introducing unrelated features. In particular, real network transitions
extend NET-05/07/12/14/15; persistence and client upgrades extend LIFE-02/03/06/
11/14/15/16/17; known runtime paths/environment selection extend DISC-03/09 and
SCI-01/02/03/04; onboarding and honest failure paths extend UX-01/02/05/06/07/08.

## Safe pilot procedure

1. Select authorized test host/account aliases and the actual client OS/auth
   method. Keep real aliases, users, addresses, paths and credentials outside
   committed examples/reports; use generic role labels in evidence.
2. Inventory prerequisites and discovery using read-only commands. Opening an
   existing server preserves its original ownership/lifecycle and uses its normal
   private login. Do not request passwords/tokens through chat or generic logs.
3. For managed/endurance work, create a dedicated temporary project and a fresh
   JupyHop UUID with synthetic data/kernel variables. Record identity privately.
   Only that created session may be stopped/archived by the experiment.
4. Observe background progress and memory across independently authorized clients
   and configured routes. Agree the endurance duration before running it; a
   representative target is two to four hours, not an indefinite workload.
5. Client suspend/network changes are operator-controlled manual steps. Test last
   logout or physical reboot only in a dedicated disposable account/host/VM where
   no scientific workload can be affected. Never force logout/reboot or change
   linger/PAM/systemd policy on an active scientific account to make a test pass.
6. Record exact software versions, observations and failures using redacted
   roles. Stop/archive the experiment's own UUID, close owned forwards and remove
   only its temporary resources. Preserve scientific data and unmanaged state.

Unavailable pilot infrastructure is a pending gate, not passing evidence. A
correct explanation that a site kills user workloads can satisfy the supported
policy boundary; persistence must not be promised on that site unless a separately
reviewed, permitted supervision path is actually demonstrated. Reboot destroys
ordinary kernel memory; expected behavior is truthful stale/lost-state detection.

## Implementation order and decisions

1. Keep 0.2.0 within the observed Linux/endpoint/authentication boundary above.
2. Stabilize with actual users and a second physical home client when available;
   record exact evidence rather than broadening claims from unavailable cases.
3. Fix demonstrated defects with meaningful regressions, run the matrix and
   rebuild reviewed numeric-version artifacts for each candidate increment.
4. Extend OS/auth/URL/process-manager scope only after its own acceptance.

Maintainers continue small coherent commits and direct pushes to main. Tags,
GitHub releases and PyPI upload remain separate explicitly requested actions.
M7 Slurm, centralized/web services, cross-user sharing, exhaustive discovery and
additional backends remain separate optional work. Automatic browser credential
handoff or a systemd backend needs demonstrated pilot necessity and its own
security/operational acceptance; neither is assumed to be required here.
