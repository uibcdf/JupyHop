# Update the client

The current public Conda release is **0.2.0**. Run these steps on each local
client you want to update. Remote Jupyter environments, existing notebook files
and managed runners have separate lifetimes and do not need reinstalling for a
client update.

## Before changing the local environment

Save notebook files and note the SSH alias, managed UUID and any custom runtime
paths. Keep the session's Jupyter password available through your private
credential workflow. Close an attached JupyHop tunnel with Ctrl-C before changing
its local environment, then update from a separate terminal. The remote server
and kernel remain subject to their launcher and site policy.

Check the [release notes](releases.md) and [compatibility policy](compatibility.md).
The installed 0.1.0-to-0.2.0 upgrade is tested with the same surviving kernel and
unchanged remote runner/registry. This does not promise arbitrary future schema
migrations, downgrades or survival after a remote process exits.

## Install the chosen Conda release

For an existing client environment named `jupyhop`:

```console
mamba activate jupyhop
mamba install -c uibcdf -c conda-forge jupyhop=0.2.0
jupyhop --version
```

Review the proposed environment transaction. If you prefer to keep the previous
client environment available, create a separate one following
[Installation](installation.md). Both clients can reach the same live remote
managed session when their protocol/state contracts are compatible.

For source or wheel installations, install the reviewed replacement into the
chosen client environment using the same method described in
[Installation](installation.md#source-or-reviewed-wheel). There is no public
PyPI 0.2.0 release or remote JupyHop package to update.

## Verify by reconnecting

From the updated local client:

```console
jupyhop status workstation SESSION_ID
jupyhop open workstation SESSION_ID
```

Authenticate to Jupyter and return to the existing notebook/kernel. Use
`discover`/`open` with the required runtime paths for an unmanaged server.
Reconnection makes a new local forward; it does not recreate kernel memory.

If the client reports incompatible state/protocol, preserve private records and
check the supported versions. Do not edit schema numbers, delete the registry or
start a replacement server as a migration step. Report the redacted version/error
details using [Troubleshooting](troubleshooting.md#reporting-a-problem).
