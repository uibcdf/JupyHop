---
myst:
  html_meta:
    description: "Install the JupyHop Linux client with mamba or Conda. Supports Python 3.11–3.14 and includes OpenSSH without requiring local Jupyter."
    "property=og:description": "Install the JupyHop Linux client with mamba or Conda. Supports Python 3.11–3.14 and includes OpenSSH without requiring local Jupyter."
---

(installation)=
# Install JupyHop

Install the client on the **Linux computer where you use the browser**.
You need mamba or Conda for the recommended installation below. Supported client
Python versions are **3.11, 3.12, 3.13 and 3.14**.

## Conda or mamba

Run in your **local terminal**:

```console
mamba create -n jupyhop -c uibcdf -c conda-forge python=3.14 jupyhop=0.4.0
mamba activate jupyhop
jupyhop --version
```

Expected result:

```text
jupyhop 0.4.0
```

Prefer Conda? Use the equivalent commands **instead**:

```console
conda create -n jupyhop -c uibcdf -c conda-forge python=3.14 jupyhop=0.4.0
conda activate jupyhop
jupyhop --version
```

The published uibcdf package includes OpenSSH. **You do not need local Jupyter
or tmux.** To use another supported Python, change `python=3.14` in the create
command. On an additional client, repeat this installation and configure its
ordinary SSH route; remote managed-session records stay on the remote host.

**Next: [Open your first notebook →](quickstart.md#2-check-your-ssh-route)**

If JupyHop is already installed, follow [Update the client](upgrading.md).
The current Conda build is `0.4.0=py_0`. Its noarch Python payload has an explicit
Linux constraint; macOS and Windows are outside current support. Detailed
[publication evidence](https://github.com/uibcdf/jupyhop/blob/main/devguide/38-04-conda-publication.md)
identifies the tested archive and digest.

## What the remote host needs

You normally **do not install JupyHop remotely**. Use an existing environment
containing Jupyter, or [prepare one](remote-setup.md).

| What you want to do | Remote prerequisites |
| --- | --- |
| Open an existing server | Authorized SSH, Linux, Python 3.11 or later as a helper, and a compatible authenticated Jupyter server with private current-user runtime metadata |
| Start a new managed server | The helper above, an existing Python with Jupyter Server 2.20 or later (below 3), a usable kernel/frontend, tmux on the SSH command PATH, an existing project directory and stable Linux machine identity |
| Stop a managed server safely | Linux pidfd support through the selected helper Python or named libc wrappers |

JupyterLab or another suitable frontend is needed remotely to edit notebooks.
JupyHop selects existing executables directly; it does not install or activate
scientific environments. Managed start writes private settings/state and a
runner for its new session. [Compatibility](compatibility.md) lists exact endpoint
and platform boundaries.

## Source or reviewed wheel

JupyHop is **not published on PyPI**. In a reviewed source checkout, with your
chosen virtualenv or Conda environment active, run **locally**:

```console
python -m pip install .
jupyhop --version
```

Alternatively install a reviewed wheel with `python -m pip install PATH_TO_WHEEL`.
Both routes need OpenSSH on the client's PATH. The Python client has no mandatory
Python-package dependencies. Contributors can use the editable installation in
[Contributing](contributing.md).
