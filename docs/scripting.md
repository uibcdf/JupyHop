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
action. Those commands never guess a session from its display name or PID.
Supply a new managed server's Jupyter password through a protected stdin source
with `--password-stdin`; this does not provide an SSH password.

## JSON output

Successful `--json` output goes to stdout; diagnostics go to stderr. Normal
results exclude passwords, tokens, cookies and private keys. Runtime/state paths
and identities can still be private information, so redact them before sharing.
Not every failure emits a JSON result. Check the exit status and stderr before
assuming stdout contains a report.

| Command | Result shape / lifetime |
| --- | --- |
| `doctor` | Versioned selected-interpreter diagnostic, including prerequisite results |
| `discover` | Single-host report with `servers` and partial-search `coverage` |
| `list` | Local version-1 inventory with a `hosts` array of per-route success/error results |
| `open` | One connection result with a token-free local URL; process remains attached |
| `start --no-open` | Managed launch result and request UUID; no attached local tunnel |
| `status`, `stop` | Managed status report, including its server entries and any allowed error |
| `archive` | Archive result for the exact managed UUID |

`list HOST --json` uses the fleet envelope even for one host. Use
`discover HOST --json` when your script expects a single-host discovery report.

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
| 6 | No verified discovery candidate in the partial search |
| 7 | Ambiguous or invalid server selection |
| 8 | Forwarding failure |
| 11 | Managed lifecycle refusal |
| 12 | Failed/unconfirmed managed launch, including transport failure with unknown remote write outcome |
| 13 | Unconfirmed stop/archive outcome |
| 14 | Some inventory routes failed while others succeeded |
| 130 | Interrupted; inspect remote state before retrying a write |

For an SSH or interrupted-write failure, do not infer remote process death from
the local exit status. Follow [Recovery](recovery.md). More detailed actions for
these errors are in [Troubleshooting](troubleshooting.md).
