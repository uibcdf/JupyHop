# 24 — Conda distribution through UIBCDF infrastructure

This is the historical 0.2.0 publication report. The current 0.3.0 publication is
recorded in [31](31-03-conda-publication.md), reusing the same workflow.

Status: 0.2.0 build py_0 published to uibcdf/main, with source acceptance,
four installed Conda clients and independent public receiving verified.
The maintainer explicitly authorized publishing a usable package to uibcdf for
testing. The selected package version is 0.2.0, without a version suffix.

## Existing mechanisms studied

The neighboring molsysmt, molsysviewer, pyunitwizard, argdigest, depdigest and
smonitor repositories use recipes under devtools/conda-build, build environments
under devtools/conda-envs and the UIBCDF-owned build/upload action. Their current
routes distinguish a staging upload from promotion of the same tested archive.
SMonitor's recent route separates build-only, archive inspection, exact-file
upload and digest-bound promotion. MolSysMT's native multi-platform ABI3 builds
and coupled MolSysViewer qualification are unnecessary for this pure Python tool.

JupyHop reuses
[build/upload/promote v2.3.0](https://github.com/uibcdf/action-build-and-upload-conda-packages/tree/87c70b1443d5f22d738ee3ddf812bdbe0152f6c2)
at its immutable commit, plus the existing
[public-file verifier](https://github.com/uibcdf/molsyssuite/tree/399d33a4ee0da148571cba7cfc004e3f3a2e71e7/.github/actions/verify-public-conda).
It does not copy the upload, registry mutation or promotion implementations, add
runtime suite dependencies, or change another repository.

## Decisions and workflow

- Build one noarch Python archive, py_0 for the first Conda build. The build
  string is separate from package version 0.2.0. No platform conversion or
  repeated interpreter builds are needed.
- Require __linux and Python >=3.11,<3.15 in Conda dependencies. Pure Python does
  not imply tested macOS/Windows operation. OpenSSH is a client dependency;
  Jupyter and tmux remain remote prerequisites only. There are no mandatory
  Python runtime dependencies.
- Read version directly from committed pyproject.toml. Static package metadata
  needs no versioningit, temporary tag, public tag or GitHub Release to build a
  candidate. Conda publication is an explicit workflow dispatch, never an
  ordinary push side effect.
- Require a clean exact main commit, matching workflow SHA/version and all six
  successful source checks at that SHA. Inspect executed tests, actual-wheel
  upgrades, browser, Unix-account/password cases and account cleanup; skipped or
  incomplete evidence cannot authorize publication.
- The shared build action runs its recipe test with upload disabled. The local
  inspector binds source bytes, license, Python metadata, launcher, Linux/runtime
  constraints, archive paths and SHA256 before the shared upload action writes
  only that file to uibcdf/label/staging.
- Four independent installed clients, Python 3.11–3.14 on hosted Linux, resolve
  the exact version/build from staging without local Jupyter. Their installed
  channel record must match the retained archive's digest, and ssh must come
  from the client prefix. Installing a local archive alone bypasses the solver's
  dependency checks; it is not accepted as channel-resolution evidence. The existing
  package smoke now accepts --client-prefix and exercises doctor, profiles/fleet,
  existing open and managed start/open/status/stop/archive through ProxyJump.
  Remote fixtures use a separate interpreter and only disposable loopback state.
  The 3.14 cell also runs the native terminal authentication regressions with
  Conda's OpenSSH on PATH.
- Only after all four installed jobs succeed does the shared promotion action
  add main to the same digest-verified staging file. The independent shared
  verifier checks public labels, downloaded bytes and the solver index. Retain
  source-gate, inspected-archive, upload, producer and promotion/public receipts.
  No overwrite, force upload, rebuild during promotion or implicit newest-build
  selection is used.

Conda's [virtual-package specification](https://conda.org/learn/ceps/cep-0030/)
explicitly supports restricting noarch packages to an OS with __linux. Its
[recipe documentation](https://docs.conda.io/projects/conda-build/en/stable/resources/define-metadata.html)
describes TOML metadata loading and noarch entry points. Future macOS support is
tracked in [issue #2](https://github.com/uibcdf/jupyhop/issues/2); it requires its
own evidence before relaxing this boundary.

## Local observations and files

An isolated temporary mamba build environment produced
jupyhop-0.2.0-py_0.tar.bz2, passed the recipe's import/version/CLI/OpenSSH tests and
the exact-archive inspector. Installing it into a separate clean CPython 3.14
prefix passed the installed-client smoke. A subsequent indexed-channel install
verified dependency resolution, the installed archive digest and the prefix's
OpenSSH executable, then passed the complete ProxyJump/lifecycle smoke again.
No system/scientific environment, personal SSH configuration or remote workload changed.

The indexed test exposed fixture host configuration written as 0664 under a
group-writable umask. Conda's OpenSSH 10.6p2 rejected the included hosts file;
making only the two generated fixture config files explicitly 0600 corrected
that reproducible refusal. Host trust and product SSH permission checks are not
relaxed. A cross-platform indexed dry-run with macOS virtual prerequisites
refuses JupyHop specifically because __linux is absent; this is a solver-boundary
check, not a macOS runtime test.

The 16 new publication guards pass with all 241 unit tests, lint/format and strict
types. The enlarged source suite passes all 310 cases on local CPython 3.14,
including 69 loopback integrations. All ten native terminal regressions also pass
with Conda's OpenSSH on PATH.
A public read before upload returned HTTP 404 for uibcdf/jupyhop; no existing
package or coordinate is assumed safe to overwrite.

Publication guard unit tests reject wrong commits, dirty source, incomplete or
skipped gates, altered source, unsafe archive paths/aliases/symlinks, native
binaries, missing platform constraints/dependencies and a missing CLI launcher.
The earlier [0.2.0 source run](https://github.com/uibcdf/jupyhop/actions/runs/42557863957)
passed all six jobs; the Conda candidate must obtain its own exact-commit run.

Main files: [recipe](../devtools/conda-build/meta.yaml),
[build script](../devtools/conda-build/build.sh),
[build environment](../devtools/conda-envs/build_env.yaml),
[publication workflow](../.github/workflows/build_and_upload_conda_packages.yaml),
[source/archive checks](../experiments/conda_release.py),
[guard tests](../tests/test_conda_release.py),
[shared installed smoke](../experiments/package_smoke.py) and source-manifest/
artifact-inspector updates. User installation and operator instructions are in
the quickstart and release guide.

## Hosted qualification and publication

The immutable candidate is 53737f87ca2658ecceef1992329137d3be7ba3be.
Its [source acceptance](https://github.com/uibcdf/jupyhop/actions/runs/42560580553)
passes all six jobs: 310 tests on each Python 3.11–3.14, actual installed-wheel
upgrades, clean clients, server comparisons, Chrome and native SSH passwords/
actual-account cleanup. The downloaded CI wheel/sdist and ZIP/checksums were
independently checked against that commit, including the complete source/docs
and UTF-8 README.

The [Conda publication run](https://github.com/uibcdf/jupyhop/actions/runs/42560992989)
also passes all six jobs. The single inspected file uploaded to staging has
SHA256 `061225745df3da02efd03981feb234b9bb919f73cd05de7040432ab65fc119e4`.
All four clients resolve that exact version/build from staging, verify their
installed record digest and Conda OpenSSH, and pass the full installed-client
smoke. The Python 3.14 cell additionally passes all ten terminal regressions.
Promotion preserves the same file and staging label while adding main; both the
promotion receipt and independent public download/solver-index verifier report
verified status.

A separate local install resolves jupyhop=0.2.0=py_0 from uibcdf/main with a
new prefix and fresh package cache. The actual downloaded archive, installed
record, version, import origin and Conda OpenSSH match. This CPython 3.14.10 client
has no local Jupyter and passes doctor, profiles/fleet, existing open and managed
start/open/status/stop/archive through a disposable ProxyJump route. Fixtures and
owned connections were cleaned after acceptance.

This report retains the candidate, run IDs, exact archive/digest and independent
receiving result. Original bounded upload/producer/promotion/public receipts
accompany the workflow artifacts. The separately downloaded source-CI artifacts
at the candidate commit have these hashes:

| Artifact | SHA256 |
| --- | --- |
| jupyhop-0.2.0-py3-none-any.whl | ca1c90072aeb6421eca4344da8ff6118ba3fd935e5672a58d434821bfe68cb13 |
| jupyhop-0.2.0.tar.gz | e6d909f85e6a416dbc1a90f0869610a24b35c3f0525d293555519ea01566db65 |

Later documentation-only commits do not rebuild or replace the published bytes.

## Limits and next step

The scoped source, artifact, installed-client, main-label/public-index and
independent receiving gates passed. Future candidates require their own exact
source/installed acceptance. Missing credentials or registry errors must remain
failures. Keep real credentials in
the existing ANACONDA_UIBCDF_TOKEN secret, never in source, commands or chat.

Linux and the previously documented endpoint/authentication/persistence limits
remain in force. Staging publication is not main visibility. A later documentation
closeout commit does not replace a qualified archive or move its source identity.
Further stabilization uses actual users; optional M7 work is unchanged.
