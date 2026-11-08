# JupyHop

**Your lightweight hub for remote Jupyter sessions.**

JupyHop is an open-source project designed to make it easy to **launch, discover, manage, and reconnect to Jupyter sessions on remote machines over SSH**, without deploying a central JupyterHub service.

> **Status: early design.** JupyHop is not yet a functional or installable application. All CLI examples below illustrate intended behavior, not implemented commands.

## Motivation

Researchers and developers frequently run notebooks on remote Linux workstations, GPU servers, or HPC systems while working from laptops, home computers, or other machines. SSH port forwarding makes remote Jupyter access possible, but choosing ports, managing processes, finding active sessions, and reconnecting after interruptions can be tedious.

JupyHop aims to make these everyday workflows simple while keeping notebooks, data, kernels, and Python environments on their existing hosts.

## Intended experience

```console
jupyhop start workstation --env research --workdir '~/projects/research'
jupyhop list
jupyhop open workstation
jupyhop stop workstation
```

These commands are **proposals**, not a currently supported interface. A host such as `workstation` would refer to an existing alias in `~/.ssh/config`, potentially using `ProxyJump` to reach a host behind an SSH bastion.

## Design principles

- **Lightweight:** no mandatory central service, daemon, VPN, or web portal.
- **SSH-native:** reuse OpenSSH configuration, authentication, and jump hosts.
- **Remote execution:** leave kernels, environments, notebooks, and data where they belong.
- **Persistent sessions:** disconnect one client and reconnect later from another.
- **Discoverable sessions:** find managed sessions and, where supported, existing Jupyter servers accessible to the authenticated remote user.
- **Automatic forwarding:** select free local ports rather than relying on fixed forwarding ranges.
- **Multi-host workflows:** manage independent machines through one consistent interface.
- **Extensibility:** accommodate different process managers and eventually schedulers such as Slurm.
- **Portable configuration:** no hard-coded institution-specific hosts, networks, or credentials.

## Proposed architecture

An initial client-side CLI would use SSH to invoke a small remote helper or a set of remote commands. That component would start, identify, and manage Jupyter Server instances for the current operating-system user. The CLI would establish authenticated SSH forwarding to the selected instance and open the corresponding local browser URL.

A user-level service manager could keep remote sessions alive independently of the connecting SSH client. The process manager, session registry, protocol, and exact command syntax are still design decisions.

The initial architecture does **not** require a permanently running central JupyHop server.

## Relationship to JupyterHub

[JupyterHub](https://jupyterhub.readthedocs.io/) provides central authentication, routing, and user server spawning for multi-user Jupyter deployments.

JupyHop does not aim to reimplement JupyterHub. It targets individuals and small research teams who **already have SSH access** and want lightweight management of their own remote sessions without operating a Hub. For institution-wide identity management, shared web access, or large managed deployments, JupyterHub may be preferable.

JupyHop is independent of, and not endorsed by, Project Jupyter.

## Security

Because Jupyter provides code execution on the remote machine, the intended implementation will:

- Rely on established SSH authentication and per-user operating-system permissions.
- Bind remote Jupyter servers to loopback by default and access them through SSH forwarding.
- Preserve Jupyter Server authentication; never disable it to simplify tunneling.
- Avoid shared privileged execution accounts.
- Never log or expose tokens, passwords, private keys, and secrets; any credential persistence must follow the reviewed security policy and restricted permissions described in the development guide.
- Store local host configuration outside the source repository, with sanitized examples.

The security design must be reviewed and tested before recommending production deployments.

## Roadmap (proposed)

1. **Design baseline:** specify security, session lifetimes, discovery, CLI behavior and test scenarios.
2. **SSH foundations:** use OpenSSH configuration and diagnose direct/ProxyJump access.
3. **Existing sessions:** discover and open an authorized manually started Jupyter Server over SSH.
4. **Managed sessions:** launch new remote Jupyter Servers without exposing their ports publicly.
5. **Persistence:** manage owned servers, reconnect from other authorized clients and verify live kernel continuity.
6. **Scientific workflows:** support environment profiles, project directories and multiple hosts.
7. **Public beta:** complete compatibility and security testing, documentation and packaging.
8. **Optional extensions:** evaluate Slurm, enhanced discovery or an interface without recreating JupyterHub.

See the [detailed development roadmap](devguide/06-roadmap.md) and [scenario acceptance matrix](devguide/08-scenarios-and-acceptance.md). These are plans, not currently shipping features.

## Installation

JupyHop has **not been published to PyPI**, and there is currently no supported installation procedure.

## Development plan

The proposed architecture, CLI contract, security model, test strategy, and milestone roadmap are documented in the [development guide](devguide/README.md).

## Contributing

JupyHop is in the early design phase. Use cases, architectural feedback, and comparisons with existing tools will be valuable as the project develops.

Developed by the [Computational Biology and Drug Design Research Unit (UIBCDF)](https://www.uibcdf.org/).

## License

JupyHop is distributed under the [MIT License](LICENSE), following the licensing approach of MolSysMT and MolSysViewer.
