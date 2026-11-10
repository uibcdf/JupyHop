---
myst:
  html_meta:
    description: "Open a Jupyter server already running under your SSH account. Select a server, log in and extend discovery with known environments or runtime paths."
    "property=og:description": "Open a Jupyter server already running under your SSH account. Select a server, log in and extend discovery with known environments or runtime paths."
---

(open-an-existing-server)=
# Open an existing Jupyter server

Use this workflow when Jupyter is already running under your remote SSH account,
perhaps in a terminal, tmux or another Conda environment. JupyHop connects you to
that server and keeps its original configuration and launcher.

First time using JupyHop? [Install and follow the Quickstart](quickstart.md).

(establish-ssh-access)=
## Before you begin

- [Install the client locally](installation.md) and check that `ssh workstation`
  reaches the intended account. Replace `workstation` with your SSH alias;
  [gateway routes](ssh.md#proxyjump) work too.
- Have an authenticated Jupyter server running remotely, with a
  [supported endpoint](compatibility.md#endpoint-and-remote-requirements).
- Have that server's existing **Jupyter password or token** available privately.
  It is separate from your SSH password. [Remote setup](remote-setup.md) helps
  locate the environment or create a first manual server.

## Discover and open

Run in your **local terminal**:

```console
jupyhop open workstation
```

Open searches automatically. Select a server number, even when only one is ready,
then log in on Jupyter's normal browser page. You can see a
[chooser and notebook example](quickstart.md#3-open-a-server-that-is-already-running)
in the Quickstart. There is no forwarding port to configure and no mandatory
JupyHop TOML file or remote JupyHop package.

Keep the command running while you work. **Ctrl-C closes only this tunnel.**
Run the same open command again to return to a living server/kernel. Its original
launcher and site policy determine whether it survives disconnection.
JupyHop cannot stop or archive this externally started server.

## Authenticate and work

Enter an SSH password only in the terminal's OpenSSH prompt. Enter the existing
Jupyter password/token in **Jupyter's browser login form**. For a token-auth server,
obtain the token privately from the original authorized launcher/startup output.
JupyHop does not retrieve it or insert it into the printed URL. If you never set
a Jupyter password, a token may be the normal login for that server.

The printed URL works on this computer while this tunnel is active. On another
authorized client, run open there to obtain its own URL. For a client without
automatic browser opening, run **locally**:

```console
jupyhop open workstation --no-browser
```

Open the printed URL in a browser on that same client. A URL from an older tunnel
can have a different port. [Recovery](recovery.md) explains same-kernel continuity
and using two clients.

## Extend a partial search

“No verified server found” means the known locations did not yield a supported
live server. It does **not** prove that no Jupyter server is running.
To inspect those locations without opening anything, run **locally**:

```console
jupyhop discover workstation
```

If you know a custom runtime directory or a Python from the server's environment,
use the corresponding local command, substituting its actual remote path:

```console
jupyhop open workstation --runtime-dir '~/custom-runtime'
jupyhop open workstation --remote-python /opt/conda/envs/analysis/bin/python
```

Repeat `--remote-python` or `--runtime-dir` for several known paths.
[Find those paths remotely](remote-setup.md#find-an-existing-environment) if needed.
The helper's standard library is enough for discovery; missing Jupyter packages
in a system-Python doctor report do not prove another environment has no server.
JupyHop does not enumerate every Conda environment or inspect arbitrary processes.

Runtime directories/files must belong to the current remote account, be private
(0700/0600) and have no symlinks. Discovery never deletes stale metadata.
[Discovery diagnostics](troubleshooting.md#ssh-works-but-discovery-is-empty)
explain missing/limited/unsupported results. Save repeated discovery preferences
in [optional host configuration](configuration.md); launch profiles' server paths
affect new servers, not existing discovery.

## Select a particular server

For a named server started by JupyHop, run **locally**:

```console
jupyhop open workstation --name analysis
```

For an unmanaged server, copy its current observation ID from discover; it is an
identifier, not a login token. Run **locally**, replacing the placeholder:

```console
jupyhop open workstation SERVER_ID
```

PIDs are not selectors. [Session identities](sessions.md) gives the exact rules.
Scripts must handle ambiguous selection explicitly; see [Scripting](scripting.md).

**Next:** [Reconnect later](recovery.md), or
[start a managed project](managed-sessions.md) when you want lifecycle control.
