# Scripting and exit codes

Use explicit SSH aliases and exact server/session IDs in scripts. A headless
client requires noninteractive SSH authentication on every hop. `--batch` makes
that requirement explicit even when a terminal exists.

```console
jupyhop discover workstation --batch --json
jupyhop list workstation-a workstation-b --batch --json
jupyhop status workstation SESSION_ID --batch --json
```

For stop/archive, an exact managed UUID plus `--yes` explicitly authorizes the
action. Automated mutations never select from a display name or PID. Existing
UUID --yes stop scripts stay stop-only. To explicitly authorize both phases:

```console
jupyhop stop workstation SESSION_ID --yes --archive --batch --json
```

That form uses a versioned compound result, separating stop from archive. An
uncertain stop does not archive; a confirmed stop with uncertain archival returns
13 and a same-UUID recovery instruction. `--keep-record` is available for terminal
users who want stop-only behavior. `manage` and lifecycle name/number selection
require a terminal; they are not new automation target-resolution rules.

Supply a new managed server's Jupyter password through a protected stdin source
with `--password-stdin`; this does not provide an SSH password.

`--batch` disables SSH authentication prompts. Server/route selection also stays
noninteractive when stdin/stdout are not terminals or when `--json` is supplied.
For stop/archive, `--json` therefore requires `--yes` even in a terminal.

## Start with a protected password source

For an existing protected credential file, run on the local client:

```console
jupyhop start workstation --batch --server-python /absolute/remote/env/bin/python --workdir '~/projects/analysis' --name analysis-batch --password-stdin --no-open --json < /path/to/private/new-jupyter-password
```

Replace the paths with your own values. The file supplies a single UTF-8 password
line, 8–1024 characters without ASCII control characters, ending in an optional
LF. Stdin input is additionally bounded to 4096 bytes including that line ending.
Keep it accessible only to you, outside the repository; a protected credential
manager's stdout can supply the same input. Do not put its contents in argv,
environment variables, shell history or debug/CI logs. SSH must authenticate
noninteractively on every hop. Retain the session password through your chosen
private workflow for future Jupyter login; the server retains only its hash.

`--no-open` returns the launch result. `--no-browser` alone still creates an
attached tunnel and keeps the process running. A failed or interrupted start can
have created a server; preserve its request UUID and reconcile before retrying.

## JSON output

Successful `--json` output goes to stdout; diagnostics go to stderr. Normal
results exclude passwords, tokens, cookies and private keys. Runtime/state paths
and identities can still be private information, so redact them before sharing.
Not every failure emits a JSON result. Check the exit status and stderr before
assuming stdout contains a report.

The [JSON reference](json-reference.md) gives actual field layouts and examples.
The CLI's result shapes differ from the internal remote wire envelopes.

| Command | Result shape / lifetime |
| --- | --- |
| `doctor` | Versioned selected-interpreter diagnostic, including prerequisite results |
| `doctor --report` | Version-1 shareable support report; local context survives a failed remote check |
| `discover` | Single-host report with `servers` and partial-search `coverage` |
| `list` | Local version-1 inventory with a `hosts` array of per-route success/error results |
| `open` | One connection result with a token-free local URL; process remains attached |
| `start --no-open` | Managed launch result and request UUID; no attached local tunnel |
| `status`, `stop` | Managed status report, including its server entries and any allowed error |
| `archive` | Archive result for the exact managed UUID |
| `status --history` | Version-1 managed/history inventory and summary; partial/unavailable counts stay explicit |
| `stop --archive --yes` | Version-1 compound result with separate stop/archive outcomes |

`list HOST --json` uses the fleet envelope even for one host. Use
`discover HOST --json` when your script expects a single-host discovery report.

For example, this shell fragment retains empty partial discovery as a report
while treating other failures as errors, including under `set -e`:

```sh
umask 077
if jupyhop discover workstation --batch --json > discovery.json; then
    jupyhop_exit=0
else
    jupyhop_exit=$?
fi
case "$jupyhop_exit" in
    0|6) python -c 'import json, sys; r = json.load(sys.stdin); print([s["id"] for s in r["servers"] if s["state"] == "ready"])' < discovery.json ;;
    *) exit "$jupyhop_exit" ;;
esac
```

Run it in a private working directory and use a fresh output filename; `umask`
does not tighten permissions of an existing file. Preserve `coverage` when
presenting the report; an empty ready-ID list is a partial search result.

`open --json` prints a connection result and stays running while its tunnel is
needed. A caller must manage that process lifetime; waiting for ordinary exit
before using the URL would wait for the tunnel to close. `start` without
`--no-open` can also attach the browser/tunnel flow. Interactive SSH prompts remain
owned by OpenSSH's controlling terminal.

Wire versions, remote registry schema and the local inventory/config format
have separate contracts. Inspect the [version policy](compatibility.md) and
validate fields rather than assuming unrelated envelopes have the same shape.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Requested checks/results succeeded; list inspected every selected route, even if no ready servers were found |
| 2 | Invalid arguments or local configuration |
| 3 | SSH/access/timeout failure; list could inspect no selected route |
| 4 | Missing remote prerequisites or failed Python probe |
| 5 | Invalid or incompatible remote JSON/protocol/schema |
| 6 | No verified candidate in a single-host search, or an explicit ID is absent/no longer verified |
| 7 | Ambiguous/invalid terminal selection, or hostless open has zero or several candidates without a valid choice |
| 8 | Forwarding failure |
| 11 | Managed lifecycle refusal |
| 12 | Failed/unconfirmed managed launch, including transport failure with unknown remote write outcome |
| 13 | Unconfirmed stop/archive outcome |
| 14 | Some inventory routes failed while others succeeded |
| 130 | Interrupted; inspect remote state before retrying a write |

For an SSH or interrupted-write failure, do not infer remote process death from
the local exit status. Follow [Recovery](recovery.md). More detailed actions for
these errors are in [Troubleshooting](troubleshooting.md).

For `status`, exit 0 confirms a successful observation, even if a managed entry
is stale/failed/unreachable. Check `servers[].state` and the
[state meanings](sessions.md#interpret-an-observed-state) before deciding that a
server is ready. A lifecycle error may still produce a JSON report before its
nonzero exit and stderr diagnostic.
Human status without a selector uses the new read-only overview; status --json
without --history preserves its earlier managed-server shape/reconciliation.
Names select read-only open/status directly, but automated stop/archive still
require an exact UUID. Only --report is intended as a shareable attachment;
other JSON can contain identities/paths.
