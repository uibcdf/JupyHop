# Quickstart

JupyHop's client runs on Linux with CPython 3.11–3.14 and OpenSSH. It needs no
local Jupyter and no Python runtime dependencies. Version 0.2.0 has not been
published to PyPI; Conda distribution is described below.

## Install the client

Create a Linux client from the public Conda channel:

```console
mamba create -n jupyhop -c uibcdf -c conda-forge python=3.14 jupyhop=0.2.0
mamba activate jupyhop
jupyhop --version
```

Conda includes OpenSSH, without local Jupyter or tmux. See
[Installation](installation.md) for source/wheel alternatives, remote
prerequisites and additional-client setup.

## Open a server that is already running

First establish ordinary SSH access to an existing alias:

```console
ssh workstation
```

Verify the host fingerprint through your normal trusted channel, then exit that
SSH shell. JupyHop keeps strict host checking. In a terminal, OpenSSH handles
password/passphrase prompts; keys/agent work too. Python never reads or caches
the SSH password. User, keys, Include/Match and ProxyJump belong in OpenSSH
configuration. A POSIX-compatible remote login shell and Python >=3.11 are required.
Headless commands or explicit `--batch` require noninteractive SSH authentication.
Terminal authentication has its own `--ssh-auth-timeout` (default 120 seconds);
`--timeout` bounds probes/network startup. No key provisioning is mandatory.

`doctor` inspects only its selected Python. A system Python without Jupyter can
still act as the stdlib discovery helper for servers in Conda/venv environments;
Jupyter does not need installing into that system Python just to open one.

With your current-user Jupyter server already running remotely:

```console
jupyhop discover workstation
jupyhop open workstation
```

No JupyHop configuration file, remote JupyHop package, tmux or manual tunnel/port
selection is needed for this workflow. Select a server on the terminal if several
are found; scripts use its exact ID from `discover`.

Log in on Jupyter's normal page with the server's existing password/token. JupyHop
does not retrieve it. Obtain credentials only through the server's authorized
private workflow; avoid putting them in commands, URLs or bug reports.

Keep `jupyhop open` running. Ctrl-C closes its local forward; the existing server's
original launcher determines persistence. Use `--no-browser` on a headless client
and open the printed token-free login URL on that same client.

Discovery is always partial. For a custom runtime path or another helper Python:

```console
jupyhop discover workstation --runtime-dir '~/custom-runtime'
jupyhop open workstation --remote-python /absolute/remote/env/bin/python
```

Runtime directories/files must be current-user-owned, private (0700/0600) and
without symlinks. Supported endpoints are authenticated IPv4 loopback HTTP;
see [compatibility](compatibility.md) before using other server configurations.

## Start and recover an owned server

The remote host also needs tmux, Linux machine identity and an existing Python
>=3.11 with Jupyter Server >=2.20,<3 and a usable kernel. The currently recommended
tested server is 2.21.1. Environments and project directories must already exist.
JupyHop does not install them or run Conda activation hooks.

```console
jupyhop start workstation --server-python /absolute/remote/env/bin/python --workdir '~/projects/analysis' --name analysis --no-open
```

Choose a strong new session password when privately prompted. This password is
independent of SSH; remember it for future clients. Copy the returned session ID.
The server password hash is stored privately on the remote account; the plaintext
is not retained. Scripts use `--password-stdin` with a protected credential source.

```console
jupyhop open workstation SESSION_ID
```

Work in Jupyter, then close the browser and press Ctrl-C in the CLI. From the
original or another authorized client:

```console
jupyhop status workstation SESSION_ID
jupyhop open workstation SESSION_ID
```

Authenticate again and reconnect to the original notebook/kernel. If the server
and kernel survived, their memory remains; opening a notebook file cannot recover
memory lost through reboot or a crash. Remote last-logout policies can kill even
tmux workloads. JupyHop does not change systemd/linger/PAM policy or auto-restart.

## Stop and retire a managed entry

```console
jupyhop stop workstation SESSION_ID
jupyhop archive workstation SESSION_ID
```

Each action requires its exact managed UUID and terminal confirmation (`--yes`
explicitly authorizes it in scripts). Stop terminates that server and its kernels.
Archive requires observed inactivity and moves private records/settings/recovery
evidence, releasing the old name. It does not delete scientific files or stop
orphaned kernels. Neither action can control a manually launched server.

If an SSH/start/stop request is interrupted, the remote outcome can be unknown:
inspect `status`/`discover` before starting again. Retry an interrupted archive
with the same UUID. Read [troubleshooting](troubleshooting.md) for failure codes
and [Configuration](configuration.md) for optional profiles and multiple hosts.
