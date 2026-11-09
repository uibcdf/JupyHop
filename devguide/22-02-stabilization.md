# 22 — 0.2.0 operational stabilization

Status: planned. Current package: 0.1.0. Target: 0.2.0, using the numeric
x.y.z release policy. This increment follows M6 and precedes optional M7 work.
No 0.2.0 functionality or real-site acceptance is claimed by this plan.

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

**Open scope decision:** current SSH transport enforces BatchMode and requires
noninteractive authentication (for example unlocked keys/agent). Password-only
SSH and interactive MFA are not a demonstrated supported workflow. Decide from
the intended users/pilot whether they are required for 0.2.0. Any implementation
must retain native OpenSSH authentication and host trust. A working interactive
SSH login alone does not establish compatibility with today's BatchMode client.

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
  transitions and hours-long endurance are not yet observed.
- Immutable historical runner compatibility is observed. A full installed
  0.1.0-to-0.2.0 client upgrade while a scientific-style kernel stays alive is
  still a separate stabilization gate.

Detailed evidence: [M6 local report](20-m6-beta-readiness.md),
[hosted CI follow-up](21-m6-github-ci.md) and
[the 65-scenario ledger](14-acceptance-ledger.md).

## Required acceptance gates

| Gate | Required demonstration | Current state |
| --- | --- | --- |
| Support and authentication contract | Freeze client/remote OS, Python/server versions, SSH auth and supported endpoints; clearly diagnose unsupported prerequisites | Baseline documented; pilot OS/auth choice pending |
| Real existing-server open | With an existing SSH alias, discover/open a manually launched current-user server, including selected Conda runtimes and ProxyJump, without choosing ports or requiring TOML; normal authorized login works | Automated mechanism passes; real-site pilot pending |
| Real managed workflow | Select an existing Python/project, start a uniquely named temporary session, close first client/tunnel/browser, then use an independent authorized client to recover the same notebook/kernel/PID/memory; stop/archive only that created UUID | Loopback and real-UID mechanisms pass; real-site pilot pending |
| Endurance and route recovery | A bounded multi-hour toy workload survives supported client disconnections; direct/ProxyJump routes reach the same registry; interruption/reconnect does not create a duplicate server | Short automated cases pass; endurance and physical route/client transition evidence pending |
| Site persistence and failure truth | Establish the dedicated test account's actual logout policy; unavailable routes, process loss/reboot identity, changed credentials and stale state give correct recovery guidance without touching unrelated workloads | Simulation/error mechanisms pass; safe site-policy observation pending |
| Installed upgrade | Launch via an installed 0.1.0 wheel, upgrade a client to 0.2.0, reconnect independently and retain PID/kernel/session/memory and immutable runner; verify documented old/new-client compatibility or explicit refusal | Historical source compatibility passes; installed-version upgrade gate pending |
| Usability and regression | A fresh client follows the quickstart; common errors identify the required action; CLI/JSON/exit contracts match docs; the declared supported matrix stays green, with the actual pilot OS recorded and additional OS versions tested before claiming them | Current matrix passes; pilot usability and final support matrix pending |
| Distribution | Build/review 0.2.0 wheel and source with matching version/license/entrypoint/checksums, no mandatory Python deps or real infrastructure/credentials; clean install/upgrade and updated release notes pass | Build machinery exists; 0.2.0 artifacts await gate completion |

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

1. Confirm pilot aliases, client OS and SSH auth; freeze the 0.2.0 support contract.
2. Prepare the real-site and installed-wheel upgrade experiments. Work that needs
   no real target can proceed independently of the pilot.
3. Run the pilot and bounded endurance, then fix demonstrated defects and UX gaps.
   Add meaningful regressions for those findings and extend the observed matrix.
4. Reconcile current docs/CLI/ledger, run final checks and build reviewed 0.2.0
   artifacts. Bump the package only when the target scope and acceptance are clear.

Maintainers continue small coherent commits and direct pushes to main. Tags,
GitHub releases and PyPI upload remain separate explicitly requested actions.
M7 Slurm, centralized/web services, cross-user sharing, exhaustive discovery and
additional backends remain separate optional work. Automatic browser credential
handoff or a systemd backend needs demonstrated pilot necessity and its own
security/operational acceptance; neither is assumed to be required here.
