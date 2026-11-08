# 01 — Product scope

## The problem

SSH tunnels support remote Jupyter, but starting servers, selecting ports, retaining session state, accessing token-protected URLs, and reconnecting from other computers are repetitive and error-prone.

## Intended users

- Individual researchers or developers with an SSH-accessible Linux workstation.
- Small scientific groups with multiple independent workstations, per-user OS accounts and an SSH bastion.
- Researchers using different Python environments and, later, HPC schedulers.

## Primary user journeys

| ID | User story | Expected result |
| --- | --- | --- |
| U1 | Launch on a remote host | Jupyter starts under the authenticated remote OS account |
| U2 | Close the laptop or SSH connection | Kernel and server stay running |
| U3 | Connect from another authorized client | The same managed remote session is discoverable and can be opened |
| U4 | Work with several sessions | Select a stable session ID/name, not a remembered port |
| U5 | Reach a host via bastion | Existing SSH ProxyJump configuration is honored |
| U6 | Open sessions on two hosts at once | Local forwards do not collide |
| U7 | Select a scientific environment | Launch Jupyter using an explicit remote environment/command |
| U8 | Lose connectivity | Clear recovery behavior, no unexpected session termination |
| U9 | Stop a session | Only the selected, owned session is stopped |

## MVP scope

A CLI with `start`, `list`, `open`, `status`, and `stop` operations; SSH aliases including ProxyJump; owned and persistent remote sessions; local SSH forwarding; and browser opening. All lifecycle operations concern **JupyHop-managed sessions** initially.

## Non-goals for MVP

- A multiuser web portal, central identity provider, or JupyterHub clone.
- Automatic discovery/control of arbitrary manually launched Jupyter processes.
- Cross-account session sharing, account provisioning, or administrator privileges.
- A VPN or bypass of institutional network access policies.
- Installation or modification of research environments.
- Slurm, Kubernetes, containers, or remote GPU allocation in the first release.
- Exposure of remote Jupyter to public IP interfaces.

## Success criteria

A fresh client can reconnect to an existing owned remote session without knowing a remote port. One broken tunnel does not terminate the remote session. Two users on the same host have isolated session state. No passwords/tokens leak into logs or public documentation.

## Out-of-scope future options

Slurm launcher, kernel selection UX, unmanaged session discovery, optional web front end, and organization-managed profiles. These require distinct design and security reviews.
