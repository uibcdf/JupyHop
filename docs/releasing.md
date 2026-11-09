# Preparing a release

The current Conda release is 0.2.0. This repository has not published it to PyPI.
Builds, CI artifacts, commits and tags do not constitute a package publication.
Uploading a release is a separate explicit maintainer action after artifact review.

Package versions and release tags use exactly `x.y.z`, for example `0.1.0`,
`0.1.1` or `0.2.0`. Tags use the same number, without a `v` prefix. Do not use
prerelease, development, postrelease or local suffixes. The `0.y.z` series
represents development before 1.0; numeric naming does not promise 1.x API stability.
The artifact inspector enforces this format. No tag is created by building or
checking a package, and wire/registry versions keep their independent contracts.

1. Review the roadmap gates, security findings, scenario ledger, supported matrix
   and known limits. Check help/quickstart against actual commands. Observe CI;
   local checks cannot claim that a remote GitHub workflow passed.
2. Update `pyproject.toml`, `src/jupyhop/__init__.py` and CHANGELOG together. Wire
   minors, local inventory/config versions and remote registry schema have their
   own contracts; a client version bump does not migrate or replace live runners.
3. Run lint/type checks, the full four-Python suite, compatibility, legacy-runner,
   browser and clean-wheel experiments described in CONTRIBUTING and the M6 report.
   Record exact versions; preserve separate real-account evidence from M5.
   The 0.2.0 stabilization also requires native terminal/Unix-password acceptance
   and the actual installed-wheel upgrade from the trusted 0.1.0 baseline. See
   [the experiment instructions](https://github.com/uibcdf/jupyhop/blob/main/experiments/stabilization.md).
4. Build in a clean checkout/environment with only the chosen release artifacts
   in `dist`, then run:

   ```console
   python -m build
   python -m experiments.release_check
   python -m experiments.package_smoke
   ```

   The artifact check verifies matching version/entrypoint, MIT licensing,
   classifiers, no mandatory dependencies, safe archive paths, source inclusion
   and wheel boundaries. It prints SHA256 hashes for the reviewed wheel/sdist
   and writes `dist/SHA256SUMS`, included with downloadable CI artifacts.
   Clean-wheel acceptance runs outside the checkout in a new venv without Jupyter.
5. Review the exact wheel/sdist and their hashes, release notes, uncommitted state
   and CI evidence. Only then authorize any tag, GitHub release or PyPI upload.
   Do not publish automatically from ordinary push/pull-request CI.

The standard workflow builds/tests/uploads downloadable CI artifacts but holds
no publishing credentials. Keep signing/tokens outside this repository and
follow the chosen registry's current secure publishing procedure when a release
is explicitly approved.

## Conda packages on uibcdf

The maintainer authorized publishing the tested 0.2.0 candidate to uibcdf.
The [Conda report](https://github.com/uibcdf/jupyhop/blob/main/devguide/24-conda-publication.md) records the reused UIBCDF
actions, Linux-only noarch decision and observed publication status. This route
does not publish PyPI, create a tag or create a GitHub Release.

The coordinate `0.2.0=py_0` is already published. For a future reviewed,
unoccupied coordinate, wait for the exact main commit's six source jobs to pass,
then substitute the approved commit, numeric version and integer build number
in this template:

```console
gh workflow run build_and_upload_conda_packages.yaml --ref main --field candidate_sha=FULL_COMMIT_SHA --field version=X.Y.Z --field build_number=BUILD_NUMBER
```

Use the configured ANACONDA_UIBCDF_TOKEN repository/organization secret. The
workflow builds/tests, inspects and stages one file, qualifies four clean installed
Python clients, then promotes those same bytes to main and verifies visibility.
Download and retain its receipts; independently install the exact public build
before marking publication complete.

For a failed downstream job, inspect its receipt and rerun only failed jobs to
retain the already staged file. Do not blindly rebuild/re-upload an occupied
coordinate. A defective artifact needs a reviewed new candidate and higher Conda
build number; source versions remain plain x.y.z. Never move a source tag or use
force upload. A manual credential/API fix cannot be treated as a passing run.
