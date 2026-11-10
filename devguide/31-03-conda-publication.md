# 31 — 0.3.0 Conda publication

Status: **0.3.0=py_0 published to uibcdf/main on 2026-11-10**, with all source,
installed-client, promotion/public-index and independent receiving gates passed.
The maintainer explicitly authorized this publication after reviewing the
[source implementation](30-03-implementation.md). Versions remain numeric x.y.z.

## Qualified source and exact package

| Item | Observed identity |
| --- | --- |
| Source/workflow commit | 9a50bef3d5144420ccb0c5776d1158b4e1a76613 |
| Source acceptance | [42787957563](https://github.com/uibcdf/jupyhop/actions/runs/42787957563), all six jobs successful |
| Source documentation build/deployment | [42787957660](https://github.com/uibcdf/jupyhop/actions/runs/42787957660), both jobs successful |
| Conda publication | [42835266565](https://github.com/uibcdf/jupyhop/actions/runs/42835266565), all six jobs successful |
| Public file | uibcdf/jupyhop/0.3.0/noarch/jupyhop-0.3.0-py_0.tar.bz2 |
| Conda archive SHA256 | 015425e8b5a4fdeeb851d6d0a744fde97fb5c369d70c486ac43c8f389a537449 |
| Public labels | staging and main, on the same file |

Before dispatch, the local source was clean and equal to origin/main. The public
release API returned 404 for 0.3.0 and 200 for the existing 0.2.0 release. The
exact-source publication guard passed independently and again inside the workflow.
No occupied coordinate was overwritten and no force upload was used.

Source acceptance observed 394 tests per CPython 3.11–3.14, both server-compatibility
jobs, actual installed-wheel upgrades from 0.1.0 and published 0.2.0 source,
browser/kernel reconnection, real Unix account isolation and native passwords.
This is the final documentation-closeout source commit, distinct from the earlier
8bca6ab implementation anchor recorded in report 30.

## Reused publication mechanism and decisions

The existing [workflow](../.github/workflows/build_and_upload_conda_packages.yaml)
reuses UIBCDF build/upload/promote v2.3.0 at
87c70b1443d5f22d738ee3ddf812bdbe0152f6c2 and the public verifier at
399d33a4ee0da148571cba7cfc004e3f3a2e71e7. The
[0.2.0 distribution report](24-conda-publication.md) explains that architecture.
No publication code, dependency, recipe or client functionality changed for this release.

One noarch archive is built once, tested, inspected against the committed Python
source/license and uploaded to staging. Four independent installed clients resolve
that exact version/build from the staged channel, verify their installed SHA256
and use OpenSSH from their Conda prefix. Only after those jobs pass is main added
to the same digest-verified file. The public verifier checks labels, downloaded
bytes and the solver index; promotion does not rebuild the package.

The package requires Linux, Python >=3.11,<3.15 and OpenSSH. It has no mandatory
Python dependencies or local Jupyter/tmux requirement. Remote Jupyter environments
and managed runners are not installed or migrated by client publication.
No GitHub Release, version tag or PyPI upload was created.

## Experiments and observed acceptance

| Gate | Result |
| --- | --- |
| Recipe import/version/CLI/OpenSSH tests | Passed before upload |
| Exact archive inspector | Passed in CI and independently on the downloaded retained Conda archive |
| Installed Conda clients, Python 3.11–3.14 | All four resolved the same staged digest and passed the installed smoke without local Jupyter |
| Installed smoke coverage | Doctor/support report, profiles/fleet, existing access, named open, managed start/status/stop/archive, history/counters and explicit compound completion through ProxyJump |
| Native Conda OpenSSH terminal authentication | All ten regressions passed in the 3.14 job |
| Promotion and independent public verifier | Both receipts report verified; main and staging refer to the inspected file |
| Separate public receiving | Fresh temporary mamba prefix/cache resolved 0.3.0=py_0 from uibcdf/main; downloaded archive, installed record, version and import origin matched |
| Separate installed smoke | Passed with the public client and its Conda OpenSSH, disposable loopback SSH/Jupyter fixtures and owned cleanup |

The separate public receiving client ran CPython 3.14.10 and OpenSSH 10.6p2. It
had no jupyter_server installed. Its --help included resume/manage and --version
reported jupyhop 0.3.0. The cached downloaded archive was hashed independently;
the installed channel record alone was not treated as byte verification.
No personal SSH configuration, scientific environment/session or institutional
server was used for this verification.

Original receipts and the exact Conda archive are retained in the workflow:

- [Candidate/build evidence](https://github.com/uibcdf/jupyhop/actions/runs/42835266565/artifacts/13773776436): source-gates.json, archive.json, upload receipt, producer events and the Conda file. ZIP SHA256: ef5419475ee51e8162fcc8808fa0ae8cc7b63d9a1d2943105786e38816d56928.
- [Promotion/public evidence](https://github.com/uibcdf/jupyhop/actions/runs/42835266565/artifacts/13773211899): promotion receipt and public verification. ZIP SHA256: 493ed09811573aae5e6f45ee96df387486e55deee34485bad228975796c9afc7.

Both ZIP digests were verified after independent download. Local receiving
receipts, logs and the inspected archive are retained outside the repository.
The temporary receiving environment and its isolated package cache were removed.
Public guides, README, changelog, security policy and roadmap now identify 0.3.0
and give matching installation/update commands. These documentation-only closeout
changes do not replace the published archive or its source identity.

## Limits and next step

The [compatibility boundary](../docs/compatibility.md) remains Linux and the tested
server/authentication/persistence matrix. No additional platform, forced logout,
network interruption, reboot or 0.3.0 physical-site pilot was tested here. Existing
server discovery remains partial; unmanaged servers remain open-only. Report 30
retains the bounded history and terminal lifetime limitations.

Install/update the local client to 0.3.0 as described in
[upgrading](../docs/upgrading.md), then repeat the guided physical-client
usability pilot. No JupyHop reinstall in the remote scientific environment is
required for ordinary operation. Further package candidates need their own exact
source/installed acceptance and an unoccupied version/build coordinate.
