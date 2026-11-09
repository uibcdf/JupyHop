# Prepare the remote host

Run this guide **on the remote Linux computer**, after connecting with
`ssh workstation`. The client and browser stay on your local computer. Opening
an existing compatible server needs no new installation; use the environment
and launcher that already provide it.

## Find an existing environment

In the remote environment you intend to use, inspect its interpreter and Jupyter:

```console
python -c 'import sys; print(sys.executable)'
python -m jupyter_server --version
python -m jupyter kernelspec list
python -m jupyter --runtime-dir
```

Copy the absolute Python path and, for an existing server, its actual runtime
directory. If the server was launched with a custom `JUPYTER_RUNTIME_DIR`, use
that path: an unrelated shell or environment need not report the same directory.
The [Jupyter directory reference](https://docs.jupyter.org/en/latest/use/jupyter-directories.html)
explains these environment variables.

Back **on the local client**, substitute the copied paths:

```console
jupyhop doctor workstation --remote-python /absolute/remote/env/bin/python
jupyhop discover workstation --runtime-dir /absolute/remote/runtime
```

`doctor` checks one interpreter's packages and capabilities. It does not test a
Jupyter login, kernel execution, forwarding policy or server persistence. Missing
Jupyter in the helper does not prevent discovery of a server in another
environment. Python >=3.11 and the Linux process/socket checks are still required.

## Create an environment when needed

If your authorized remote account needs a new environment, the following is an
example of the tested server stack. Run it **remotely**, with your site's
permission to install packages and run Jupyter:

```console
mamba create -n jupyter-remote -c conda-forge python=3.14 jupyter_server=2.21.1 jupyterlab=4.6.4 ipykernel=7.4.0 tmux
mamba activate jupyter-remote
python -c 'import sys; print(sys.executable)'
python -m jupyter kernelspec list
command -v tmux
```

Record that Python path. The version pins reproduce the observed stack; review
upstream fixes and the [compatibility matrix](compatibility.md) when choosing
other versions. JupyHop does not execute these installation commands for you.
For managed sessions, tmux must also be discoverable on the noninteractive SSH
PATH; installing it only in an activated environment may not provide that.
See [SSH troubleshooting](troubleshooting.md#tmux-works-interactively-but-start-reports-missing-tmux).

You can now return to your **local client** and follow
[Managed sessions](managed-sessions.md), supplying the recorded Python path.
Managed launch supplies its own private runtime directory and authentication
settings. It does not require the manual launch below.

## Try a manually launched server

This optional example creates an **unmanaged** server for the existing-server
workflow. Run it **remotely** in the Jupyter environment above. The fresh private
runtime directory keeps this server's credentials outside the notebook project:

```console
mkdir -p "$HOME/projects/jupyhop-demo"
jupyhop_runtime_dir=$(mktemp -d "$HOME/jupyhop-runtime-XXXXXXXX")
printf '%s\n' "$jupyhop_runtime_dir"
JUPYTER_RUNTIME_DIR="$jupyhop_runtime_dir" python -m jupyterlab --no-browser --ServerApp.ip=127.0.0.1 --ServerApp.port=0 --ServerApp.root_dir="$HOME/projects/jupyhop-demo"
```

Leave this remote terminal open. Copy the printed runtime directory. From a
**second local terminal**, substitute that path:

```console
jupyhop discover workstation --runtime-dir /absolute/remote/jupyhop-runtime-XXXXXXXX
jupyhop open workstation --runtime-dir /absolute/remote/jupyhop-runtime-XXXXXXXX
```

The fresh server normally supplies a token in its remote startup output, unless
your existing configuration uses a password. Keep that output private and enter
the token/password in the local Jupyter login form. The upstream
[authentication guide](https://jupyter-server.readthedocs.io/en/stable/operators/security.html)
describes this login. Leave authentication enabled; use the local URL printed by
JupyHop to reach the forwarded endpoint.

Ctrl-C in the **local JupyHop terminal** closes the tunnel. Ctrl-C in the
**remote Jupyter terminal** shuts down this manually launched server, with
Jupyter's normal confirmation. Its launcher controls persistence. For work that
must survive closing the remote terminal, use a permitted persistent launcher or
the [managed workflow](managed-sessions.md). JupyHop cannot stop/archive this
manual server or clean up its runtime files.
