# JupyHop

**Your lightweight hub for remote Jupyter sessions.**

JupyHop is an open-source project for **discovering, opening, launching, managing, and reconnecting to remote Jupyter sessions over SSH**—without requiring a central JupyterHub deployment.

It is designed for researchers, data scientists, developers, and small teams who already have SSH access to workstations or servers and want to work with their remote notebooks as easily as with local ones.

> **Project status: 0.3.0 — source candidate in qualification.** Session names, consistent terminal choices, a management menu, managed/history summaries, confirmed stop-and-archive and shareable diagnostics extend the tested Linux workflows. CPython 3.11–3.14 and OpenSSH remain the support boundary. The published Conda package is still 0.2.0 until separate promotion; neither version is on PyPI. See [implementation, observed tests and pending qualification](devguide/30-03-implementation.md).

Start with the [public documentation](https://www.uibcdf.org/jupyhop/).
Its sources include the [quickstart](docs/quickstart.md), [compatibility matrix](docs/compatibility.md)
and [troubleshooting](docs/troubleshooting.md). Development instructions are in
[CONTRIBUTING](CONTRIBUTING.md); vulnerability reporting is in [SECURITY](SECURITY.md).
The guides also cover [remote preparation](docs/remote-setup.md),
[session identities/states](docs/sessions.md), [CLI JSON](docs/json-reference.md)
and [updating a client](docs/upgrading.md).
The [0.2.0 operational scope](devguide/22-02-stabilization.md) and
[acceptance evidence](devguide/23-02-stabilization-evidence.md) distinguish tested
workflows from unmeasured physical transitions and site policies.
The [physical home-client pilot](devguide/28-02-physical-client-pilot.md) now
confirms managed/manual access, same-kernel reconnection and concurrent sessions
through a real SSH gateway. Its usability findings inform the
[0.3.0 design baseline](devguide/29-03-session-ux-design.md) and
[implementation report](devguide/30-03-implementation.md). Those improvements
are not available in the older 0.2.0 package.
Version 0.2.0 is available on the [uibcdf Conda channel](https://anaconda.org/uibcdf/jupyhop)
for Linux. Distribution follows the shared UIBCDF build/test/staging/promotion
workflow; see [publication evidence](devguide/24-conda-publication.md).

## The problem

Remote Jupyter is already possible with SSH, but the ordinary workflow involves starting a server, arranging process persistence, finding its port and login details, setting up an SSH tunnel, and remembering how to reconnect. Doing this across multiple machines and clients adds friction.

**JupyHop's goal is to make the location of the browser independent of the location of the computation.** The Jupyter server, kernels, Python environments, data, and notebooks stay on the remote host. JupyHop takes care of the access workflow using SSH connections the user is already authorized to make.

## At a glance

With an existing authorized SSH alias and a discoverable Jupyter server:

```console
# Open an existing Jupyter server on an SSH-accessible machine
jupyhop open workstation

# Find supported current-user servers; discovery is always partial
jupyhop discover workstation
jupyhop list workstation

# Keep the tunnel attached and print a token-free login URL
jupyhop open workstation --no-browser
```

`open` opens the normal Jupyter login page. Enter your existing password/token.
Opening existing servers does not retrieve their credentials. Keep the command running.
Ctrl-C closes its tunnel, leaving the remote server alone. A terminal chooser
appears even for one ready candidate. Exact IDs or managed `--name` select
directly; scripts retain the one-candidate behavior and refuse ambiguity.
No JupyHop TOML configuration is required.

To launch a new owned server, select an existing remote Jupyter Python and
directory. The remote host needs `tmux` on its noninteractive SSH PATH:

```console
jupyhop start workstation --server-python /absolute/remote/env/bin/python --workdir '~/projects/analysis' --name analysis
jupyhop start workstation --name analysis-batch --no-open --json
jupyhop open workstation SESSION_ID
jupyhop status workstation SESSION_ID
jupyhop stop workstation SESSION_ID
```

`start` prompts privately for a new Jupyter session password. It crosses encrypted
SSH stdin; only an Argon2 password hash is retained in a private remote Jupyter
settings file. No password/token enters argv, ordinary JSON or diagnostics. Use
a strong session password rather than your SSH password. Scripts may supply one
line from a protected credential source with `--password-stdin`; no `--password`
argument exists. If a private prompt cannot hide input, it refuses safely.
`--no-open` returns verified launch information without creating
a local tunnel; otherwise the same attached browser/no-browser flow is used.

`discover`/`list` label verified owned servers as `managed` and preserve a stable
session ID. `open` accepts that exact ID or managed `--name`. `resume` is an alias
for open. Human `status HOST` shows a read-only summary of ready, stopped awaiting
archive, review and history records; `--history` lists bounded archived evidence.
Exact-UUID status and legacy status JSON retain interrupted-readiness reconciliation.

Terminal stop/archive can select by exact managed name or a numbered chooser;
the target is pinned to its UUID and revalidated. Stop's confirmation normally
offers both stop and archive, with `--keep-record` for stop-only use. Only a
confirmed stop proceeds to the existing inactivity guard/archive move, releasing
the name/slot while retaining evidence and notebooks. Uncertain/partial outcomes
report the phase and same-UUID recovery step.

Scripts retain exact UUID plus `--yes` and stop-only behavior; `--archive`
explicitly authorizes compound completion. Stop terminates all kernels and
computations of that server. Names are conveniences, not credentials/authority;
unmanaged IDs and PIDs cannot authorize stop. Discovered servers are never
adopted, stopped or restarted.

```console
jupyhop open workstation --name analysis
jupyhop resume workstation
jupyhop status workstation --history
jupyhop manage workstation
```

Manage reuses those same inventory/select/confirm/dispatch operations. An open
stays in the foreground; Ctrl-C returns to the menu, possibly requiring fresh
SSH authentication after its foreground master ends. Exit closes owned local
connections. No detached tunnel service is introduced.

Optional launch profiles and host preferences use TOML:

```toml
# ~/.config/jupyhop/config.toml (or --config FILE)
version = 1
[profiles.research]
server_python = "/absolute/remote/env/bin/python"
workdir = "~/projects/analysis"
[hosts.workstation-a]
profile = "research"
[hosts.workstation-b]
profile = "research"
```

Use an owned regular file without group/other write permission (`chmod 600` is
recommended). Host addresses, users, keys and jumps remain in OpenSSH config;
credentials are not accepted in JupyHop TOML. Profiles select an existing Python
and directory without activating, installing or modifying an environment.

```console
jupyhop start workstation-a --env research
jupyhop list workstation-a workstation-b --json
jupyhop list                   # all configured hosts
jupyhop open                   # configured hosts; choose on a terminal if ambiguous
jupyhop archive workstation-a SESSION_ID --yes
```

Explicit CLI Python/workdir values override the profile. Per-host
`remote_python` and `runtime_dirs` can specify a stdlib helper and additional
discovery paths; no Jupyter dependency is required in that helper.
`list` returns version-1 multi-host inventory with per-route errors. Its JSON
shape differs from the old single-host alias: use `discover HOST --json` for
the original single-host report. Scripts choose a route explicitly with
`open HOST ID` when multiple candidates exist.

After stopping a managed session, `archive` moves its inactive record/settings
and recovery files into a private archive, freeing its name and active-record
budget. It preserves evidence for possible orphaned kernels. It does not delete
scientific data or stop orphaned kernels; live or uncertain identities are refused.

A host such as `workstation` would be an existing alias in the user's `~/.ssh/config`; SSH can connect directly or via a jump host using `ProxyJump`.

## Use cases and scenarios

Existing-server access, diagnostics, managed launch/stop and same-live-kernel
reconnection, profiles and multi-host inventory ship through M5. Broader platform
and physical-network workflows remain bounded by the roadmap's acceptance gates.

### 1. Open a Jupyter server that is already running

A Jupyter server was launched manually in a terminal, a `tmux` session, or another environment. From a different computer, run `jupyhop open workstation`: JupyHop should discover supported current-user servers, establish an SSH tunnel, and open the chosen server in the local browser.

Discovery is *best-effort*: custom runtime directories, older server variants, and unusual authentication configurations may require explicit settings or a manual login. An incomplete search must be reported honestly.

### 2. Start a new Jupyter server without logging in interactively first

From a laptop, create a server on a remote workstation with `jupyhop start workstation`. The remote server should run under the authenticated SSH user's operating-system account, with Jupyter authentication preserved and without exposing a public Jupyter port.

### 3. Choose the remote Python environment and working directory

Launch Jupyter with an explicit existing Python and project directory on the **remote** host:

```console
jupyhop start workstation --server-python /absolute/remote/env/bin/python --workdir '~/projects/analysis'
```

The environment must already exist; it is not installed or activated by JupyHop.
Named `--env` profiles choose an executable/workdir from optional TOML. Server and kernel environments are
distinct concepts; JupyHop checks that kernel specifications are available.

### 4. Continue work from another computer

Start working on a remote notebook at the office, leave the Jupyter server running, and later connect from a laptop at home. The new client should locate and open the same server without needing the old client's port assignments or tunnel state.

**If the original kernel is still alive**, its in-memory objects and running computation remain available. Opening the notebook file alone does not guarantee recovering a kernel that has died.

### 5. Disconnect without stopping a long-running computation

Close the browser, shut down the local SSH tunnel, or lose the client network connection. A *properly supervised, remotely running* Jupyter server and its kernels should continue independently of the local connection. Reconnecting recreates the tunnel, not the computation.

This is **not** checkpointing: rebooting the remote host or losing the kernel ordinarily destroys in-memory state.

### 6. Reach an internal workstation through an SSH gateway

A laptop outside a private network can access a workstation through an existing SSH bastion:

```text
Laptop  --SSH-->  Gateway  --SSH-->  Workstation (Jupyter + kernels)
```

JupyHop should reuse the SSH alias and `ProxyJump` configuration; the gateway is a transport hop, not a required JupyHop service. No additional public Jupyter port is needed.

### 7. Connect directly between machines on the same local network

When two machines can communicate over LAN through SSH, JupyHop should work without forcing traffic through a gateway. Routing is determined by the **current client's OpenSSH configuration**, which may differ between home and office.

### 8. Use a gateway or login host as a Jupyter destination

The machine acting as an SSH gateway may itself be a permitted destination for a user-owned Jupyter server. JupyHop should support direct SSH access to it as well as forwarded access through it.

On HPC systems, interactive work on login nodes remains subject to site policy; resource-intensive kernels should use compute nodes allocated by the scheduler rather than running by default on the gateway.

### 9. Open sessions on several remote hosts simultaneously

Use separate browser tabs for Jupyter running on a workstation, a second workstation, and another SSH-accessible server. JupyHop should allocate local forwarding ports without collision and keep the servers and tunnels independently identifiable.

### 10. Run multiple Jupyter servers on a single remote machine

Different projects may use different Jupyter instances, environment profiles, or directories on the same host. JupyHop should list distinct instances, allow explicit selection, and avoid confusing one server with another because a port or display name was reused.

### 11. Reconnect from a new or replacement laptop

A new authorized client with working SSH access should be able to discover the remote user's servers and reconnect without restoring an old laptop's local JupyHop state. Managed session information belongs on the remote host; SSH configuration and any extra discovery settings may still need to be configured on the new client.

### 12. Keep different users' sessions separate

Members of a team can use JupyHop with their own Unix/SSH accounts, potentially on the same host. Discovery, process control, and session state must respect remote operating-system permissions. JupyHop does **not** grant new SSH access or provide cross-user sharing in the initial version.

### 13. Recover cleanly from ordinary failures

If a client sleeps, an SSH gateway becomes unavailable, the browser closes, the local port is occupied, or the remote server has exited, JupyHop should diagnose what happened without silently stopping another process or pretending that lost kernel state still exists.

A connection that fails is not proof that the remote server has stopped. Host reboot, server crash, changed authentication, and stale discovery files require explicit reconciliation or reauthentication.

### 14. Work without a graphical browser

A headless client should be able to use a documented `--no-browser` flow and obtain nonsecret connection information for use with an appropriate client. Authentication tokens must not leak through routine logs, diagnostics, or machine-readable output.

### 15. Diagnose remote Jupyter access

`jupyhop doctor workstation` diagnoses SSH access and the selected Python's
installed Jupyter packages, visible runtime directory and process managers.
It does not prove server readiness or supervise managed sessions. Discovery can
use a stdlib-only remote Python even when doctor reports no Jupyter packages in
that interpreter; the server may run in a different Conda environment.

## Where JupyHop can connect

| Client location | Jupyter destination | Intended connection |
| --- | --- | --- |
| Laptop outside a private network | Internal workstation | Existing SSH gateway / `ProxyJump` |
| Laptop outside a private network | SSH-accessible gateway itself | Direct SSH |
| Workstation on a LAN | Another SSH-accessible workstation | Direct SSH where configured |
| Workstation on a LAN | SSH-accessible login/gateway host | Direct SSH where permitted |
| Any authorized client | Several SSH-accessible hosts | Separate managed forwards |
| New client with authorized SSH access | A pre-existing remote user session | Rediscover and reconnect |

**Connectivity prerequisite:** the client must already have a working and authorized SSH path to the destination, with trusted host keys. Terminal commands support native OpenSSH password/passphrase prompts and keys/agent. Headless commands or explicit `--batch` require noninteractive authentication. Each invocation owns its private connection; SSH passwords stay in OpenSSH. Individual MFA variants remain untested. JupyHop does not automatically make machines behind NAT or firewalls reachable, establish a VPN, or bypass access restrictions.

## Managed vs. discovered Jupyter servers

| Capability | JupyHop-managed server | Existing/discovered server |
| --- | --- | --- |
| Discover and list | Implemented with verified ownership | Implemented, partial coverage |
| Open through SSH | Implemented | Implemented for verified IPv4 loopback / HTTP servers |
| Start with chosen Python/workdir | Implemented, private tmux launcher | Started outside JupyHop |
| Reconnect to a still-running server | Fresh login/tunnel; same surviving kernel verified across independent clients | Fresh login/tunnel; persistence belongs to its external launcher |
| Stop through JupyHop | Verified graceful stop by exact UUID, with confirmation | **Not allowed in MVP** |
| Archive inactive registry evidence / release name | Explicit verified move to private archive | **Not allowed** |
| Preserve kernel state after remote reboot | **Not possible by default** | **Not possible by default** |

JupyHop manages **the route**, creates owned servers, reconciles readiness and
observes process loss, gracefully stops verified identities and archives inactive
records without deleting recovery evidence.
JupyHop does not replace Jupyter's kernel manager or
make kernels persistent across crashes and reboots.

## Design principles

- **Lightweight and SSH-native:** no mandatory central JupyHop service, web portal, VPN, or JupyterHub deployment.
- **Existing identities:** reuse OpenSSH keys, aliases, host verification, and `ProxyJump`.
- **Compute stays remote:** do not copy scientific environments or data to the client merely to open a notebook.
- **Secure by default:** remote servers and local forwards bind to loopback; Jupyter authentication stays enabled.
- **Client-independent sessions:** reconnection does not rely on remembering a particular client's tunnel ports.
- **Explicit ownership:** only verified JupyHop-managed servers may be stopped through JupyHop.
- **Honest discovery:** incomplete searches and unsupported server setups must not be reported as definitive absence.
- **Minimal setup first:** common existing-server access should need no additional JupyHop configuration when SSH and remote prerequisites are already sufficient.
- **General-purpose:** no hard-coded organization-specific hostnames, networks, environments, or credentials.

## Architecture

```text
Local client
  JupyHop CLI + browser
     |
     +-- OpenSSH (direct or via ProxyJump) --> Remote host / authenticated user
                                               |-- Jupyter Server
                                               |     +-- kernels and notebooks
                                               |-- optional user-level process manager
                                               +-- managed session metadata
```

M2/M3 read supported runtime metadata, verify current-account process/socket
ownership and HTTP/authentication behavior, create an owned loopback forward,
then open Jupyter's normal login page. Read-only probes travel through SSH
stdin; no remote JupyHop package installation is needed. Managed start writes
an immutable versioned runner and private state for its new session, then uses
a dedicated tmux socket. Client upgrades do not rewrite running launchers or
scientific environments. No central daemon is required.

See the [architecture](devguide/02-architecture.md), [session and authentication contracts](devguide/09-session-lifecycle-and-auth.md), and [remote runtime design](devguide/10-remote-runtime-and-protocol.md).

## How JupyHop differs from JupyterHub

[JupyterHub](https://jupyterhub.readthedocs.io/) is a mature centralized multi-user Jupyter deployment platform, with authentication, routing, and configurable spawning.

JupyHop is **not a JupyterHub fork or a replacement for managed multi-user deployments**. Its niche is individual developers and small research groups who *already have authorized SSH access* to remote computers and want a simpler way to access and manage their own sessions. Organization-wide user provisioning, centralized policies, collaboration across accounts, and a shared browser portal are outside the initial scope.

JupyHop is an independent project, not affiliated with or endorsed by Project Jupyter.

## Security and limitations

Jupyter offers code execution on the machine hosting a kernel, so session discovery, SSH host verification, authentication, process ownership, and credential handling must be designed and tested carefully.

JupyHop will not disable SSH host-key checking or Jupyter authentication to make a connection work. It must avoid logging credentials, run under the authorized OS account, never stop unowned servers, and keep remote Jupyter endpoints private by default. Any credential storage requires a reviewed security policy.

**Important limits:**

- No automatic access to a machine without an authorized SSH route.
- No guarantee of discovering every manually launched or custom-configured server.
- No automatic recreation of live Python objects or kernels after a remote crash/reboot.
- No control of other users' servers or shared-team authentication in the initial scope.
- Slurm/HPC compute-node launching is a **future, optional backend**, not an MVP feature.
- Other platforms, unusual proxy configurations, custom HTTPS and IPv6 setups require compatibility testing before being advertised as supported.

See [security and reliability](devguide/04-security-and-reliability.md), [discovery and connectivity](devguide/11-discovery-and-connectivity.md), and [scenario acceptance matrix](devguide/08-scenarios-and-acceptance.md).

## Development roadmap

M0–M6 acceptance is recorded for the documented support boundary, including
hosted GitHub CI. Version 0.2.0 establishes the operational baseline; the 0.3.0
source candidate adds the post-pilot session/diagnostic usability increment.
The full roadmap is:

1. **M0 — Validate design assumptions:** discovery, auth handoff, process managers, tunnel lifetime, and remote helper.
2. **M1 — SSH foundations:** host aliases, ProxyJump, remote diagnostics.
3. **M2 — Discover and open existing servers:** the first immediately useful workflow.
4. **M3 — Managed launching:** start Jupyter servers with secure endpoints.
5. **M4 — Persistent lifecycle:** reconnect across clients, stop owned sessions, handle stale state.
6. **M5 — Scientific and multi-host workflows:** environments, directories, multiple servers and users.
7. **M6 — Public beta and release:** integration/security tests, packaging, documentation.
8. **M7 — Optional extensions:** Slurm, enhanced discovery, additional front ends.

For detailed milestones, acceptance criteria, design decisions, and known constraints, consult the [development guide](devguide/README.md) and [roadmap](devguide/06-roadmap.md).

## Installation

Use Linux, Python 3.11–3.14 and the OpenSSH client.
For the published client:

This channel command currently installs the older 0.2.0 interface. Use reviewed
0.3.0 source/wheel below for the new menu/names until its separate promotion.

```console
mamba create -n jupyhop -c uibcdf -c conda-forge python=3.14 jupyhop=0.2.0
mamba activate jupyhop
jupyhop --version
```

Conda includes OpenSSH. Follow the [quickstart](docs/quickstart.md); see
[remote preparation](docs/remote-setup.md) for the Jupyter environment and
[updating](docs/upgrading.md) for an existing client. Version 0.2.0 is not on PyPI.

For development from a source checkout:

```console
python -m pip install --no-deps -e .
jupyhop --help
jupyhop doctor workstation
jupyhop doctor workstation --remote-python /absolute/remote/environment/bin/python --json
jupyhop discover workstation --json
jupyhop open workstation
jupyhop open workstation SERVER_ID --no-browser
```

The client has **no Python runtime dependencies** and does not need local
Jupyter. OpenSSH resolves the existing alias, remote user, keys, `Include`,
`Match` and `ProxyJump`. Doctor uses strict host-key checking and native SSH authentication:
first verify access with `ssh workstation`, establish host trust through the
normal SSH workflow, then use a terminal for native password/passphrase prompts
or unlock keys in your agent. Scripts use `--batch` with noninteractive SSH access.
JupyHop does not read/cache SSH passwords or edit SSH configuration.
`--ssh-config PATH` passes a specific file to OpenSSH; `--timeout SECONDS` bounds each probe/
network startup (default 20), while `--ssh-auth-timeout SECONDS` bounds terminal
authentication (default 120). Each live private connection authenticates once;
manage can authenticate again after explicitly closing an open/master with Ctrl-C.

The selected remote Python must be >=3.11. Doctor reports its installed Jupyter
Server/core versions, the runtime directory visible to that interpreter, the
remote Unix identity, and process-manager availability. Missing Jupyter packages
produce a diagnostic and exit 4; choose the existing environment using its
absolute Python path. No remote package, helper, server or tunnel is installed
or started by doctor. Environment activation is unnecessary; doctor does not
list running servers or prove their absence/readiness.
`doctor --report` adds normalized local/selected-remote support context with
identities, paths and credentials excluded; review before sharing. It uploads
nothing. See [Diagnostics](docs/diagnostics.md) for the optional notebook API and
a copyable stdlib cell that needs no remote JupyHop installation.

Discovery uses Jupyter's runtime path when available and standard Linux defaults
otherwise. For custom or separate environment paths, explicitly extend coverage:

```console
jupyhop discover workstation --runtime-dir '~/custom/runtime'
jupyhop discover workstation --remote-python /env/one/bin/python --remote-python /env/two/bin/python
```

`--runtime-dir` and discovery/open `--remote-python` are repeatable. No process
scan or Conda inventory is attempted. Discovery always reports `complete: false`;
a zero-result search is not proof that no servers exist. Runtime directories and
metadata must belong to the remote account, be private (0700 / 0600), and use
paths without symlinks. Metadata is never modified or deleted.

The initial tested server stack is Jupyter Server 2.21.1 / JupyterLab 4.6.4.
Supported candidates must own a `127.0.0.1` TCP listener and expose recognizable
Jupyter 2 API/auth behavior. Simple ASCII custom base paths such as `/science/`
work, including WebSockets. Public/wildcard listeners, IPv6-only servers, HTTPS,
Unix sockets, older `nbserver` metadata and unknown authentication/proxy setups
are rejected or labeled unsupported. TLS verification is never disabled.

`open` prints a token-free login URL and owns one fresh foreground SSH connection.
Keep it running; Ctrl-C, SIGTERM or terminal hangup closes only that connection.
Repeated opens create independent tunnels and ports. Browser absence falls back
to the printed URL on this client. There is no detached tunnel daemon or shared
connection reuse. The original launcher remains responsible for server/kernel
persistence. See [the M2 contract](devguide/16-m2-existing-servers.md).

Managed launching requires an existing Python >=3.11 with Jupyter Server >=2.20,<3,
available kernels, `tmux` and a readable stable Linux machine ID. JupyterLab is
enabled when installed; otherwise the server provides its normal server/API
view. `--server-python` selects the server environment; `--remote-python` selects
the helper and is the server default if no separate path is supplied. Neither
path depends on shell activation. Native ephemeral-port reporting requires Server
2.20 or later; 2.21.1 is the recommended tested stack. Older existing servers are
validated separately; see [compatibility](docs/compatibility.md).
The helper/server use isolated Python imports: their required packages must be
available in the chosen environment. See [import-mode diagnostics](docs/environments.md#match-the-interpreters-import-mode)
for user-site or PYTHONPATH-only installations.
Relative workdirs resolve against remote HOME;
`~` means the remote account, and workdir symlinks are canonicalized.

State lives under `$XDG_STATE_HOME/jupyhop/hosts/<host-account-scope>/sessions/ID`
(default `~/.local/state`). Host scope hashes the Linux machine ID and account
UID so shared HOME directories do not merge different hosts. State directories
are private 0700; files are 0600. Registry schema 1.0 is separate from wire
protocols (start 1.2, status/stop 1.3, archive 1.4, read-only managed/history
inventory 1.5, discovery 1.6). Incompatible state
is refused without automatic migration. No existing
Jupyter configuration, scientific environment or SSH config is rewritten.

Failed or interrupted starts may leave a running server and a recoverable launch
record. Note the request ID and run `status HOST ID` or `discover` before retrying.
Names stay reserved and active records are retained (maximum 128) until explicit
archive. `archive HOST ID` needs confirmation or `--yes`; it moves only the
inactive private session directory to `archive/ID` under the same host/account
registry. Repeated archive is safe. Old UUIDs are not reused, and archived data is
retained with its private permissions. No automatic deletion is attempted.
A request with no verified PID may
remain `starting`; this is unconfirmed intent, not proof of a running process.

`status` distinguishes `ready`, `starting`, `stopping`, `stopped`, `stale`, `failed`
and `unreachable`. Reboot identity changes and missing/replaced processes are
reported as stale; no kernel restoration or automatic restart is attempted.
Private tmux and live-kernel continuity are tested after closing browser, tunnel
and all first-client connections. Site last-logout/cgroup/linger policy still
applies: JupyHop never changes it and cannot guarantee survival if the OS kills
the user workload. Physical host reboot/last-login policy was not tested.

Safe stop requires Linux pidfd support (kernel >=5.3), exposed by the helper's
Python or native libc. Python APIs are preferred; builds omitting them use named
libc wrappers through stdlib ctypes. If unavailable, stop refuses safely; select
a capable helper with `--remote-python`. The descriptor is pinned before
identity/provenance checks, and receives only graceful SIGTERM. There is no
PID-only signal, tmux kill, automatic SIGKILL or automatic restart. Stop timeout
or SSH interruption leaves its outcome unknown: check status before retrying.
See [the lifecycle contract](devguide/18-m4-lifecycle.md) and
[M5 profiles, inventory and archival evidence](devguide/19-m5-scientific-workflows.md).

Exit codes: 0 checks passed; 2 invalid input; 3 SSH/access/timeout failure;
4 missing remote prerequisites or failed Python probe; 5 invalid/incompatible
probe output; 6 no verified candidate (partial search); 7 ambiguous/invalid
selection; 8 forwarding failure; 11 lifecycle refusal; 12 unconfirmed/failed
managed launch; 13 unconfirmed/pending lifecycle request; 14 partially failed
multi-host inventory; 130 interrupted. `list` returns 0 when every selected host
was inspected (even with no ready servers), 14 when some hosts failed, and 3
when all failed. Discovery remains partial. Managed-start transport failure also uses 12
because the remote write/process outcome may be unknown.
`--json` emits nonsecret structured results;
errors go to stderr. Transport errors leave remote session state unknown.
An explicit ID absent from a single-host open search returns 6; hostless open
selection failures, including zero fleet candidates, return 7. A successful
status observation can return 0 for stale/failed/unreachable entries: inspect
their states. The [JSON reference](docs/json-reference.md) describes each CLI
result shape separately from the internal remote wire protocol.

Automatic deletion of archived state, profile activation hooks, custom supervision
backends, other operating systems and non-POSIX remote login shells are untested
or unimplemented. Config v1 permits up to 16 hosts and 32 profiles; sequential
inventory uses a deadline per host. Scientific environments that require custom
activation scripts must be prepared outside JupyHop. Available notebook kernels
remain Jupyter's responsibility.

## Contributing

The project is in early development. Development tools can be installed with
`mamba install -c conda-forge pytest ruff mypy python-build setuptools` or
`python -m pip install -e '.[dev]'`. Experimental Jupyter dependencies are separate
in `.[experiments]`; see the [M0 report](devguide/13-m0-validation.md).

```console
pytest                         # isolated unit tests; SSH integration skipped
pytest --run-integration       # disposable loopback sshd, never real hosts
ruff check .
ruff format --check .
mypy
python -m build --no-isolation
python -m experiments.package_smoke
python -m experiments.browser_smoke  # optional Chrome + JupyterLab acceptance
python -m experiments.browser_smoke --managed --reconnect
python -m experiments.m4_reconnect
# Optional real-account acceptance: see experiments/m5_accounts.md
```

Integration requires a non-root Unix user, OpenSSH server/client, an existing
`/run/sshd`, permission to bind loopback sockets, tmux, and Jupyter Server/kernels
in the test interpreter. It creates temporary keys/configuration and never uses your
SSH hosts; their HOME/runtime are isolated too. See
[test evidence and limits](devguide/18-m4-lifecycle.md).
Suggestions and research-computing use cases remain welcome.

Developed by the [Computational Biology and Drug Design Research Unit (UIBCDF)](https://www.uibcdf.org/).

## License

JupyHop is distributed under the [MIT License](LICENSE).
