# Session identities, states and storage

Use `discover` or `list` to find servers, and `status` to inspect managed records.
They answer different questions: discovery returns verified endpoints and
diagnostics from known paths; status observes the managed registry, including
records whose processes have stopped.

```console
jupyhop discover workstation
jupyhop list workstation
jupyhop status workstation
jupyhop status workstation SESSION_ID --json
```

## Which identifier to use

| Value | Meaning and use |
| --- | --- |
| Managed `id` | A 32-character lowercase hexadecimal UUID, printed without hyphens; use the exact value for open/status/stop/archive on that host/account |
| Unmanaged `id` | A 24-character hexadecimal observation ID from discovery; use it for open while that endpoint remains verified |
| `name` | A managed display name; it cannot select a session for open or lifecycle actions |
| `observed_id` | Endpoint observation identity; it is not lifecycle authority |
| PID or port | Diagnostic information; neither selects or authorizes a session |

`SESSION_ID` and `SERVER_ID` in examples are placeholders for the actual printed
`id`. A managed UUID belongs to the remote host/account, independent of its SSH
alias or local forwarding port. It remains the same when another authorized
client opens that surviving session. After a server restart, rediscover an
unmanaged server instead of assuming an old observation ID still identifies it.

Managed names contain 1–64 ASCII letters, digits, underscores, dots or hyphens,
starting with a letter or digit. Names remain reserved until explicit archive,
including after stop. A new session reusing an archived name has a new UUID.

## Interpret an observed state

Only `ready` candidates can be opened. A state describes the observed server or
record; it does not prove that every notebook kernel is healthy.

One managed server can have several notebooks and kernels. Its managed UUID
remains the same when a notebook kernel starts, restarts or stops. Notebook
session IDs and kernel IDs belong to Jupyter; they are not selectors for
JupyHop lifecycle actions. Stopping that server affects all its kernels.

| State | Meaning | Next step |
| --- | --- | --- |
| `ready` | A supported live server endpoint and its ownership were verified | Open it, authenticate and select the existing notebook/kernel |
| `starting` | Managed launch intent exists, but readiness is unconfirmed; a verified PID may be absent | Query status and discover before retrying start |
| `stopping` | Stop intent is recorded and the process has not yet been observed gone | Query status again; a repeated stop still revalidates the exact UUID |
| `stopped` | The managed server process is gone after recorded stop intent | Archive its inactive records when appropriate; memory recovery is unavailable |
| `stale` | Boot/process identity changed, or the original process disappeared | Preserve evidence; do not infer that a replacement process has the old kernel |
| `failed` | Managed launch/runner failure is recorded | Inspect the diagnostic and private evidence before deciding whether to retry |
| `unreachable` | The endpoint or process identity could not be verified | Check prerequisites and connectivity; this does not establish process death |
| `unsupported` | Discovery found metadata/endpoint behavior outside the supported boundary | Read `reason` and check compatibility; JupyHop will not open it automatically |

A failed SSH connection is a command or per-host inventory error, not a reliable
new state for the remote session. Within a successful remote report,
`unreachable` can mean that the process exists but its endpoint/provenance cannot
be verified. Read the accompanying `reason` and per-host error fields.

`status` can reconcile an interrupted launch's private readiness record. It does
not restart a server or run a kernel health check. **Exit 0 means the status
request succeeded**, even when its server state is `stale`, `failed` or
`unreachable`. Scripts must inspect `servers[].state`; see
[JSON output](json-reference.md) and [exit codes](scripting.md#exit-codes).

## Where records live

| Location | Content |
| --- | --- |
| Local `$XDG_CONFIG_HOME/jupyhop/config.toml`, default `~/.config/jupyhop/config.toml` | Optional launch/discovery preferences; OpenSSH keeps routing/authentication |
| Remote `$XDG_STATE_HOME/jupyhop/hosts/SCOPE/sessions/UUID/`, default below `~/.local/state` | Active managed record, immutable runner, private Jupyter settings, runtime/recovery files and server log |
| Remote `.../hosts/SCOPE/archive/UUID/` | Explicitly archived inactive evidence/settings; no automatic deletion |

The host/account scope derives from the remote Linux machine ID and Unix UID,
so a shared home directory does not merge registries from different machines.
Consistent remote HOME/XDG settings are needed across clients reaching the same
registry. Changing those paths or the account's host identity can make an old
registry unavailable; it does not stop its server.

The JSON `identity.scope` identifies an observation for the current boot/account.
It changes after reboot and is different from the stable registry directory's
scope. Use returned record/archive paths instead of constructing them from that
JSON field.

Managed directories are private 0700 and files 0600. Do not edit records,
substitute runner files or change schema numbers to force access. Settings,
logs and kernel connection files can be sensitive; keep backups private too.
Restoring files cannot restore a dead kernel's memory.

At most 128 active managed records are retained per host/account registry,
including inactive records. Use [archive](managed-sessions.md#archive-inactive-records)
after verified inactivity to release names and this budget. Archives retain
evidence and possible orphaned-kernel recovery data; they are not running-session
backups. There is no archive list/restore/delete command or automatic restart.
