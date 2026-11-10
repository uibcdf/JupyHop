# Changelog

## 0.3.0 — session usability

- Always show a terminal chooser for open without a selector, including a single
  candidate. Add exact managed --name selection, resume as an open alias and a
  thin manage menu over the same guarded operations. Name/number choices pin UUIDs.
- Show managed ready/stopped/review counters, retained slot use and bounded archive
  history. Unknown counts remain unknown; partial history is a lower bound.
- Reject a new start atomically when 128 unarchived records already exist, before
  creating a 129th entry. Explain how to release capacity with verified archive.
- Confirm interactive stop and archive together, retaining evidence and releasing
  names after confirmed stop. Add --keep-record; UUID --yes scripts retain stop-only
  behavior unless --archive explicitly authorizes both phases. Report partial
  completion and same-UUID recovery without automatically retrying uncertain writes.
- Classify SSH ownership/write failures and connection timeouts with conditional
  remedies. Capture bounded stderr while native passwords stay on /dev/tty; no
  automatic permission repair or duplicate OpenSSH policy is introduced.
- Distinguish discovery sample/scan limits and summarize obsolete unmanaged rows
  in ordinary output. --all/JSON retain detailed bounded inspection; metadata and
  endpoint/ownership checks are preserved.
- Add shareable doctor --report, optional notebook kernel_report and a stdlib
  diagnostic cell, without mandatory remote JupyHop installation or dependencies.
- Preserve registry schema 1.0 and live runners. Qualification includes actual
  installed upgrades from 0.2.0 source as well as the historical 0.1.0 baseline.
- Retain verified pidfd exit evidence in stop replies when a subsequent process
  observation is unavailable; never apply it to another recorded identity.

Source acceptance passes 394 tests on each supported Python plus installed,
native-password, account-isolation and browser gates; see [30](devguide/30-03-implementation.md).
Build `0.3.0=py_0` is published on uibcdf/main after four installed Conda clients
and independent public receiving passed; see [publication evidence](devguide/31-03-conda-publication.md).
There is no PyPI publication or new physical infrastructure pilot for 0.3.0.

## 0.2.0 — pre-1.0 stabilization

- Support native terminal SSH passwords/passphrases and keys/agent through one
  invocation-owned foreground master per route. Add --batch and a bounded
  --ssh-auth-timeout; RPCs/forwards cannot fall back to a new network connection.
  Python never reads or caches the SSH password.
- Continue bounded runtime discovery after the 64-record diagnostic sample fills;
  retain verified live servers in preference to stale/unsupported diagnostics.
  Existing metadata remains untouched and discovery remains explicitly partial.
- Classify timeouts, execution errors and malformed responses during the
  pre-launch environment check as prerequisite failures before any state/server
  creation; retain the existing timeout and credential redaction.
- Verify installed 0.1.0-to-0.2.0 clients preserve live kernels and immutable
  runners, including simultaneous old/new clients with independent keys/HOMEs.
- Observe two hours of disconnected toy computation on a real Linux target,
  followed by the same kernel/session/PID/memory/progress and verified own cleanup.
- Add native terminal/password, guarded site-fixture and cleanup regressions;
  CI covers Python 3.11–3.14, actual Unix passwords/accounts and browser kernels.
- Add a Linux-constrained Conda recipe and reuse UIBCDF's exact-file build,
  staging upload and promotion actions, with four installed-client gates.
  [Publication evidence](devguide/24-conda-publication.md) records channel status;
  no PyPI publication is included.

Supported operation remains bounded by the [compatibility matrix](docs/compatibility.md).
Physical home-client network moves, forced last logout/reboot, other client OSes
and individually configured MFA variants remain unmeasured. See
[the acceptance evidence](devguide/23-02-stabilization-evidence.md).

## 0.1.0 — prepared, unpublished

First pre-1.0 candidate for Linux and CPython 3.11–3.14. The client uses OpenSSH and
has no mandatory Python dependencies or local Jupyter requirement.

Package versions and release tags use only x.y.z, without a v prefix or release
suffixes. Pre-1.0 development is represented by the 0.y.z series.

- Discover/open supported existing current-user Jupyter servers, directly or via
  ProxyJump, with normal Jupyter login and automatic owned loopback forwards.
- Launch password-authenticated managed servers with existing Python/workdir,
  private tmux persistence, remote registry, verified status and graceful stop.
- Reconnect independent clients to the same surviving server/kernel memory.
- Optional TOML profiles, bounded multi-host inventory and explicit inactive
  archive with name reuse and retained recovery evidence.
- Close owned SSH resources on SIGTERM/SIGHUP during probes as well as open;
  refuse password input when the terminal cannot hide it.
- Reopen atomically replaced records with a bounded retry, avoiding spurious
  unsafe-state failures without relaxing file permissions or ownership checks.
- Require Jupyter Server >=2.20,<3 for managed native ephemeral-port launching;
  refuse older versions before state creation. Existing-server access remains
  separately validated. See the compatibility matrix for tested combinations.

Not supported: arbitrary runtime/process discovery, lifecycle control of unmanaged
servers, cross-user sharing, IPv6-only/HTTPS/Unix sockets, remote reboot memory
restoration, automatic restart, permanent archive deletion, Slurm or other client
platforms. Site last-logout policy can terminate tmux workloads. This is not a
JupyterHub deployment or a centralized access service.

See [the quickstart](docs/quickstart.md), [compatibility](docs/compatibility.md),
[security policy](SECURITY.md) and milestone reports for evidence and limits.
