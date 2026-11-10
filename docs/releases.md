# Release notes

## 0.3.0 — Session usability candidate

Source implementation is in qualification; the Conda channel remains at 0.2.0
until the new artifact's separate promotion. The
[implementation evidence](https://github.com/uibcdf/jupyhop/blob/main/devguide/30-03-implementation.md)
tracks remaining gates without labeling proposed/publication work as complete.

- Named managed selection with --name; consistent terminal choosers even for one
  ready server; resume is an alias for open.
- A thin manage menu and managed/history counters. Bounded history stays visibly
  partial; unknown counters are not zero.
- Interactive stop confirms stop and archive together, preserving evidence and
  releasing names. --keep-record retains a stopped record. Existing UUID --yes
  scripts stay stop-only unless --archive explicitly authorizes both phases.
- Actionable SSH permission/ownership/timeout feedback, bounded captured stderr,
  native private password prompts and no automatic configuration repair.
- Distinct sample/scan diagnostics and human aggregation of obsolete unmanaged
  rows, with --all/JSON inspection and unchanged metadata safety checks.
- Shareable doctor --report and optional notebook kernel_report, with a stdlib
  diagnostic cell that requires no remote JupyHop installation.
- Registry schema remains 1.0; runners/scientific environments are not migrated.
  The installed-candidate gate includes published 0.2.0 source as a baseline as
  well as historical 0.1.0.

## 0.2.0 — Linux stabilization

Version 0.2.0 is available from [uibcdf on Conda](https://anaconda.org/uibcdf/jupyhop).
It supports CPython clients 3.11–3.14 and the Linux/server boundary in
[Compatibility](compatibility.md).

- Native terminal SSH passwords/passphrases and keys/agent, directly or through
  ProxyJump, with invocation-owned connections and safe cancellation.
- Existing-server discovery/open and managed start/status/reconnection/stop/
  archive, with profiles and multi-host inventory.
- Bounded discovery retains verified live endpoints when stale diagnostics fill
  its sample; original runtime metadata stays untouched.
- Installed 0.1.0-to-0.2.0 upgrade retains a live kernel and immutable runner.
- A two-hour real-site disconnected synthetic workload recovered the same kernel,
  memory and progress, followed by verified own cleanup.
- One Linux-constrained Conda archive qualified through four installed clients
  and promoted from staging to main without rebuilding the file.

The [publication record](https://github.com/uibcdf/jupyhop/blob/main/devguide/24-conda-publication.md)
identifies the exact Conda file/digest and observed tests. Documentation published
after that candidate does not replace those qualified package bytes. There is no
PyPI publication of 0.2.0.

Physical client/network transitions and forced last logout/reboot remain
unmeasured. Future macOS support is tracked in [issue #2](https://github.com/uibcdf/jupyhop/issues/2).
Slurm, additional persistence backends, cross-user sharing and kernel-memory
restoration after process loss are outside the implemented scope.

The full source history is in [CHANGELOG](https://github.com/uibcdf/jupyhop/blob/main/CHANGELOG.md).
Package versions and release tags use numeric `x.y.z` identifiers without
prefixes or suffixes; Conda's build number is a separate field.
