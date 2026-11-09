# Reconnection and recovery

The browser, SSH tunnel, Jupyter server and notebook kernel have separate
lifetimes. Reconnection creates a new route to an existing server; memory is
preserved only if the original kernel survived.

## Reconnect from the same or another client

Close the first browser/tunnel when you finish using that client. On a second
Linux client, install JupyHop, configure authorized SSH access and supply any
custom discovery paths needed there. No old client-state directory or port
assignment needs copying.

For an existing server:

```console
jupyhop discover workstation
jupyhop open workstation SERVER_ID
```

For a managed server, reuse the exact UUID:

```console
jupyhop status workstation SESSION_ID
jupyhop open workstation SESSION_ID
```

Log in to Jupyter through its normal page and return to the existing
notebook/session. Starting a new server or restarting a kernel does not recover
the old computation. Opening the same notebook file alone cannot restore lost
in-memory objects.

The first client's browser/tunnel can also stay open: two authorized clients
can reach the same surviving server through independent local forwards. Closing
one forward leaves the other usable. In the second frontend, select the original
running notebook/session; creating a different kernel gives separate memory.
JupyHop does not coordinate simultaneous edits to the same notebook file.

## What survives disconnection

| Event | Expected action |
| --- | --- |
| Browser closes | Reopen through the attached tunnel, or run `open` again |
| Ctrl-C or client terminal closes | Create a new tunnel with `open`; the old owned forward is closed |
| SSH route or network fails | Restore authorized connectivity, then inspect and reopen |
| Another configured route reaches the same host/account | Reuse its original managed UUID |
| Server/kernel exits or the remote host reboots | Report lost/stale process state; live memory cannot be recreated |

Managed servers use private tmux, subject to the site's logout/cgroup policy.
Existing servers use their original launcher. JupyHop never enables linger or
changes systemd/PAM policy to extend process lifetime. Ask your administrator
about permitted persistent workloads if the site terminates processes at logout.

Two hours of disconnected synthetic computation followed by the same kernel,
session, memory and progress were observed on a real Linux target. Physical
home-client suspend/network moves and forced last logout/reboot were not measured;
see [Compatibility](compatibility.md).

## Reconcile an interrupted operation

Keep the request UUID printed for a managed launch. If a reply is lost, the
remote operation may already have taken effect.

| Interrupted operation | Recovery |
| --- | --- |
| Start | Inspect `status HOST UUID` and `discover HOST` before making a new start request |
| Stop | Inspect the exact UUID's status; retry that UUID when appropriate |
| Archive | Retry archive with the same UUID to reconcile the move |
| Open | Run open again after restoring access; opening does not start a server |

`starting` without a verified PID is unconfirmed intent, not proof of a live
server. Missing or replaced process identity is stale. An unavailable SSH route
does not establish that a server has stopped. Preserve records when outcomes
are uncertain; do not delete state or edit schema numbers to force acceptance.

## Credentials and client upgrades

Use a fresh authorized Jupyter login after credentials change. Browser cookie
validity follows Jupyter's policy; a private window can help diagnose login.
JupyHop has no password-reset or credential-cache feature.

The installed 0.1.0-to-0.2.0 client upgrade is tested with a live surviving kernel,
concurrent old/new clients and unchanged remote runner/registry bytes. A client
update does not reinstall remote environments or rewrite running launchers.
Unknown state/protocol versions are refused; arbitrary future migrations are not
promised. Keep [compatible clients and helpers](compatibility.md).

[Update the client](upgrading.md) gives the Conda procedure and reconnection
checks. [Session identities, states and storage](sessions.md) explains how to
distinguish an observed stale/unreachable session from a failed SSH request.
