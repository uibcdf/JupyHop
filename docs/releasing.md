# Preparing a release

The current candidate is 0.1.0b1. This repository has not published it to PyPI.
Builds, CI artifacts, commits and tags do not constitute a package publication.
Uploading a release is a separate explicit maintainer action after artifact review.

1. Review the roadmap gates, security findings, scenario ledger, supported matrix
   and known limits. Check help/quickstart against actual commands. Observe CI;
   local checks cannot claim that a remote GitHub workflow passed.
2. Update `pyproject.toml`, `src/jupyhop/__init__.py` and CHANGELOG together. Wire
   minors, local inventory/config versions and remote registry schema have their
   own contracts; a client version bump does not migrate or replace live runners.
3. Run lint/type checks, the full four-Python suite, compatibility, legacy-runner,
   browser and clean-wheel experiments described in CONTRIBUTING and the M6 report.
   Record exact versions; preserve separate real-account evidence from M5.
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
