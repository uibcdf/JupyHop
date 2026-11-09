# Start and manage a server

A managed server is created by `jupyhop start` in your remote account. Its UUID
identifies the exact server for status, open, stop and archive. The private remote
registry retains recovery evidence; display names are conveniences for people.

## Prepare the remote environment

Choose an existing remote Python with Jupyter Server >=2.20,<3, a usable notebook
kernel and your desired frontend, such as JupyterLab. Version 2.21.1 is the tested
recommended server stack. tmux must be available on the remote noninteractive
PATH, and the project directory must already exist.

See [Prepare the remote host](remote-setup.md) if you need to install an
environment or check which Python/runtime is being used.

Find the interpreter path in your chosen environment on the remote computer:

```console
python -c 'import sys; print(sys.executable)'
```

JupyHop selects that executable directly; it does not activate or install Conda
environments. [Environments](environments.md) distinguishes helper, server and
kernel Python. Scientific setup remains under your control.

Managed start uses private JupyHop settings and enables JupyterLab when it is
installed in the selected server environment. Otherwise it provides the server/API
view. Your ordinary Jupyter configuration files and other automatically enabled
server extensions are not loaded by this launcher. There is no option to pass an
existing Jupyter config or arbitrary server flags to `start`. Use the existing-server
workflow when your separately configured launcher is needed, within the supported
endpoint/authentication boundary.

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

Passwords must contain 8–1024 characters without ASCII control characters. The
private prompt asks for confirmation before SSH authentication; `--password-stdin`
reads one UTF-8 line from a protected source.
[Scripting](scripting.md#start-with-a-protected-password-source)
shows the noninteractive form. There is no Jupyter password reset command.

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

An exit-0 status query means observation succeeded, not that the server is ready.
Read the [state meanings and storage reference](sessions.md); only `ready`
candidates can be opened. Status can reconcile an interrupted launch record.

Closing the browser or pressing Ctrl-C in `open` leaves the remote server under
its private tmux launcher. Persistence is subject to site logout/cgroup policy.
See [Reconnection and recovery](recovery.md) before changing clients or retrying
an interrupted operation.

## Stop explicitly

```console
jupyhop stop workstation SESSION_ID
```

Confirm the exact UUID when prompted. **Stopping terminates that server and all
its kernels**, including computations in other notebooks attached to the same
server. The managed UUID selects a server, not a particular notebook or kernel.
Scripts must supply the exact UUID and `--yes` to authorize the action.

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

Archive releases the name and one of the registry's 128 active-record slots.
Archived UUIDs are no longer returned by status/discovery and cannot be reopened
or restored by an archive command. Preserve the private archive path if needed.
