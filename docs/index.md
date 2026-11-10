---
myst:
  html_meta:
    description: "Open remote Jupyter in your local browser through SSH. Start named sessions, reconnect to living kernels and manage projects without manual tunnels."
    "property=og:description": "Open remote Jupyter in your local browser through SSH. Start named sessions, reconnect to living kernels and manage projects without manual tunnels."
---

(jupyhop)=
# Remote Jupyter over SSH

**Your remote notebooks, in your local browser.**

JupyHop finds your running Jupyter server, connects through your existing SSH
access and opens your browser. Your notebooks and computations stay remote;
you do not have to choose ports or build tunnels by hand.

```console
jupyhop open workstation
```

<p class="jh-actions"><a class="jh-button" href="quickstart.html">Install and open your first notebook →</a> <a href="#room-to-grow">See what you can do</a></p>

**Linux · Python 3.11–3.14 · Existing SSH access**

No local Jupyter or central service required. [Version 0.3.0](releases.md) is
available from the uibcdf Conda channel.

## Two ways to begin

::::{container} jh-grid
:::{container} jh-card
<h3 id="jupyter-is-already-running">Jupyter is already running</h3>

Open it through SSH and log in with its existing password or token. No remote
JupyHop installation is needed.

[Open an existing server →](existing-servers.md)
:::
:::{container} jh-card
<h3 id="you-need-a-new-server">You need a new server</h3>

Start a named session in an existing remote Jupyter environment. Choose your
project directory and return to it later.

[Start your first managed session →](quickstart.md#start-and-recover-an-owned-server)
:::
::::

## Your browser travels; your computation stays

::::{container} jh-route
:::{container} jh-route-node
**Your Linux computer**

JupyHop + browser
:::
:::{container} jh-route-link
**SSH**

Direct or through an optional gateway
:::
:::{container} jh-route-node
**Remote Linux computer**

Jupyter + kernels + notebooks
:::
::::

Run JupyHop on the computer where you use the browser. It reuses OpenSSH aliases,
keys, agents and password prompts, including [ProxyJump](ssh.md#proxyjump).
The gateway needs SSH access and forwarding permission; Jupyter runs at the
destination. Keep the local command running while you work. **Ctrl-C closes the
tunnel and leaves the remote server running** under its existing launcher.

## Room to grow

Start with one connection. Add these capabilities when your work needs them:

- **Return to a computation.** [Resume a named session](recovery.md) from another
  authorized client. Memory remains available while the same kernel is alive.
- **Keep projects organized.** [Manage sessions](managed-sessions.md#manage-from-one-terminal)
  from a terminal menu: choose, inspect and finish work without memorizing IDs.
- **Choose your scientific Python.** Use an existing remote environment and
  [select notebook kernels](environments.md) independently.
- **Work across machines.** [Inspect several SSH hosts and save profiles](configuration.md)
  for repeated Python/project choices.
- **Automate and get help.** Use [JSON in scripts](scripting.md),
  [diagnostic reports](diagnostics.md) and the full [CLI reference](cli.md).

## Is JupyHop a fit?

Use it when you have authorized SSH access to a Linux workstation or server and
want to use its notebooks from a Linux browser computer. Existing servers can be
opened; servers started by JupyHop can also be stopped and archived with explicit
confirmation. Both keep Jupyter authentication enabled.

Discovery is partial and the remote environment must already exist. Reconnection
cannot restore a stopped kernel's memory. Check the
[supported server setups](compatibility.md) if your system uses a custom endpoint
or authentication scheme. JupyHop is an MIT-licensed CLI for individual SSH
accounts; shared portals, Slurm integration and macOS support are outside the
current release.

**Ready? [Open your first notebook →](quickstart.md)**

Need help first? [Choose your starting point](getting-started.md) or
[solve a connection problem](troubleshooting.md).

```{toctree}
:caption: Documentation
:maxdepth: 1
:hidden:

getting-started
user-guide
reference
project
```
