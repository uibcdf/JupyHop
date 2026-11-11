---
myst:
  html_meta:
    description: "Start named remote Jupyter sessions, resume by name, inspect the terminal menu and safely stop and archive finished work."
    "property=og:description": "Start named remote Jupyter sessions, resume by name, inspect the terminal menu and safely stop and archive finished work."
---

(start-and-manage-a-server)=
# Start and manage remote sessions

Start a named Jupyter server for a project, return to it later and finish it
safely when the work is done. JupyHop runs it under your remote SSH account
using a private tmux launcher. Your notebooks stay in the project directory.

New here? The [Quickstart](quickstart.md) shows a complete first notebook.
If you only need a server that is running already, use [Open an existing server](existing-servers.md).

## Prepare the remote environment

You need an existing project directory and remote Python containing Jupyter
Server 2.20 or later (below 3), a usable notebook kernel and your desired frontend,
such as JupyterLab. Server 2.21.1 is the tested recommended stack. tmux must be
available on the remote **noninteractive SSH PATH**.

[Prepare the remote host](remote-setup.md) shows how to obtain the Python path,
check kernels and verify tmux. JupyHop uses that executable directly, without
installing or activating a Conda environment. The notebook kernel can use
[a different Python](environments.md).

## Start

In your **local terminal**, replace the Python and project paths with existing
paths on the remote computer:

```console
jupyhop start workstation \
    --server-python /opt/conda/envs/analysis/bin/python \
    --workdir '~/projects/analysis' \
    --name analysis
```

With the **0.4.0 source candidate**, answer any OpenSSH prompts and continue in
your browser. New managed servers use a native Jupyter token generated on the
remote computer. JupyHop delivers browser access automatically after verifying
the selected session through SSH.

With the published **0.3.0** client, choose and confirm a Jupyter session
password first. After SSH authenticates, enter that password in Jupyter's login
page. Sessions started this way keep their usual login when reopened.

The server and local forward receive ports automatically. Use the name
`analysis` to find this project again. In 0.4.0, `--verbose` shows session UUIDs
and detailed observations. Names and UUIDs identify sessions.

### Choose password authentication

In 0.4.0, add `--auth password` if you want a Jupyter password for a new session.
Choose and confirm it in the terminal. JupyHop uses it to open the browser for
that first start. On later visits, enter it on Jupyter's login page if prompted.
Passwords contain 8–1024 characters without ASCII control characters. The
remote settings retain the hash. See the protected stdin workflow in
[Scripting](scripting.md#start-with-a-protected-password-source).

Use start once for a new project session. Repeating it creates a new request;
an unarchived duplicate name is refused. If start is interrupted, keep its
printed request ID and [inspect the outcome before retrying](recovery.md#reconcile-an-interrupted-operation).

## Observe and reopen

Keep the local command running while using its tunnel. Ctrl-C closes the tunnel
and leaves the remote server under its tmux launcher. Later, run **locally**:

```console
jupyhop resume workstation --name analysis
```

Complete Jupyter login if prompted, then select the original notebook/kernel. Resume is an alias for
open: it makes a fresh forward without restarting the server. Memory survives
only while the same kernel runs. See [Recovery](recovery.md) for another-client
access and site persistence limits.

If you prefer a numbered choice, or want a read-only overview, run **locally**:

```console
jupyhop resume workstation
jupyhop status workstation
```

These are independent choices, not mandatory steps before every connection.
The chooser shows names, origins and states, even for one ready candidate. In
0.4.0, add `--verbose` for UUIDs and endpoint details.
Only ready servers can open. Exit 0 from status means observation succeeded;
it can still describe a stopped/stale server. [Session states](sessions.md)
explain the exact distinctions.

## Manage from one terminal

In your **local terminal**, after closing an attached tunnel or in another terminal:

```console
jupyhop manage workstation
```

For two ready projects, the menu looks like this (invented names/IDs, with no
additional inventory warnings):

```{literalinclude} _static/session-menu.txt
:language: text
```

Choose an action, then a session by number. Open stays attached; Ctrl-C in that
open returns you to the menu and leaves the server running. OpenSSH may ask you
to authenticate again because that foreground connection ended. Exit closes the
menu's owned local connections. Start a new server with `start` separately.

The overview tells you how many **managed records** are ready, stopped awaiting
archive, need review or are archived. These are not counts of every Jupyter
process on the host. Unknown counts stay unknown; incomplete history is shown as
a lower bound. [Overview and history](sessions.md#overview-and-history) explains
pagination and scope. The menu manages one host at a time; [list](configuration.md#inventory-several-routes)
can inspect several aliases.

## Stop explicitly

When finished with the **server and all its notebooks**, run **locally**:

```console
jupyhop stop workstation --name analysis
```

Or omit `--name` to choose by number. The terminal confirmation identifies the
exact session and normally offers **stop and archive**. Type `stop` only when
you intend to end the work. **Stopping terminates all that server's kernels and
computations**, including work attached from another client.

After confirmed stop, archival retains evidence and releases the name/slot.
You do not need to remember a second housekeeping command. Notebooks and
scientific files remain in your project directory. Use `--keep-record` for
stop-only behavior. An uncertain stop never triggers archive; if stop succeeded
but archival is unconfirmed, the feedback gives a same-UUID recovery action.

Only servers started by JupyHop can be stopped this way. Names/choices resolve
once to the exact UUID; the backend revalidates ownership and process identity
before graceful pidfd signalling. There is no forced-kill fallback, automatic
restart or control of an unmanaged server.

Scripts require the exact UUID plus `--yes` and remain stop-only by default;
`--archive` explicitly authorizes both phases. See [Scripting](scripting.md).
An interrupted stop may have taken effect: inspect the exact UUID's status.

## Archive inactive records

A record can remain unarchived after `--keep-record`, a stop-only script or an
interrupted completion. Inspect and select it **locally**:

```console
jupyhop status workstation
jupyhop archive workstation
```

Archive asks for confirmation and rechecks inactivity. It retains private
settings/recovery evidence and releases the old name and one active-record slot.
It does not delete notebooks or stop possible orphaned kernels. Live or uncertain
records are refused. There is no automatic or permanent archive deletion command.
An exact current name or UUID can also select an inactive record.

The registry allows 128 unarchived records, including stopped entries; start
refuses before creating another record when full. Use the overview to find
inactive entries. JupyHop does not stop servers or delete evidence to make space.

Inspect history **locally**:

```console
jupyhop status workstation --history
```

Archives are evidence, not resumable sessions or kernel backups. Archived UUIDs
leave the active registry; a new server reusing the name has a new UUID.
History pages/counts can be partial. Preserve private archive paths if needed.

## Detached start and launcher details

For a deliberate launch without a local browser/tunnel, run **locally**:

```console
jupyhop start workstation \
    --server-python /opt/conda/envs/analysis/bin/python \
    --workdir '~/projects/analysis' \
    --name analysis --no-open
```

Use this form to start the server and return without opening it. To keep the
tunnel attached and open the browser yourself, add `--no-browser` to an open or
resume command. In 0.4.0, automatic access prints a private file link that you
can open on this computer within 60 seconds. For manual Jupyter login, use
`--login manual` to get the normal login URL. Manual login requires the server's
own credential or an existing browser cookie.

Use exact IDs for recovery and scripts:

```console
jupyhop status workstation SESSION_ID
jupyhop open workstation SESSION_ID
```

Exact-UUID status and legacy status JSON can reconcile interrupted launch
readiness; overview/history remain read-only. They do not restart the server.

The managed launcher loads private JupyHop settings, enables JupyterLab when
installed, and otherwise provides a server/API view. It does not load ordinary
Jupyter configuration files or other automatically enabled server extensions.
There is no arbitrary-config/server-flags option for start. Use the
[existing-server workflow](existing-servers.md) when your own supported launcher
configuration is required. Persistence remains subject to site logout/cgroup
policy; JupyHop does not enable linger or change systemd/PAM policy.

**Next:** [Reconnect from another computer](recovery.md),
[save project profiles](configuration.md) or consult [session storage and states](sessions.md).
