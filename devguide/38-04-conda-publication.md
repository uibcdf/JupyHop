# 38 — 0.4.0 Conda publication

Status: **0.4.0=py_0 published to uibcdf/main on 2026-11-11**, with source,
installed-client, promotion and independent receiving acceptance observed.

## Maintainer decision

After the [guided physical pilot](37-04-physical-client-pilot.md), the maintainer
explicitly chose to publish with the current validation and collect new-user
feedback afterwards. This accepts the automated qualification and guided pilot
for 0.4.0. A23's unassisted new-reader walkthrough is deferred. The decision
does not claim that walkthrough occurred. The
[manage presentation issue](https://github.com/uibcdf/jupyhop/issues/6) is
scheduled for the following version.

## Qualified source and exact package

| Item | Observed identity |
| --- | --- |
| Source/workflow commit | 1b474e5f454a91b66c2b927979040285e9c7422a |
| Source acceptance | [42965569840](https://github.com/uibcdf/jupyhop/actions/runs/42965569840), all six jobs successful |
| Source documentation build/deployment | [42965569724](https://github.com/uibcdf/jupyhop/actions/runs/42965569724), successful |
| Conda publication | [42966240728](https://github.com/uibcdf/jupyhop/actions/runs/42966240728), all six jobs successful |
| Public file | uibcdf/jupyhop/0.4.0/noarch/jupyhop-0.4.0-py_0.tar.bz2 |
| Conda archive SHA256 | abe4bd6df7f59c3dd02921cb2591ba63b169a8bb63446545564bde16eeb52048 |
| Labels | main and staging on the same file |

Preflight found the 0.4.0 coordinate available and the source checkout clean.
The configured publication credential was available through the organization.
The strengthened source checker passed locally and in the workflow. It requires
installed 0.3.0 compatibility in both directions on all four Python jobs and
automatic Chrome/Firefox access on Python 3.14, alongside the existing
source/upgrade/account/SSH checks. Regression tests cover omitted acceptance steps.

The [implementation report](36-04-implementation.md) retains the earlier local
qualification archives and their digests. The file identified here is the
workflow-built public release.

## Publication mechanism

The existing [workflow](../.github/workflows/build_and_upload_conda_packages.yaml)
uses UIBCDF build/upload/promote v2.3.0 at
87c70b1443d5f22d738ee3ddf812bdbe0152f6c2 and the public verifier at
399d33a4ee0da148571cba7cfc004e3f3a2e71e7. It built and inspected one archive,
uploaded it to staging, qualified four installed clients and promoted that
digest to main. The public verifier confirmed labels, download bytes and solver
index visibility.

The package requires Linux, Python >=3.11,<3.15 and OpenSSH. The client has zero
mandatory Python dependencies. Scientific environments and immutable managed
runners keep their separate lifetimes. Package versions use numeric x.y.z.
This publication used the Conda route.

## Experiments and observed acceptance

| Gate | Result |
| --- | --- |
| Source qualification | All four Python jobs and both server comparisons passed, including installed upgrades and browser/account/native-password acceptance |
| Recipe and archive checks | Import/version/CLI/OpenSSH tests and source/license/metadata inspection passed |
| Installed Conda clients | Python 3.11, 3.12, 3.13 and 3.14 each resolved the staged digest and passed the installed smoke |
| Installed OpenSSH | Each client bound OpenSSH to its Conda prefix. The 3.14 job passed native terminal-authentication acceptance |
| Promotion | Receipt verified the same SHA256 moving from staging to main |
| Public verifier | Receipt verified main visibility, downloaded bytes and solver index |
| Independent receiving | A fresh temporary mamba client resolved 0.4.0=py_0 from uibcdf/main. Installed metadata and the independently downloaded and cached archive hashes matched |
| Independent source inspection | The public archive and installed Python files matched the qualified source and MIT metadata |
| Independent installed smoke | Passed doctor/support report, profiles/fleet, named open, managed/history inventory, compound completion, existing access and lifecycle through disposable ProxyJump fixtures |
| Independent automatic access | The actual public Conda client and its OpenSSH completed named resume, the private no-browser handoff and an authenticated API request through a disposable ProxyJump route |

The separate receiving client ran Python 3.14.10 and OpenSSH 10.6p2 with
OpenSSL 3.6.5. It had no local jupyter_server. Import/version checks, the
installed channel URL, prefix ownership and the actual Conda OpenSSH path were
verified. A separately fetched public archive was inspected against the source.
The extra automatic-access check used a test actor to redeem the protected
file proof. The Chrome/Firefox acceptance is recorded in the source jobs.
The receiving tests used generated loopback fixtures.

## Retained evidence

- [Candidate/build artifact](https://github.com/uibcdf/jupyhop/actions/runs/42966240728/artifacts/13830953014) contains the Conda file, source gate, archive inspection and producer/upload evidence. ZIP SHA256 is `469a1da553def0ad4d56d88de960e2a6229b9c8f394f9f61f77c35080fb32892`.
- [Promotion/public artifact](https://github.com/uibcdf/jupyhop/actions/runs/42966240728/artifacts/13830964583) contains the verified promotion and public-index receipts. ZIP SHA256 is `8be5b2a15f1b78224bae5429dd75693d4e5981872c00620f93b4512d08dca593`.

Both ZIP digests were verified after download. Independent receiving receipts,
logs and the public archive were retained outside the repository. Public
installation/update commands and release notes now select 0.4.0. Documentation
closeout commits preserve the released archive's source identity above.

## Acceptance and follow-up

- [x] Exact source and required acceptance jobs observed.
- [x] One archive built, inspected and uploaded to staging.
- [x] Four installed clients verified against that digest.
- [x] Same file promoted and visible on uibcdf/main.
- [x] Public archive independently downloaded, inspected and installed.
- [x] Installation guides and release notes updated to observed package status.

G6 is complete. Gather new-user feedback and improve manage's presentation under
issue #6 in the next version. The tested Linux/server/browser boundaries and
site persistence limits remain documented in [Compatibility](../docs/compatibility.md).
