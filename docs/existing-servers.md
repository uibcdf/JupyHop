# Open an existing server

Use this workflow when Jupyter is already running under your remote Unix account,
whether it was launched in a terminal, tmux or another environment. Opening a
server preserves its original ownership, configuration and launcher.

## Establish SSH access

First verify your route using ordinary OpenSSH:

```console
ssh workstation
```

Verify a new host fingerprint through your normal trusted channel, then exit the
SSH shell. Routing and gateway setup are described in [SSH and gateways](ssh.md).

The remote server must have a supported authenticated IPv4 loopback HTTP endpoint
and private runtime metadata. See [Compatibility](compatibility.md). Its existing
Jupyter password/token must be available through your authorized private workflow.

To find the environment/runtime or launch a first manual server, follow
[Prepare the remote host](remote-setup.md). `open` does not start a missing server.

## Discover and open

On your local client:

```console
jupyhop discover workstation
jupyhop open workstation
```

With one verified candidate, `open` creates a local loopback forward and opens the
normal Jupyter login page. With multiple candidates, a terminal lets you choose.
To select explicitly, copy the exact ID shown by discovery:

```console
jupyhop open workstation SERVER_ID
```

Names and PIDs are not selectors. The [session reference](sessions.md) explains
managed UUIDs and unmanaged observation IDs. In scripts or with `--json`,
ambiguous selection is an error even when a controlling terminal is available.
No JupyHop TOML file, remote JupyHop installation or manual forwarding-port
selection is needed for this workflow.

## Authenticate and work

SSH authentication and Jupyter login are separate. Enter the remote account's
SSH password only in OpenSSH's native prompt. Enter the existing Jupyter
password/token on Jupyter's login page. JupyHop does not retrieve either secret
from existing servers or insert it into the printed URL.

Keep the terminal command running. The local URL belongs to this client and its
active tunnel; run `open` again on another authorized client to obtain a new URL.

For a client without a browser:

```console
jupyhop open workstation --no-browser
```

Open its printed login URL in a browser on that same client. Ctrl-C closes only
the owned local SSH resources. The external launcher and site policy determine
whether the remote server survives disconnection. JupyHop cannot stop or archive
an existing server.

## Extend a partial search

Discovery checks known runtime directories and validates candidates. It does not
enumerate every Conda environment or prove that no servers exist when none are
found. Additional known paths and helper interpreters can extend coverage:

```console
jupyhop discover workstation --runtime-dir '~/custom-runtime'
jupyhop open workstation --remote-python /opt/conda/envs/analysis/bin/python
```

Replace the example interpreter with an existing path on the remote host.
Discovery/open accept repeated `--remote-python` and `--runtime-dir` options.
The [environment guide](environments.md) explains interpreter selection; profiles
and host preferences can retain known paths for future invocations. Profiles'
server Python/workdir settings affect new launches; use host `remote_python` and
`runtime_dirs` to extend later discovery.

Runtime directories/files must be current-user-owned, private (0700/0600) and
without symlinks. Discovery never removes stale metadata. Unsupported metadata,
process identities or endpoints remain diagnostics rather than authorization
to open or control an unrelated process.
