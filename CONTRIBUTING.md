# Contributing

Read [README.md](README.md) and [devguide](devguide/README.md) first. The devguide
is the source of architectural/functional decisions; update it when evidence
changes a decision. Keep discovered servers separate from managed lifecycle.
Small coherent commits should keep code, tests and docs synchronized.

Maintainer development currently uses small coherent commits pushed directly to
`main`. CI validates each push; this workflow does not require a pull request.

## Development environment

Use CPython 3.11–3.14 on Linux; development currently uses 3.14. A dedicated Conda
environment is suitable:

```console
mamba create -n jupyhop-dev -c conda-forge python=3.14 pip
mamba activate jupyhop-dev
python -m pip install -e '.[dev,experiments]'
```

Unit tests need `ssh-keygen` for private fixture-key preparation; they do not
connect over SSH, run sshd or require tmux. Integration additionally needs the
OpenSSH client/server and tmux. An operator may need to create
`/run/sshd` for local sshd privilege separation. Never modify a shared SSH service
or institutional machines just to run tests.

```console
ruff check .
ruff format --check .
mypy
pytest
pytest --run-integration
python -m build
python -m experiments.release_check
python -m experiments.package_smoke
```

Default pytest runs only unit tests and does not import optional Jupyter packages.
Integration is explicitly enabled and must run as a non-root user. Its generated
keys/sshd instances, loopback ports, HOMEs, state and servers are disposable; it
does not read normal SSH config or target scientific sessions. Real Unix-account
acceptance is a separate operator-authorized fixture: see
[its instructions](experiments/m5_accounts.md). Do not run that privileged script
against an untrusted checkout. It is never part of installed-client operation.

Browser acceptance uses a real Chrome/Chromium with its normal sandbox:

```console
python -m experiments.browser_smoke
python -m experiments.browser_smoke --managed --reconnect
```

No `--no-sandbox` workaround is supported. CI defines the four-version suite and
separate compatibility experiments. Record exact observed versions and failures;
do not turn an unavailable platform/service into a passing compatibility claim.

## Changes and reports

Prefer stdlib and ordinary OpenSSH over extra services or transport abstractions.
Do not add mandatory Python dependencies without evidence. Test meaningful
behavior and failure boundaries; no destructive tests against real workloads.
Commit no real machine addresses, users, credentials or private logs. Use example
aliases/domains and generated temporary identities. New features need truthful
help, README/devguide updates and scenario-ledger mapping when applicable.

The code is MIT licensed; contributions use the same license. For vulnerabilities
see [SECURITY.md](SECURITY.md), for releases see [the release guide](docs/releasing.md).
