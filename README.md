# JupyHop

**Your remote Jupyter notebooks, in your local browser.**

JupyHop is a Python command-line tool that opens remote Jupyter through the SSH
access you already have. It finds running servers, chooses forwarding ports and
opens your browser. You can also start named sessions, return to a living kernel
from another computer and manage your projects from one terminal.

**Linux · Python 3.11–3.14 · MIT license**

[Documentation](https://www.uibcdf.org/jupyhop/) ·
[First notebook](https://www.uibcdf.org/jupyhop/quickstart.html) ·
[Report a problem](https://github.com/uibcdf/jupyhop/issues)

## Installation

On the Linux computer where you use the browser, with mamba installed:

```console
mamba create -n jupyhop -c uibcdf -c conda-forge python=3.14 jupyhop=0.3.0
mamba activate jupyhop
```

Use `conda` instead of `mamba` if you prefer. The published **0.3.0** package
includes OpenSSH; local Jupyter and tmux are unnecessary. See
[installation options](https://www.uibcdf.org/jupyhop/installation.html) for
other Python versions and source installation. JupyHop is not on PyPI.

## Open your first notebook

If `ssh workstation` already works and Jupyter is running under that remote
account, run this **locally**:

```console
jupyhop open workstation
```

Replace `workstation` with your SSH alias. Choose a server in the terminal, then
log in on Jupyter's normal browser page with that server's password or token.
SSH keys, agents and native password prompts work, including through
[ProxyJump gateways](https://www.uibcdf.org/jupyhop/ssh.html#proxyjump).

Keep the terminal running while you work. **Ctrl-C closes only the tunnel**;
it leaves the remote server alone. Run the same command again to reconnect.
No JupyHop configuration file or remote JupyHop installation is needed for this
ordinary workflow. The remote host needs Linux, Python 3.11 or later and a
[supported authenticated Jupyter server](https://www.uibcdf.org/jupyhop/compatibility.html).

Need a complete walkthrough, or no server is running yet? Follow the
[Quickstart](https://www.uibcdf.org/jupyhop/quickstart.html).

## Start a project and return later

Choose an existing remote environment containing Jupyter, an existing project
directory and a name. The remote computer also needs tmux on its SSH command
PATH; [remote preparation](https://www.uibcdf.org/jupyhop/remote-setup.html)
shows how to check those prerequisites.

Run **locally**, replacing the two remote paths:

```console
jupyhop start workstation \
    --server-python /absolute/remote/env/bin/python \
    --workdir '~/projects/analysis' \
    --name analysis
```

With the **0.4.0 source candidate**, authenticate in any OpenSSH prompts and
continue in your browser. A new managed session opens without a Jupyter password
prompt. With the published **0.3.0** client, choose a Jupyter session password and
enter it on the browser login page. Keep it for later visits to that session.

After closing the local tunnel, return from this or another authorized Linux
client:

```console
jupyhop resume workstation --name analysis
```

Your computation and memory remain available **while the original server and
kernel are alive**. Reconnection creates a new tunnel; it cannot restore a
kernel lost to a crash, stop or reboot. See
[reconnection](https://www.uibcdf.org/jupyhop/recovery.html) for the complete workflow.

## Choose, inspect and finish sessions

You do not need to memorize session IDs. Open the terminal menu:

```console
jupyhop manage workstation
```

It shows managed-session counts and offers open/resume, stop, archive, history,
refresh and exit. Named sessions and numbered selectors make ordinary use easy;
exact IDs remain available for scripts and recovery.

**Stop terminates that server and all its kernels.** Interactive stop asks for
confirmation and normally archives its inactive records too, releasing the name
and retaining evidence. Notebooks stay in your project directory.

JupyHop distinguishes two kinds of server:

| Server | What JupyHop can do |
| --- | --- |
| Started outside JupyHop | Discover and open it; its original launcher controls its lifetime |
| Started with `jupyhop start` | Open, inspect, safely stop and archive its inactive records |

See [managed sessions](https://www.uibcdf.org/jupyhop/managed-sessions.html) for
names, selectors, counts and completion.

## Grow from one notebook to several projects

- **Choose scientific environments.** Select the existing server Python and
  working directory; [choose notebook kernels separately](https://www.uibcdf.org/jupyhop/environments.html).
- **Reuse project settings.** Optional [profiles](https://www.uibcdf.org/jupyhop/configuration.html)
  remember Python paths and directories. Basic use needs no TOML file.
- **Inspect several machines.** `jupyhop list workstation-a workstation-b`
  inventories explicit SSH aliases. Separate terminal invocations provide
  independent tunnels for simultaneous work.
- **Automate and diagnose.** Use [JSON and exit codes](https://www.uibcdf.org/jupyhop/scripting.html)
  in scripts, or generate a [support report](https://www.uibcdf.org/jupyhop/diagnostics.html)
  when you need help.

## Where JupyHop fits

```text
Your Linux computer                       Remote Linux computer
JupyHop + browser  --- existing SSH --->   Jupyter + kernels + notebooks
                      optional gateway
```

Your environments, notebooks and computations stay remote. The gateway needs
ordinary SSH access/forwarding permission. There is no central JupyHop service
or JupyterHub deployment to maintain.

JupyHop suits individual users and teams with their own authorized SSH accounts.
It does not grant SSH access or provide cross-user sharing, a web login portal
or scheduler integration. Discovery checks known locations and is always
partial; an empty search does not prove that no server exists. Authentication
and host verification remain enabled. Read the
[compatibility boundary](https://www.uibcdf.org/jupyhop/compatibility.html) and
[security guidance](https://www.uibcdf.org/jupyhop/security.html).

## Project and contributing

Version **0.3.0** is published on the [uibcdf Conda channel](https://anaconda.org/uibcdf/jupyhop).
See [release notes](https://www.uibcdf.org/jupyhop/releases.html),
[updating a client](https://www.uibcdf.org/jupyhop/upgrading.html) and the
[publication record](devguide/31-03-conda-publication.md).

Contributions and research-computing use cases are welcome. Start with
[CONTRIBUTING](CONTRIBUTING.md) for development and isolated tests, or the
[development guide](devguide/README.md) for architecture, scenarios, experiment
evidence and the [roadmap](devguide/06-roadmap.md). Follow
[SECURITY](SECURITY.md) for vulnerability reporting.

Developed by the [Computational Biology and Drug Design Research Unit (UIBCDF)](https://www.uibcdf.org/).
JupyHop is independent of Project Jupyter.

## License

[MIT](LICENSE).
