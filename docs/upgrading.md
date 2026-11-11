---
myst:
  html_meta:
    description: "Update a local JupyHop Conda client and reconnect to existing remote sessions without reinstalling scientific environments or rewriting living launchers."
    "property=og:description": "Update a local JupyHop Conda client and reconnect to existing remote sessions without reinstalling scientific environments or rewriting living launchers."
---

# Update the client

The current public Conda release is **0.4.0**. Run these steps on each local
client you want to update. Remote Jupyter environments, existing notebook files
and managed runners have separate lifetimes and do not need reinstalling for a
client update.

## Before changing the local environment

Save notebook files and note the SSH alias, managed name or UUID and any custom
runtime paths. For a password-based session, keep its Jupyter password available
through your private credential workflow. Close an attached JupyHop tunnel with Ctrl-C before changing
its local environment, then update from a separate terminal. The remote server
and kernel remain subject to their launcher and site policy.

Check the [release notes](releases.md) and [compatibility policy](compatibility.md).
Installed upgrades from 0.1.0, 0.2.0 and 0.3.0 to the actual 0.4.0 client are tested with
the same surviving kernel and unchanged remote runner/registry. This does not
promise arbitrary future schema migrations, downgrades or survival after a remote
process exits.

## Install the chosen Conda release

For an existing client environment named `jupyhop`:

```console
mamba activate jupyhop
mamba install -c uibcdf -c conda-forge jupyhop=0.4.0
jupyhop --version
```

Review the proposed environment transaction. If you prefer to keep the previous
client environment available, create a separate one following
[Installation](installation.md). Both clients can reach the same live remote
managed session when their protocol/state contracts are compatible.

For source or wheel installations, install the reviewed replacement into the
chosen client environment using the same method described in
[Installation](installation.md#source-or-reviewed-wheel). There is no public
PyPI release or mandatory remote JupyHop package to update.

## Verify by reconnecting

From the updated local client:

```console
jupyhop status workstation
jupyhop resume workstation --name analysis
```

Replace `analysis` with your current managed name; an exact session UUID works
too. Complete any required login and return to the existing notebook/kernel. Use
`discover`/`open` with the required runtime paths for an unmanaged server.
Reconnection makes a new local forward; it does not recreate kernel memory.

If the client reports incompatible state/protocol, preserve private records and
check the supported versions. Do not edit schema numbers, delete the registry or
start a replacement server as a migration step. Report the redacted version/error
details using [Troubleshooting](troubleshooting.md#reporting-a-problem).

## Interaction changes in 0.4.0

New managed sessions open automatically after SSH authentication. Return by name
with `jupyhop resume HOST --name NAME`. A session created by 0.3.0 still uses its
existing Jupyter password. Add `--auth password` to choose password authentication
for a new session, and `--verbose` to see full identifiers and observations.

Ordinary JSON keeps manual login and its existing fields. Scripts using
`--password-stdin` still create password-based sessions. See
[Scripting](scripting.md) for the browser options and new access failure code.

## Interaction changes in 0.3.0

Open without a selector always offers a terminal chooser, even for one candidate.
An exact UUID or managed --name selects directly. Native headless/JSON ambiguity
behavior and stop-only UUID --yes scripts remain compatible. Interactive stop now
explains and offers archival in the same confirmation; --keep-record preserves
the stopped entry. Use status --history for versioned inventory JSON/history;
status --json alone retains its earlier shape and reconciliation semantics.
Archive preserves evidence and notebooks; it cannot recover a dead kernel.
