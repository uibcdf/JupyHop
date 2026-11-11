# 38 — 0.4.0 Conda publication

Status: **publication authorized and being prepared**. Version and build target
are **0.4.0=py_0** on the uibcdf Linux-only noarch channel. Publication completion
requires observed promotion and independent public installation.

## Maintainer decision

After the [guided physical pilot](37-04-physical-client-pilot.md), the maintainer
explicitly chose to publish with the current validation and collect new-user
feedback afterwards. This accepts the automated qualification and guided pilot
for the 0.4.0 release. A23's unassisted new-reader walkthrough is deferred.
The decision does not claim that walkthrough occurred. The
[manage presentation issue](https://github.com/uibcdf/jupyhop/issues/6) remains
scheduled for the next version.

## Preparation

- Current client/package version is the numeric 0.4.0.
- The preflight API request found no existing 0.4.0 release at the requested
  coordinate. The workflow must still reject an occupied or different artifact.
- The configured publication credential is available through the organization.
  Credential values are consumed only by the pinned publication actions.
- The source gate now requires successful installed 0.3.0 compatibility on all
  four Python jobs and automatic Chrome/Firefox access on Python 3.14, in
  addition to the existing source/upgrade/account/SSH checks.
- The workflow builds and stages one inspected file, tests that digest with
  four installed clients, promotes it to main and verifies public visibility.
  An independent download/install is required before this report is complete.

The [local qualification artifacts](36-04-implementation.md) provide prior
development evidence. Release receipts will identify the exact workflow-built
archive and source revision. See [the release procedure](../docs/releasing.md).

## Release evidence

- [ ] Exact publication source and all required source jobs accepted.
- [ ] One archive built, inspected and uploaded to staging.
- [ ] Four installed Conda clients verified against that archive digest.
- [ ] The same file promoted and visible on uibcdf/main.
- [ ] Public archive independently received, inspected and installed.
- [ ] Public installation guides and release notes updated to observed status.
