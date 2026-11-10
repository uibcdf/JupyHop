# JSON output reference

This page describes **0.3.0 CLI output**, after validation of remote replies.
It is distinct from the internal SSH wire envelopes. Ordinary `doctor --json` retains
`protocol`, `operation` and `data` at the top level; do not expect those keys in
the other commands' JSON. Doctor --report is a separate support shape; `list`
has its own local `version: 1` contract.

Examples below use invented identities and paths. The empty results demonstrate
shape; they do not claim no remote servers exist. Check exit status and stderr:
some errors produce a report followed by a nonzero exit, and other failures
produce no JSON. See [Scripting](scripting.md) for process and input handling.

`identity.scope` is an opaque current-boot/account observation scope, not the
stable host/account directory name in the managed registry. Do not use it to
construct a state path or as a session selector. Use the managed UUID and the
returned `record_path`/`archived.path` when a path is needed.

## Discover and inventory

`discover HOST --json` returns these top-level fields:

```json
{
  "host": "workstation",
  "identity": {"uid": 1000, "user": "researcher", "scope": "aaaaaaaaaaaaaaaaaaaaaaaa"},
  "coverage": {
    "complete": false,
    "paths": [{"path": "/home/researcher/.local/share/jupyter/runtime", "source": "linux-default", "status": "missing"}],
    "issues": []
  },
  "servers": []
}
```

This empty discovery exits **6**. `coverage.complete` is always false, including
when ready servers are found. Path statuses are `ok`, `missing`, `unsafe` or
`limited`. Issues can include scan/time/output limits, unavailable interpreters
or unavailable managed state; preserve them when presenting results.

A server entry, when present, contains:

| Field | Meaning |
| --- | --- |
| `id`, `origin`, `name`, `observed_id` | Selection identity, managed/unmanaged provenance and optional managed display name; see [Session identities](sessions.md) |
| `state`, `reason` | Observed state and diagnostic; only `ready` is openable |
| `pid`, `port`, `address`, `base_url`, `version` | Validated remote endpoint/process details; some can be null for non-ready entries |
| `sources` | Remote runtime directories contributing the observation |

`list HOST --json` wraps that report in a fleet result even for a single host:

```json
{
  "version": 1,
  "complete": false,
  "hosts": [
    {
      "host": "workstation",
      "ok": false,
      "report": null,
      "error": {"code": 3, "message": "SSH route unavailable in this illustrative result."}
    }
  ]
}
```

Here all routes failed, so list exits **3**. For an inspected route, `ok` is true,
`report` is the discover result and `error` is null, even if `servers` is empty.
All inspected routes yield exit 0; mixed inspected/failed routes yield 14. A
single-host failure's original code is retained in `hosts[].error.code`.

## Managed status, stop and archive

`status HOST --json` and `stop HOST UUID --yes --json` share these fields:

```json
{
  "host": "workstation",
  "identity": {"uid": 1000, "user": "researcher", "scope": "aaaaaaaaaaaaaaaaaaaaaaaa"},
  "servers": [],
  "error": null
}
```

An unfiltered status with no active records can return this and exit **0**.
For an exact UUID that is absent from the active registry, `error` becomes
`not_managed` and exit is **11**. Archived UUIDs are absent from that registry.
Successful observation of a stale/failed/unreachable managed record can also exit
0: inspect `servers[].state` rather than treating command success as readiness.
The `reason` values describe observations, not kernel health.

`archive HOST UUID --yes --json` adds an `archived` field. A successful result has
empty `servers`, `error: null` and:

```json
{
  "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "path": "/home/researcher/.local/state/jupyhop/hosts/cccccccccccccccccccccccc/archive/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
}
```

This block is the **value of `archived`**, not the full response. A failed archive
has `archived: null` and an error. Retrying the same already archived UUID can
succeed idempotently; it does not restore a session.

## Launch and open

`start HOST --no-open --json` returns `host`, `id`, `state`, `error`, `record_path`,
`server` and `identity`. A ready launch has `error: null` and a verified managed
`server` entry. Unconfirmed/failed launches can still emit JSON with their request
ID and null `server`/`identity`; inspect the nonzero exit and reconcile that UUID
before another start. `record_path` can be null when no record was established.
The known registry_full refusal reports failed with null record_path/server:
0.3.0 did not create a 129th record. It is distinct from an unknown transport
outcome; inspect/archive existing inactive entries to release capacity.

`open HOST ID --json --no-browser` emits a single object and then stays attached:

```json
{
  "host": "workstation",
  "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "origin": "managed",
  "url": "http://127.0.0.1:49152/login?next=%2F",
  "authentication": "jupyter-login",
  "tunnel": "attached"
}
```

The port and URL path are illustrative: use the exact returned URL, including a
custom base path. The URL works on this client while its tunnel is alive.
`--json` alone does not suppress browser launch; add `--no-browser` for automation.
A successful `start --json` without `--no-open` also emits this connection shape,
not the detached launch report. Read one line while the child process remains
alive; waiting for end-of-file waits until the forward closes.

## Doctor

`doctor HOST --json` has `protocol: {"major": 1, "minor": 0}`, `operation: "doctor"`,
`host`, `ok`, `missing` and a `data` object. Data includes `identity`, `python`,
`jupyter_server`, `jupyter_core`, `runtime_dirs`, `coverage` and `process_managers`.
Package versions may be null. `data.coverage` is `selected-interpreter-only`.
Missing packages or unsupported Python yield `ok: false`, the named `missing`
prerequisites and exit 4, rather than an SSH failure.

Normal output excludes credentials. Identities, local URLs and remote paths still
need redaction before sharing. The [version policy](compatibility.md#client-wire-and-state-versions)
defines the independent client/wire/registry contracts; validate the fields your
script needs and handle null/non-ready/per-route-error results explicitly.

## Managed overview and history

`status HOST --history --json` explicitly selects the new version-1 inventory
shape. Human unfiltered status uses the same read-only observations; legacy
status --json without --history keeps the earlier shape above.

```json
{
  "version": 1,
  "host": "workstation",
  "identity": {"uid": 1000, "user": "researcher", "scope": "aaaaaaaaaaaaaaaaaaaaaaaa"},
  "sessions": [],
  "complete": true,
  "history": {"entries": [], "offset": 0, "next_offset": null, "complete": true},
  "error": null,
  "history_error": null,
  "summary": {"ready": 0, "stopped": 0, "review": 0, "unarchived": 0, "archived": 0, "archive_count_exact": true}
}
```

This is a successful empty managed/history observation, not evidence about
unmanaged servers. Active entries contain id, name, state and reason. History
entries contain id, name and record_state; record_state is retained evidence,
not the current process state or an authorization to resume.

`complete` applies to active managed enumeration. Unknown active counts are null,
not zero. History has its own completeness/error fields. A partial archive count
is the number of verified entries on the returned page, a lower bound, not the
total; check archive_count_exact. Pages contain at most 64 entries; follow a
non-null next_offset using --history-offset (0–4096). Enumeration can change
between requests. A later page is never an exact total, even at its end.

## Compound completion and support reports

`stop HOST UUID --yes --archive --json` uses version 1 with host, id, stop and
archive fields. Stop/archive contain their respective validated legacy reports;
archive remains null when it was not attempted or no reply was obtained. A
reported phase failure adds an allowlisted error object. Inspect exit status
and both phases: stop can succeed while archival is unconfirmed. An SSH failure
before the first stop reply can still produce no JSON. Ordinary stop --yes
without --archive retains its original output and stop-only semantics.

`doctor HOST --report` emits report_version 1 with context, client, remote,
outcome and privacy. Versions are normalized; identities/paths/credentials are
not copied into it. Remote can be null on failure while client remains useful.
The optional notebook API uses the same report_version with its own kernel
context/package-metadata shape; see [Diagnostics](diagnostics.md). Neither form
uploads or creates kernels. Ordinary doctor --json remains the private-context
diagnostic described above.

```console
jupyhop doctor workstation --report --json
```
