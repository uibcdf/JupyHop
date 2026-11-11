---
myst:
  html_meta:
    description: "Return to the same running Jupyter notebook from this or another authorized client. Understand tunnel lifetimes and reconcile interrupted operations."
    "property=og:description": "Return to the same running Jupyter notebook from this or another authorized client. Understand tunnel lifetimes and reconcile interrupted operations."
---

(reconnection-and-recovery)=
# Return to a running notebook

Close a tunnel at one computer and continue from another, without remembering
ports or copying local session state. JupyHop reconnects you to the existing
remote server. **Memory remains only while the original kernel is alive.**

If you have not connected yet, start with the [Quickstart](quickstart.md).

## Reconnect from the same or another client

On another Linux browser computer, [install JupyHop](installation.md) and check
that its ordinary SSH route reaches the same remote account. Each client can
have its own direct or gateway route. Supply any custom discovery paths there
too; no old client directory or forwarding port needs copying.

For a named server started with JupyHop, run in your **local terminal**:

```console
jupyhop resume workstation --name analysis
```

For a server started outside JupyHop, or to choose a session by number, run
**locally**:

```console
jupyhop open workstation
```

Log in through Jupyter's normal page. Select the **original running notebook and
kernel** in JupyterLab. Opening a new notebook/kernel or restarting one gives
separate memory. If you used the Quickstart's example, a new cell containing
`print(continuity_marker)` should print `hello from the remote kernel` when you
have returned to that living kernel.

Two clients can also stay connected through independent tunnels. Closing one
does not close the other. JupyHop does not coordinate simultaneous edits to the
same notebook file.

## What survives disconnection

| Event | What to do |
| --- | --- |
| Browser closes | Reopen through the attached tunnel, or run open again |
| Ctrl-C or client terminal closes | Run resume/open to create a new tunnel |
| SSH route or network fails | Restore access, then inspect and reopen; failure does not prove the server stopped |
| Another SSH route reaches the same host/account | Reuse the current managed name or original UUID |
| Server/kernel exits or the host reboots | Inspect the observed state; a new connection cannot recreate lost memory |

Managed servers use private tmux; existing servers use their original launcher.
Site logout/cgroup policy can still terminate them. JupyHop does not enable
linger, change systemd/PAM policy or restart a lost kernel. Ask your administrator
about permitted persistent workloads when needed.

Same-kernel reconnect, independent clients and a two-hour disconnected synthetic
workload have been observed. Forced last logout/reboot and physical network
moves remain separate, unmeasured conditions; see [Compatibility](compatibility.md).

## Reconcile an interrupted operation

Keep the request UUID printed by managed start. If the connection ends before
the reply is confirmed, the remote operation may already have happened. Inspect
**locally**, substituting that exact ID:

```console
jupyhop status workstation SESSION_ID
jupyhop discover workstation
```

The ID is especially useful here because a name might not have been registered
yet. Status can reconcile interrupted readiness; it does not restart a server.

| Interrupted operation | Safe next action |
| --- | --- |
| Start | Inspect that request UUID and discover before making a new start request |
| Stop | Inspect that exact UUID's status; retry it when appropriate |
| Archive | Retry archive with the same UUID to reconcile the move |
| Stop-and-archive | Read the reported phase; after a confirmed stop with uncertain archival, retry archive on that UUID |
| Open | Restore access and run open again; opening does not start a server |

`starting` without a verified PID is unconfirmed intent, not proof of a live
server. Missing/replaced identity is stale. An unsuccessful SSH/status request
is not evidence that nothing started. Preserve uncertain records; do not delete
state or edit schema numbers to force acceptance. [Troubleshooting](troubleshooting.md)
gives the next checks for specific messages.

## Credentials and client upgrades

With 0.4.0, resume a token-based managed session by name to open the browser
again. If browser access fails after readiness, retry resume for that same
session. For password-based or manually started servers, use the session's
Jupyter password or token at its login page. If credentials
changed, obtain the current one through your private authorized workflow. Browser
cookies follow Jupyter's policy; a private window can help diagnose login.
JupyHop does not cache or reset Jupyter passwords.

[Updating the local client](upgrading.md) does not reinstall remote scientific
environments or rewrite living launchers. Installed upgrades from 0.1.0 and
0.2.0 to 0.3.0 have been tested with a surviving kernel and unchanged remote
runner/registry. Unknown state/protocol versions are refused; arbitrary future
migrations are not promised. Keep [compatible clients and helpers](compatibility.md).

Interactive stop normally archives after confirmed inactivity. If a UUID has
left active status, inspect `jupyhop status workstation --history`. History is
retained evidence, not a resumable kernel, and old archived names are not selectors.

**Next:** [Choose and finish projects in the menu](managed-sessions.md#manage-from-one-terminal)
or [update a local client](upgrading.md).
