# Start and manage a server

A managed server is created by `jupyhop start` in your remote account. Its UUID
identifies the exact server for status, open, stop and archive. The private remote
registry retains recovery evidence; display names are conveniences for people.

## Prepare the remote environment

Choose an existing remote Python with Jupyter Server >=2.20,<3, a usable notebook
kernel and your desired frontend, such as JupyterLab. Version 2.21.1 is the tested
recommended server stack. tmux must be available on the remote noninteractive
PATH, and the project directory must already exist.

Find the interpreter path in your chosen environment on the remote computer:

```console
python -c 'import sys; print(sys.executable)'
```

JupyHop selects that executable directly; it does not activate or install Conda
environments. [Environments](environments.md) distinguishes helper, server and
kernel Python. Scientific setup remains under your control.

## Start

On the local client, replace the example Python/project paths with your own remote
paths:

```console
jupyhop start workstation --server-python /opt/conda/envs/analysis/bin/python --workdir '~/projects/analysis' --name analysis
```

OpenSSH handles any SSH password/passphrase prompt. JupyHop separately prompts
for a **new Jupyter session password** and retains only its hash in private remote
settings. Remember that password for later clients. It must be independent of your
SSH password. Log in normally in the browser.

The returned UUID is the session's stable identifier. Copy it, or find it with
`jupyhop list workstation`. A new server and local forward receive ports
automatically; concurrent sessions do not need fixed port assignments.

To start without attaching a local browser/tunnel:

```console
jupyhop start workstation --server-python /opt/conda/envs/analysis/bin/python --workdir '~/projects/analysis' --name analysis --no-open
```

Use one of these starts for a new session. Repeating a successful start creates a
new request; an active duplicate display name is refused. After an interrupted
start, inspect the original request ID before making another request.

## Observe and reopen

```console
jupyhop status workstation SESSION_ID
jupyhop open workstation SESSION_ID
```

Use the exact UUID returned by start. `status workstation` can inspect the managed
registry without selecting a UUID. `open` revalidates the chosen server and makes
a fresh forward; it does not restart a healthy server or create a new kernel.

Closing the browser or pressing Ctrl-C in `open` leaves the remote server under
its private tmux launcher. Persistence is subject to site logout/cgroup policy.
See [Reconnection and recovery](recovery.md) before changing clients or retrying
an interrupted operation.

## Stop explicitly

```console
jupyhop stop workstation SESSION_ID
```

Confirm the exact UUID when prompted. **Stopping terminates that server and its
kernels**, including their running computation and memory. Scripts must supply
the exact UUID and `--yes` to authorize the action.

Stop verifies the current host/account, runner and live process identity, then
uses graceful pidfd signalling. Unsupported or uncertain identities are refused.
There is no forced-kill fallback, automatic restart or lifecycle control of an
unmanaged server. An interrupted stop may have taken effect: inspect status.

## Archive inactive records

After the exact managed session is observed inactive:

```console
jupyhop archive workstation SESSION_ID
```

Archive requires confirmation, moves private records/settings/recovery evidence
and releases the old display name. It does not delete notebooks, scientific
files or possible orphaned kernels. Live or uncertain records are refused.
There is no automatic or permanent archive deletion command.
