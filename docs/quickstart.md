---
myst:
  html_meta:
    description: "Install JupyHop, open your first remote notebook through SSH, recognize the login prompts and reconnect to the same living kernel."
    "property=og:description": "Install JupyHop, open your first remote notebook through SSH, recognize the login prompts and reconnect to the same living kernel."
---

(quickstart)=
# Open your first remote notebook

Install JupyHop on the **local Linux computer where you use the browser**.
Jupyter will run on the **remote Linux computer**. You need mamba or Conda
locally and authorized SSH access to that remote computer.

(install-the-client)=
## 1. Install the client

Run in your **local terminal**, using mamba:

```console
mamba create -n jupyhop -c uibcdf -c conda-forge python=3.14 jupyhop=0.3.0
mamba activate jupyhop
jupyhop --version
```

Expect `jupyhop 0.3.0`. With Conda, replace `mamba` with `conda` in both commands.
Python 3.11–3.14 is supported. The package includes OpenSSH; you do not need
Jupyter or tmux locally. See [Installation](installation.md) for other methods.

## 2. Check your SSH route

In the **same local terminal**, replace `workstation` with your working SSH alias:

```console
ssh workstation
```

Verify a new host fingerprint through your usual trusted channel. Once you reach
the remote shell, run `exit` to return to your local terminal. Password prompts,
keys and agents all work. If SSH fails, [fix the route first](ssh.md); a private
workstation can be reached through a [ProxyJump gateway](ssh.md#proxyjump).

**Now choose one path:** if Jupyter is already running, continue below. If you
need a new server, [skip to managed start](#start-and-recover-an-owned-server).

(open-a-server-that-is-already-running)=
## 3. Open a server that is already running

The remote host needs Python 3.11 or later and a
[supported authenticated Jupyter server](compatibility.md) under your SSH
account. It may run in a different Conda environment. You need its existing
Jupyter password or token; [remote setup](remote-setup.md) helps locate the
environment or prepare a first server.

Run **locally**:

```console
jupyhop open workstation
```

Open already searches for servers; a separate discover command is optional.
In a terminal, you see a numbered choice even if only one server is ready.
For example, with invented data and no additional discovery warnings:

```text
Discovery is partial: only known runtime paths were searched; other environments or paths may exist.
1: (unnamed)  unmanaged  ready  aaaaaaaaaaaaaaaaaaaaaaaa
Select a session number (Enter cancels): 1
http://127.0.0.1:49152/login?next=%2F
Tunnel attached. Log in with your existing Jupyter password/token. Ctrl-C closes only this tunnel; the remote server is not stopped.
```

Choose a number. The browser opens Jupyter's login page; enter **that server's
Jupyter password or token** there. An SSH password belongs only in the terminal's
OpenSSH prompt. A gateway can ask for a separate SSH password. JupyHop does not
retrieve existing Jupyter credentials; [which password to use](security.md#two-authentication-steps)
explains the distinction.

Once logged in, open a notebook and select a remote kernel. Try this harmless cell:

```python
continuity_marker = "hello from the remote kernel"
print(continuity_marker)
print(sum(range(10)))
```

Expected notebook output:

```text
hello from the remote kernel
45
```

```{figure} _static/first-notebook.png
:alt: JupyterLab displaying a notebook cell and the output hello from the remote kernel followed by 45.
:class: jh-screenshot

A notebook in a disposable JupyterLab environment. The cell above runs in the
remote kernel; the browser displays its result.
```

**You are connected.** Keep the JupyHop terminal running. Ctrl-C closes only its
tunnel. The browser may then show a connection error; that is expected until you
reconnect. The existing server's launcher and site policy control its lifetime.

To return, run `jupyhop open workstation` again, log in and select the **existing
running notebook/kernel**. In a new cell, `print(continuity_marker)` shows the same
value if that kernel survived. A newly created or restarted kernel has different
memory. From another authorized Linux client, install JupyHop and use its own
SSH configuration to reach the same account; no old forwarding port is needed.

**No server found?** The search checks known locations and is always partial.
[Provide a known runtime path or Python](existing-servers.md#extend-a-partial-search).
If you have not started Jupyter yet, use the path below.

## Start and recover an owned server

Choose this path **instead of the existing-server path** when you need a new
server. You need an existing remote Python with Jupyter Server 2.20 or later
(below 3), a notebook kernel and a frontend such as JupyterLab. The project
directory must exist, and tmux must be available to noninteractive SSH commands.
[Prepare and check these once](remote-setup.md) if needed; JupyHop does not
install or activate remote Conda environments.

Run **locally**, substituting the actual remote Python and project directory:

```console
jupyhop start workstation \
    --server-python /absolute/remote/env/bin/python \
    --workdir '~/projects/analysis' \
    --name analysis
```

With the published **0.3.0** client, choose and confirm a new Jupyter session
password, answer any OpenSSH prompts, then enter the Jupyter password in the
browser. Keep it for later visits to this session.

With the **0.4.0 source candidate**, answer the OpenSSH prompts and continue in
your browser. JupyHop handles access to the newly managed session automatically.
A gateway can still prompt for its own SSH password.

The command normally starts the server **and opens it**. Do not start it again
to reconnect. Create a notebook and try the cell above. After Ctrl-C closes the
tunnel, return with the name you chose:

```console
jupyhop resume workstation --name analysis
```

Complete Jupyter login if prompted, then select the original running notebook/kernel. As long as that server
and kernel survived, their computation and memory remain. A stopped kernel,
remote reboot or site policy that kills workloads cannot be undone by reconnecting.

(stop-and-retire-a-managed-entry)=
## Choose sessions and finish work

Run **locally**, after closing an attached tunnel or in another terminal:

```console
jupyhop manage workstation
```

The menu shows managed-session counts and offers open/resume, stop, archive,
history, refresh and exit. You can select by number; no need to remember IDs.
[See an example menu](managed-sessions.md#manage-from-one-terminal).

When you are done with the managed server, choose **Stop** and confirm.
**Stop terminates all its kernels and computations.** Interactive stop normally
archives the inactive records too, retaining evidence and releasing the session
name. Notebooks remain in the project directory. Existing servers started outside
JupyHop remain open-only.

**Next:** [Learn session management](managed-sessions.md),
[return from another computer](recovery.md) or
[save project settings and use several hosts](configuration.md).
For a different result or an error, start with [Troubleshooting](troubleshooting.md).
