---
myst:
  html_meta:
    description: "Save optional JupyHop launch profiles and inspect several SSH hosts. Reuse remote Python paths and project directories without storing credentials."
    "property=og:description": "Save optional JupyHop launch profiles and inspect several SSH hosts. Reuse remote Python paths and project directories without storing credentials."
---

# Profiles and multiple hosts

Basic `jupyhop open workstation` needs no JupyHop configuration file. Profiles
become useful when you repeatedly choose a remote Python, project directory or
custom discovery path.

## Inspect several machines without extra configuration

If both SSH aliases work, run in your **local terminal**:

```console
jupyhop list workstation-a workstation-b
```

Each route keeps its own results and errors. This read-only inventory needs no
TOML file. To work on two servers at once, open them in separate local terminals;
each owns an independent tunnel. The sections below add reusable settings only
when you want them.

## Create an optional config

The default path is `~/.config/jupyhop/config.toml`, or
`$XDG_CONFIG_HOME/jupyhop/config.toml` when that variable is set. Select an
alternate file with the per-command `--config FILE` option.

```toml
version = 1

[profiles.research]
server_python = "/opt/conda/envs/analysis/bin/python"
workdir = "~/projects/analysis"

[hosts.workstation-a]
profile = "research"
remote_python = "python3"

[hosts.workstation-b]
profile = "research"
```

Create this file on your **local client**. Replace example paths with existing
remote paths; the profile must be valid on each host that uses it. The host names
are existing OpenSSH aliases. Keep routing, users, addresses and keys in SSH configuration;
passwords, tokens, shell commands and activation hooks are not TOML fields.

The config must be your regular, single-link file, at most 64 KiB, without a
final symlink or group/other write permission. Mode 0600 is recommended. An absent
default file is optional; an explicit missing file or invalid config is an error
before SSH access. Unknown fields and unsupported schema versions are refused.

Place connection/application options after the command name, for example
`jupyhop discover workstation --config /path/to/config.toml`. A profile requires
`server_python`; its optional `workdir` defaults to the remote home. A host entry
can be empty if all defaults are suitable. Profile/host names are case-sensitive.

Aliases containing dots need quoted TOML keys; otherwise TOML creates nested
tables that JupyHop refuses:

```toml
version = 1

[hosts."workstation.example.org"]
remote_python = "/opt/conda/envs/analysis/bin/python"
```

The corresponding alias must already work in OpenSSH. CLI hosts use letters,
digits, underscores, dots and hyphens, starting with a letter, digit or underscore.
Use an alias instead of `user@host`, a URL or an IPv6 literal; set User/HostName
in OpenSSH config.

## Launch preferences and overrides

After creating that config, run one of these in your **local terminal**:

```console
jupyhop start workstation-a --env research
jupyhop start workstation-a --env research \
    --workdir '~/projects/other'
```

`--env research` chooses the `profiles.research` entry. It is not a Conda activation
command. Each selected Python/project must already exist remotely.

| Setting | Selection order |
| --- | --- |
| Launch profile | Explicit `--env`, then the host's default `profile` |
| Server Python/workdir | Explicit CLI value, then selected profile, then launch defaults |
| Helper Python | Explicit `--remote-python`, then host `remote_python`, then `python3` |
| Extra runtime paths | CLI `--runtime-dir` paths merged with the host's `runtime_dirs` |

By default the server uses the selected helper Python, and the working directory
is the remote home. Workdir choices affect new launches, not an existing server.
The configuration allows up to 32 profiles, 16 hosts and 16 merged extra runtime
paths. These limits bound client work; discovery remains partial.

Discovery/open/list accept at most eight selected helper interpreters. Repeating
`--remote-python` replaces the host's helper preference; it does not add the
default `python3` automatically. Runtime paths must be absolute remote paths or
`~/...`, without `..` components. Local shell variables and `~otheruser` are not
remote-path expansion features.

## Inventory several routes

```console
jupyhop list workstation-a workstation-b
jupyhop list workstation-a workstation-b --json
jupyhop list
```

Without aliases, `list` uses the hosts in your JupyHop TOML. It does not enumerate
every SSH configuration entry. Results retain each route's success or error so a
failed host does not hide a successful one.

Inventory visits routes sequentially with per-operation deadlines; `--timeout`
is not a total fleet deadline. Password authentication may prompt separately for
each route. Duplicate aliases to the same host/account can produce separate
route entries and an open-selection ambiguity; choose `open HOST ID` explicitly.

The same remote host/account can be reached through different configured routes;
managed UUIDs belong to its remote registry. Separate hosts or Unix accounts have
separate authorization scopes. Local configuration is not an authoritative record
of running servers.

## Open from configured hosts

```console
jupyhop open
jupyhop open workstation-a SESSION_ID
```

Hostless open searches configured hosts and lets a terminal select when needed.
Scripts choose an explicit route and exact ID. Open a new terminal invocation for
each attached forward when working on several servers simultaneously.

**Next:** [Choose another notebook kernel](environments.md),
[automate inventory with JSON](scripting.md), or [return to managed sessions](managed-sessions.md).
