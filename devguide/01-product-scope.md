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
| U9 | Stop a session | Only the selected, JupyHop-managed session is stopped |
| U10 | Open a manually started Jupyter Server | Discover a verified current-user server and open it through a secure tunnel without adopting ownership |
| U11 | Work in a project directory | Start a managed server in a validated remote working directory |
| U12 | Access a lab machine from within/outside its LAN | Honor route selection supplied by the client's OpenSSH configuration |

## MVP scope

A CLI with `start`, `list`, `open`, `status`, and `stop` operations; SSH aliases including ProxyJump; **best-effort discovery and opening of existing authorized current-user Jupyter servers**; owned persistent remote sessions; local SSH forwarding; and browser opening. **Only JupyHop-managed sessions may be stopped.** Managed-session persistence is independent of the client connection but not guaranteed across remote host reboots. See [08](08-scenarios-and-acceptance.md) and [09](09-session-lifecycle-and-auth.md).

## Non-goals for MVP

- A multiuser web portal, central identity provider, or JupyterHub clone.
- Exhaustive discovery of arbitrary Jupyter processes, cross-user discovery, or lifecycle control of unmanaged servers.
- Cross-account session sharing, account provisioning, or administrator privileges.
- A VPN or bypass of institutional network access policies.
- Installation or modification of research environments.
- Slurm, Kubernetes, containers, or remote GPU allocation in the first release.
- Exposure of remote Jupyter to public IP interfaces.

## Usability and setup requirement

With an existing working SSH alias and an authorized discoverable remote server, `jupyhop open host` should require no additional JupyHop config in the common case. Other scenarios may need explicit discovery directories, launcher profiles or supported remote helper bootstrap. The CLI must distinguish empty discovery from **incomplete** discovery. See [12](12-user-experience.md).

## Success criteria

A fresh client can open an existing discoverable current-user Jupyter server and reconnect to an existing managed remote session without knowing a remote port. One broken tunnel does not terminate the remote session. Two users on the same host have isolated session state. No passwords/tokens leak into logs or public documentation.

## Out-of-scope future options

Slurm launcher, advanced/universal unmanaged server discovery or adoption, kernel selection UX, optional web front end, and organization-managed profiles. **Basic best-effort discovery/opening of authorized unmanaged Jupyter Server instances is in the MVP (M2).** These require distinct design and security reviews.
