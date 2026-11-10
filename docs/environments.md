# Python and Conda environments

JupyHop selects existing executables by path. There are four distinct Python
roles; choosing a Jupyter server environment does not implicitly choose the
notebook kernel environment.

| Role | Where it runs | How it is chosen |
| --- | --- | --- |
| Client | Your local computer | The environment where you installed JupyHop |
| Helper | Remote account | `--remote-python`, the host preference, or `python3` |
| Managed server | Remote account | `--server-python`, a launch profile, or the selected helper |
| Notebook kernel | Remote account | Jupyter's existing kernelspec and notebook/session selection |

The helper needs Python >=3.11. For discovery/open its standard library is
sufficient. A managed server additionally needs compatible Jupyter and a usable
kernel; [Compatibility](compatibility.md) lists the full boundary.

## Diagnose an interpreter

```console
jupyhop doctor workstation
jupyhop doctor workstation --remote-python /opt/conda/envs/analysis/bin/python
```

Replace the example executable with an existing remote path. Doctor checks only
its selected Python and reports its Jupyter packages, runtime paths and
process-manager availability. Missing Jupyter in the system Python does not
prove there is no running Jupyter server in another environment. The system
Python may still serve as the discovery helper.

Doctor's systemd-user capability result is diagnostic. Managed launch
uses private tmux; a systemd backend is not implemented.

### Match the interpreter's import mode

JupyHop runs the remote helper and managed server with Python's
[isolated mode](https://docs.python.org/3.14/using/cmdline.html#cmdoption-I).
Packages available only through `PYTHONPATH`, the current directory or Python's
user site are not visible to those interpreters. Choose a Conda/venv/system
Python that contains the required packages in its own environment. An interactive
import succeeding after `pip install --user` does not establish that prerequisite.

To check the intended **server** interpreter on the remote host:

```console
/absolute/remote/env/bin/python -I -m jupyter_server --version
```

The helper can remain stdlib-only for discovery/open. Notebook kernels follow
their own kernelspec command/environment; this server/helper isolation does not
silently add `-I` to kernel commands.

## Existing servers across environments

Environments often share a user's ordinary Jupyter runtime directory. Custom
paths, environment variables and site layouts can give them different runtime
directories. Extend the known search explicitly:

```console
jupyhop discover workstation --remote-python /opt/conda/envs/analysis/bin/python --remote-python /opt/conda/envs/other/bin/python
jupyhop open workstation --runtime-dir '~/custom-runtime'
```

This extends a bounded partial search. It does not enumerate Conda environments,
activate them or inspect arbitrary processes. Supply the same additional paths on
another client when those paths are not otherwise known remotely.

## Choose a managed environment

```console
jupyhop start workstation --server-python /opt/conda/envs/analysis/bin/python --workdir '~/projects/analysis' --no-open
```

The working directory is remote. Quote `~/...` so your local shell does not expand
it; relative workdirs resolve against the remote home. Workdir symlinks are
canonicalized. Runtime/state paths have stricter no-symlink requirements.

Use [profiles](configuration.md) to retain Python/workdir preferences. `--env`
selects a JupyHop profile, not a Conda environment name or activation command.
Prepare any scientific environment activation requirements outside JupyHop.
Changing a profile affects later starts; it does not modify existing servers or
their immutable runners.

## Make another Python available as a notebook kernel

Run the following **remotely**, using an existing scientific environment with
ipykernel installed. Registering a kernelspec makes that Python selectable by
Jupyter; it does not change the server's Python:

```console
mamba activate analysis-env
python -m ipykernel install --user --name analysis-env --display-name 'Python (analysis-env)'
```

Choose a kernelspec name not already in use: registering the same name replaces
that specification. Inspect available entries from the server environment with
`python -m jupyter kernelspec list`. Then select the kernel in JupyterLab when
creating a notebook. To continue an existing computation, reconnect to its
original kernel/session; switching or restarting kernels loses that connection
to its memory. The [IPython kernel guide](https://ipython.readthedocs.io/en/stable/install/kernel_install.html)
also describes registering a kernel into a particular server environment.
