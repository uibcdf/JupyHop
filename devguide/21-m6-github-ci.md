# 21 — M6 follow-up: GitHub CI and beta review

Date: 2026-11-08. **Direct-push CI validation passed.** This follows
[the local beta report](20-m6-beta-readiness.md); the current 0.1.0 candidate remains unpublished.
M7 has not started.

## Work performed

Transferred the existing implementation history to GitHub and exercised the
actual workflow on hosted Ubuntu runners. The operator selected direct commits/
pushes to main as the maintainer workflow; the initial draft PR was closed.
No merge gate, release tag, GitHub release or PyPI upload was introduced.

Local wheel/sdist inspection and checksum verification still pass. All 212 new
history blobs were checked before transfer for concrete development paths, the
actual temporary-account identity and private-key blocks. Commits preserve their
original history. No scientific host/session was used as a test fixture.

## Experiment and correction

The [initial run](https://github.com/uibcdf/jupyhop/actions/runs/42537372442), on
the locally accepted candidate, passed both Server 2.17/2.20 compatibility jobs.
Python 3.12 then failed the cross-client computation test: notebook/kernel/server
IDs were unchanged and the marker was 42, but progress was still empty. The
second client reached the kernel before the synthetic one-second computation
had finished. The original matrix fail-fast policy cancelled the other Python
jobs, so they cannot be counted as passing that run.

The fixture now starts a background thread which announces readiness, then waits
for a kernel event. Only after the first worker process and all its connections
exit does the independent second client release that event, wait for completion
and assert the original marker/progress. This establishes actual continuation
after disconnect and avoids an assumption about connection speed. The thread has
a bounded wait and is owned by the disposable kernel. No production client or
remote-runner code changes.

CI matrices now keep other versions running after a failure, with 20-minute
Linux/15-minute compatibility job bounds. Workflow concurrency cancels superseded
runs for the same Git ref. Full refs keep a fork PR's branch name separate from
main, so it cannot cancel main's validation. The operator's direct-push workflow
uses main's push event; optional PR validation has its own ref.

## Validation and acceptance

The targeted local cross-client test passed (7.87 s), retaining exact session/
kernel/PID and graceful-stop assertions. Ruff lint and format checks pass.
The [corrected main run](https://github.com/uibcdf/jupyhop/actions/runs/42537772370)
tests commit `65f20b1`.

| Job | Result |
| --- | --- |
| Linux / Python 3.11.18 | 266 passed (117.54 s); wheel/build checks passed |
| Linux / Python 3.12.16 | 266 passed (83.01 s); wheel/build checks passed |
| Linux / Python 3.13.18 | 266 passed (130.93 s); wheel/build checks passed |
| Linux / Python 3.14.10 | 266 passed (85.58 s); wheel/build checks passed |
| Chrome existing-open and managed reconnect | Passed; same live kernel memory, token-free navigation history |
| Actual two-account isolation and fixture cleanup | Passed; own stop/archive and privileged cleanup confirmed in job logs |
| Server 2.17: existing-open/kernel, managed refusal before write | Passed |
| Server 2.20: existing-open/kernel and managed lifecycle | Passed |

All six jobs and the overall workflow completed successfully. Source is checked
out on an Ubuntu 26.04.1 GitHub-hosted runner. Remote build, clean-wheel smoke,
artifact checksums, Chrome and account-fixture cleanup are observed results,
not inferred from the earlier local run. Cancelled jobs in the initial run remain
cancelled evidence rather than retrospectively passing results.

A [subsequent main run](https://github.com/uibcdf/jupyhop/actions/runs/42538335604)
on documentation/ref-concurrency commit `114b6f9` passed all application tests and
Chrome checks but timed out after 30 seconds in the runner's native useradd during
fixture provisioning. The fixture rollback and always-cleanup step succeeded.
The backend cause was not established. The affected job was rerun on a fresh
runner at the same commit, without increasing the timeout or skipping account
acceptance; the successful first main run remains separate observed evidence.
Attempt 2 completed successfully, including account creation, isolation and
cleanup. The same commit therefore passes all six jobs without a fixture change.

## Historical CI artifact inspection

Downloaded [the CI artifact](https://github.com/uibcdf/jupyhop/actions/runs/42537772370/artifacts/13640022697)
using the connected GitHub tool. Its ZIP SHA256 matches the Actions API digest:
`d1dc6119ebe262c064e5cec4d4fe143a7ec37c7f04d106be03c4c9adf087c7e8`.
The internal SHA256SUMS verifies both distributions:

| File built from commit 65f20b1 | SHA256 |
| --- | --- |
| Earlier unpublished wheel | a3c1fed79b68986134bc02306a51d326f4fb5e96578ef2a7ebe553cf1f3df5b6 |
| Earlier unpublished source archive | 724f3501f6fce4368397a931d99b45f2afefa590f891d06163548628ef0e5a5e |

Nested archive paths/types are safe, wheel metadata preserves MIT and zero
mandatory dependencies, all installed Python module bytes matched the then-current local
client, and 85 tracked source files match the exact tested Git commit. ZIP/build
metadata can yield different whole-file hashes between local and CI builds;
byte-for-byte reproducible builds are not claimed. These hashes identify this
observed CI build, not later documentation-only rebuilds.

## Numeric release policy (D41)

The maintainer selected plain x.y.z package versions and tags, without prefixes
or suffixes. The current candidate is 0.1.0; 0.y.z represents development before
1.0. Package metadata, CLI version, current user documentation and generated
artifacts follow this policy. The artifact inspector rejects other identifier
formats. No tag or registry publication is implied by this naming change.

The historical checksums above identify the earlier unpublished CI candidate;
they are retained as observed evidence, not relabeled as 0.1.0 artifacts. New
0.1.0 distributions receive their own SHA256SUMS. Only the package identifier
changes; existing runtime behavior and wire/registry compatibility stay the same.
Local validation for 0.1.0 passes: 210 unit tests, lint/format/types, version-format
refusal checks, wheel/sdist inspection and clean-wheel SSH lifecycle acceptance.
The editable CLI and installed metadata both report 0.1.0.

## Isolated account homes (D42)

The provisioning timeout recurred on a later numeric-version run. A temporary
two-runner diagnostic recorded native defaults and measured `/etc/skel` at
833208 KiB (about 814 MiB). The fixture had used `useradd --create-home`, which
copies that system skeleton into each new home; see the
[official useradd manual](https://manpages.ubuntu.com/manpages/resolute/man8/useradd.8.html).
The failure also occurred in a fresh diagnostic runner without the browser, so
it was not necessary to change the browser or production transport.

The fixture now calls `useradd --no-create-home` with an explicit generated home
path, then creates an empty mode-0700 directory owned by the verified new UID/GID.
It refuses existing home paths before account creation and never copies host
profiles/caches. Existing directories/symlinks are never reused. Four additional
unprivileged cases verify empty ownership/permissions, existing-path preservation
and refusal before native account commands. The full suite is now 270 cases:
214 unit and 56 integration. Native command deadlines remain 30 seconds.

The [corrected acceptance run](https://github.com/uibcdf/jupyhop/actions/runs/42541145668)
on `1f2fa73` passes all six jobs, including four Python suites, clean-wheel/build,
Chrome and actual UID isolation/cleanup. Preparing both users and the private
sshd took about 0.45 seconds, compared with an earlier 28-second successful
preparation and the repeated 30-second useradd failures. This supports the
skeleton-copy diagnosis without relaxing or skipping a gate.

Temporary tracing was removed after diagnosis. Whole-provision strace also
follows the long-lived fixture sshd; those exploratory jobs are diagnostic
evidence, not passing acceptance runs. No tracing dependency is added to the
client or the standard workflow.

## Decisions, files and limits

The correction strengthens the original independent-client acceptance instead of
relaxing it or extending a sleep. Direct push to main with coherent commits and
CI is the selected maintainer workflow. No production transport, authentication,
state schema, wire protocol, minimum server version, license or dependencies change.

Changed files: experiments/m4_reconnect.py, .github/workflows/checks.yml,
CONTRIBUTING.md and current devguide evidence/index/roadmap. The installed beta's
client code and wheel remain unchanged; its source artifact is regenerated to
include corrected fixtures, workflow and documentation.

Physical reboot/site logout policy, real WAN/suspend/endurance, additional client
platforms and an independent external security audit remain outside the observed
matrix. Beta publication is still a separate maintainer action after reviewing
the candidate/CI evidence; no institutional guarantees or M7 features are added.

## Next step

The main workflow and its artifact review pass. Review the unpublished beta for
an optional authorized workstation pilot or a separately requested release.
No PR approval is needed for the selected direct-push maintainer workflow.
