# JupyHop

**Your lightweight hub for remote Jupyter sessions.**

JupyHop is an open-source project for **discovering, opening, launching, managing, and reconnecting to remote Jupyter sessions over SSH**—without requiring a central JupyterHub deployment.

It is designed for researchers, data scientists, developers, and small teams who already have SSH access to workstations or servers and want to work with their remote notebooks as easily as with local ones.

> **Project status: early design.** The workflows, commands, and capabilities described below are **planned, not yet implemented**. JupyHop is not currently installable or published on PyPI. See the [development guide](devguide/README.md) for specifications and acceptance criteria.

## The problem

Remote Jupyter is already possible with SSH, but the ordinary workflow involves starting a server, arranging process persistence, finding its port and login details, setting up an SSH tunnel, and remembering how to reconnect. Doing this across multiple machines and clients adds friction.

**JupyHop's goal is to make the location of the browser independent of the location of the computation.** The Jupyter server, kernels, Python environments, data, and notebooks stay on the remote host. JupyHop takes care of the access workflow using SSH connections the user is already authorized to make.

## At a glance: intended experience

A few examples of the proposed CLI:

```console
# Open an existing Jupyter server on an SSH-accessible machine
jupyhop open workstation

# Find available servers (including supported manually started servers)
jupyhop discover workstation
jupyhop list workstation

# Start a JupyHop-managed server in a remote Python environment and directory
jupyhop start workstation --env research --workdir '~/projects/analysis' --name analysis

# Reconnect or inspect a particular managed session
jupyhop open workstation analysis
jupyhop status workstation analysis

# Stop only a JupyHop-managed session
jupyhop stop workstation analysis
```

**These commands are illustrative and subject to change.** If several servers match, JupyHop should ask the user to select one (or require an explicit identifier in noninteractive mode), rather than guessing. A manually started server can be opened when safely discoverable, but cannot automatically be stopped by JupyHop.

A host such as `workstation` would be an existing alias in the user's `~/.ssh/config`; SSH can connect directly or via a jump host using `ProxyJump`.

## Use cases and scenarios

The following are **intended workflows**, not a list of shipped features. Unless noted otherwise, they are part of the planned core experience.

### 1. Open a Jupyter server that is already running

A Jupyter server was launched manually in a terminal, a `tmux` session, or another environment. From a different computer, run `jupyhop open workstation`: JupyHop should discover supported current-user servers, establish an SSH tunnel, and open the chosen server in the local browser.

Discovery is *best-effort*: custom runtime directories, older server variants, and unusual authentication configurations may require explicit settings or a manual login. An incomplete search must be reported honestly.

### 2. Start a new Jupyter server without logging in interactively first

From a laptop, create a server on a remote workstation with `jupyhop start workstation`. The remote server should run under the authenticated SSH user's operating-system account, with Jupyter authentication preserved and without exposing a public Jupyter port.

### 3. Choose the remote Python environment and working directory

Launch Jupyter with a selected environment profile and a project directory on the **remote** host:

```console
jupyhop start workstation --env research --workdir '~/projects/analysis'
```

The selected environment must exist on the remote machine; the Jupyter server's environment and available notebook kernels are distinct concepts.

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

A planned `jupyhop doctor workstation` command should help distinguish SSH failures, missing remote prerequisites, unsupported Jupyter runtime locations, incompatible helper versions, and tunnel problems, with actionable diagnostics.

## Where JupyHop can connect

| Client location | Jupyter destination | Intended connection |
| --- | --- | --- |
| Laptop outside a private network | Internal workstation | Existing SSH gateway / `ProxyJump` |
| Laptop outside a private network | SSH-accessible gateway itself | Direct SSH |
| Workstation on a LAN | Another SSH-accessible workstation | Direct SSH where configured |
| Workstation on a LAN | SSH-accessible login/gateway host | Direct SSH where permitted |
| Any authorized client | Several SSH-accessible hosts | Separate managed forwards |
| New client with authorized SSH access | A pre-existing remote user session | Rediscover and reconnect |

**Connectivity prerequisite:** the client must already have a working and authorized SSH path to the destination. JupyHop does not automatically make machines behind NAT or firewalls reachable, establish a VPN, or bypass access restrictions.

## Managed vs. discovered Jupyter servers

| Capability | JupyHop-managed server | Existing/discovered server |
| --- | --- | --- |
| Discover and list | Planned | Planned, best-effort |
| Open through SSH | Planned | Planned, subject to verification/authentication |
| Start with chosen environment/workdir | Planned | Started outside JupyHop |
| Reconnect to a still-running server | Planned | Planned when accessible |
| Stop through JupyHop | Planned | **Not allowed in MVP** |
| Preserve kernel state after remote reboot | **Not possible by default** | **Not possible by default** |

JupyHop manages **the route to a server**, **the remote server process when it created it**, and **the session registry for its own servers**. It does not replace the Jupyter Server kernel manager or make notebook kernels intrinsically persistent across crashes and reboots.

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

## Proposed architecture

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

JupyHop should discover or invoke current-user remote Jupyter processes, validate their endpoints, create a local loopback SSH forward, and open an authenticated browser session. A small remote helper may be needed for some lifecycle operations; its deployment and protocol are still under evaluation. Remote-managed sessions must survive client disconnection without requiring a central JupyHop daemon.

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

The planned dependency-ordered stages are:

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

JupyHop is **not yet published on PyPI**, and there is no supported installation process. The command examples in this README describe planned behavior.

## Contributing

The project is currently in its design stage. Suggestions, research computing workflows, reports of missing use cases, and comparisons with existing tools are welcome as design feedback.

Developed by the [Computational Biology and Drug Design Research Unit (UIBCDF)](https://www.uibcdf.org/).

## License

JupyHop is distributed under the [MIT License](LICENSE).
