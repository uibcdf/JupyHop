# JupyHop

**Open remote Jupyter sessions through the SSH access you already have.**

JupyHop discovers existing servers, creates an SSH tunnel and opens Jupyter's
normal login page. It can also start and manage your own remote servers, then
reconnect another authorized client to the same surviving notebook and kernel.
Your notebooks, Python environments and computation stay on the remote computer.

```console
jupyhop open workstation
```

`workstation` is an alias from your OpenSSH configuration. Direct SSH and
ProxyJump work with keys, an agent or native terminal password prompts. JupyHop
chooses forwarding ports automatically. Keep the command running while you work;
Ctrl-C closes its tunnel; it does not stop the remote server.

## Choose your workflow

| You want to… | Start here |
| --- | --- |
| Install the Linux client and open your first server | [Quickstart](quickstart.md) |
| Set up remote Jupyter or locate its environment/runtime | [Prepare the remote host](remote-setup.md) |
| Open a server someone already started under your remote account | [Existing servers](existing-servers.md) |
| Start a server with a chosen Python and project directory | [Managed sessions](managed-sessions.md) |
| Continue the same computation from another client | [Reconnection and recovery](recovery.md) |
| Reach a workstation through a gateway | [SSH and gateways](ssh.md) |
| Fix an empty search or a connection error | [Troubleshooting](troubleshooting.md) |
| Understand a UUID, session state or registry location | [Session reference](sessions.md) |
| Update an existing local client | [Update the client](upgrading.md) |

## Existing and managed servers

An **existing server** was started outside JupyHop. JupyHop discovers and opens
it; its original launcher controls its lifetime.

A **managed server** was created by `jupyhop start`. It has a remote session UUID
and private recovery records. JupyHop can check its state, gracefully stop that
verified server and archive its inactive records. Stop and archive always require
the exact managed UUID and explicit authorization.

Both workflows preserve Jupyter authentication. Reconnection preserves memory
only while the original kernel is alive. A reboot or kernel crash loses that
memory.

## Current release

Version **0.2.0** is available from the [uibcdf Conda channel](https://anaconda.org/uibcdf/jupyhop)
for Linux and CPython 3.11–3.14. The client needs no local Jupyter. Discovery is
always partial; supported endpoints and remote prerequisites are listed in
[Compatibility](compatibility.md).

JupyHop uses OpenSSH and user-owned remote processes. It requires no JupyterHub
deployment or central JupyHop service. It is an independent MIT-licensed project,
not affiliated with Project Jupyter.

```{toctree}
:caption: Documentation
:maxdepth: 1

getting-started
user-guide
reference
project
```
