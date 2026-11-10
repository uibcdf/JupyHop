---
myst:
  html_meta:
    description: "Locate or create a remote Jupyter environment, record its Python path and verify tmux on the SSH command PATH before managed launch."
    "property=og:description": "Locate or create a remote Jupyter environment, record its Python path and verify tmux on the SSH command PATH before managed launch."
---

# Prepare the remote host

Use this guide once to locate a remote Jupyter environment or prepare a new one.
JupyHop itself normally runs only on your **local browser computer**. Jupyter,
the project directory and notebook kernels belong on the **remote computer**.

If a server is already running, you may be able to [open it now](existing-servers.md).
If you want JupyHop to launch one, finish the environment and tmux checks below,
then [start a managed session](managed-sessions.md#start).

## Find an existing environment

From your **local terminal**, connect using your working SSH alias:

```console
ssh workstation
```

Now in the **remote shell**, activate the environment you normally use for
Jupyter. With mamba, for example, replace `analysis-env` with its actual name:

```console
mamba env list
mamba activate analysis-env
python -c 'import sys; print(sys.executable)'
python -I -m jupyter_server --version
python -m jupyter kernelspec list
```

Use `conda` instead of `mamba` when appropriate. Record the **absolute Python
path** printed by the first Python command. The isolated `-I` check matches how
JupyHop starts its helper/server; [import-mode guidance](environments.md#match-the-interpreters-import-mode)
explains why packages installed only in a user site may not be visible.
For managed start, use Jupyter Server 2.20 or later (below 3), a usable kernel and
a frontend such as JupyterLab. The tested recommended stack uses Server 2.21.1.

For an existing server, locate the runtime path in **the shell/environment that
launched it**, preserving any custom `JUPYTER_RUNTIME_DIR`:

```console
python -m jupyter --runtime-dir
```

Environments often share this directory, but custom paths can differ. This query
identifies a path; it does not list or start servers. If you need to extend
[existing-server discovery](existing-servers.md#extend-a-partial-search), pass the
actual runtime path or Python path from your local client.

Prepare a working directory on the **remote computer**, if this is a new project:

```console
mkdir -p "$HOME/projects/analysis"
```

## Create an environment when needed

If there is no suitable environment, create one in your **remote shell**, using
mamba/Conda and your site's permitted installation workflow. This example
reproduces the tested server stack:

```console
mamba create -n jupyter-remote -c conda-forge \
    python=3.14 jupyter_server=2.21.1 jupyterlab=4.6.4 ipykernel=7.4.0
mamba activate jupyter-remote
python -c 'import sys; print(sys.executable)'
python -I -m jupyter_server --version
python -m jupyter kernelspec list
mkdir -p "$HOME/projects/analysis"
```

Record the Python path and check that a usable kernel is listed. These pins
reproduce the observed stack; review fixes and the
[compatibility matrix](compatibility.md) when choosing other versions.
JupyHop does not execute these installation commands for you.

## Check tmux for managed launch

Managed start uses tmux to run independently of the local tunnel. A tmux binary
installed only inside an activated Conda environment may not be visible to
ordinary SSH commands. **Selecting `--server-python` does not activate Conda.**

Exit the remote shell. From your **local terminal**, check the environment
JupyHop will actually use:

```console
ssh workstation 'command -v tmux'
```

If it prints a path such as `/usr/bin/tmux`, continue to the final check below.
An empty result means preparation is incomplete, even if tmux works after
interactive activation.

One complete option on **Debian/Ubuntu**, when your site permits system package
installation, is to reconnect with `ssh workstation` and run **remotely**:

```console
sudo apt-get install tmux
```

Exit that shell and repeat the local SSH check. On other systems use the site's
package-management procedure. If you cannot install system packages, ask the
administrator to provide tmux on the noninteractive SSH PATH, or arrange an
approved per-user PATH setting and recheck it. Keep startup output clean.
Do not continue to managed start until this check returns a usable path.
[tmux troubleshooting](troubleshooting.md#tmux-works-interactively-but-start-reports-missing-tmux)
explains the difference between interactive and command SSH environments.
Opening an existing server does not require tmux.

## Verify and start

From your **local terminal**, substitute the recorded remote Python path:

```console
jupyhop doctor workstation \
    --remote-python /absolute/remote/env/bin/python
```

Expect SSH OK, supported Python/Jupyter versions and `tmux found`. Doctor checks
that interpreter's prerequisites; it does not start or discover a server.
A missing-Jupyter result for the system Python does not mean no other environment
contains Jupyter.

**Next: [Start your named session →](managed-sessions.md#start)**
Supply the recorded Python and existing project directory. Managed start sets up
its own private runtime and authentication; you do not need the manual example.

## Try a manually launched server

This is an optional **alternative** for testing the existing-server workflow.
In your **remote Jupyter environment**, run:

```console
mkdir -p "$HOME/projects/jupyhop-demo"
jupyhop_runtime_dir=$(mktemp -d "$HOME/jupyhop-runtime-XXXXXXXX")
printf '%s\n' "$jupyhop_runtime_dir"
JUPYTER_RUNTIME_DIR="$jupyhop_runtime_dir" python -m jupyterlab \
    --no-browser --ServerApp.ip=127.0.0.1 --ServerApp.port=0 \
    --ServerApp.root_dir="$HOME/projects/jupyhop-demo"
```

Leave that terminal running. Keep the token in Jupyter's startup output private;
if your configuration uses a password, use that password instead. Copy only the
printed runtime directory. In a **second local terminal**, substitute that path:

```console
jupyhop open workstation \
    --runtime-dir /absolute/remote/jupyhop-runtime-XXXXXXXX
```

Select the server and enter its token/password in Jupyter's browser login form.
[Jupyter's authentication guide](https://jupyter-server.readthedocs.io/en/stable/operators/security.html)
explains that login. Keep authentication enabled and use JupyHop's current local URL.

Ctrl-C in **local JupyHop** closes the tunnel. Ctrl-C in **remote Jupyter** shuts
down this manual server, with Jupyter's normal confirmation. Its original launcher
controls persistence; JupyHop cannot stop/archive it or clean up its runtime files.
For persistent managed work, follow [Managed sessions](managed-sessions.md).
