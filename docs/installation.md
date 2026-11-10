# Installation

Install JupyHop on the computer where you will use the browser. The supported
client platform is Linux with CPython 3.11–3.14. Install only the client on each
additional computer; live managed-session records stay on the remote host.

## Conda or mamba

The current public channel coordinate is **0.3.0=py_0**, including named
selection, management, history and diagnostic reports.

Create a fresh environment from the public uibcdf and conda-forge channels:

```console
mamba create -n jupyhop -c uibcdf -c conda-forge python=3.14 jupyhop=0.3.0
mamba activate jupyhop
jupyhop --version
jupyhop --help
```

Python 3.11, 3.12 and 3.13 are supported too. Conda supplies OpenSSH, the
external SSH client. Local Jupyter and tmux are unnecessary. The Python client
has no mandatory Python-package dependencies.

The package uses a noarch Python payload with an explicit Linux constraint;
this does not advertise macOS or Windows support. The current published Conda
build is `0.3.0=py_0`; its [publication evidence](https://github.com/uibcdf/jupyhop/blob/main/devguide/31-03-conda-publication.md)
records the exact file and SHA256.

## Source or reviewed wheel

JupyHop has not been published to PyPI. To install a reviewed source checkout,
use your chosen virtualenv or Conda environment:

```console
python -m pip install .
jupyhop --version
```

Alternatively install a reviewed wheel with `python -m pip install PATH_TO_WHEEL`.
These routes require OpenSSH on the client's PATH. Contributors can use the
editable installation described in [Contributing](contributing.md).

## What the remote host needs

| Workflow | Remote prerequisites |
| --- | --- |
| Discover and open | Authorized SSH access, Linux, Python >=3.11 as a helper, an existing compatible authenticated Jupyter server and private current-user runtime metadata |
| Start a managed server | The above helper, tmux on the remote PATH, an existing Python with Jupyter Server >=2.20,<3 and a usable kernel, an existing working directory and stable Linux machine identity |
| Safely stop a managed server | Linux pidfd support exposed through the selected helper Python or named libc wrappers |

JupyterLab or another suitable frontend must be present remotely to edit
notebooks. JupyHop does not install scientific environments, run activation hooks
or install a remote JupyHop package. For managed start it writes a private runner
and state for that new session.

For commands to locate or create the remote environment, see
[Prepare the remote host](remote-setup.md). To replace a client installation
while retaining a live remote session, follow [Update the client](upgrading.md).
Check [Compatibility](compatibility.md), then follow the [Quickstart](quickstart.md).
