# JSON output reference

This page describes the **0.2.0 CLI output**, after validation of remote replies.
It is distinct from the internal SSH wire envelopes. Only `doctor` retains
`protocol`, `operation` and `data` at the top level; do not expect those keys in
the other commands' JSON. `list` has its own local `version: 1` contract.

Examples below use invented identities and paths. The empty results demonstrate
shape; they do not claim no remote servers exist. Check exit status and stderr:
some errors produce a report followed by a nonzero exit, and other failures
produce no JSON. See [Scripting](scripting.md) for process and input handling.

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
  "path": "/home/researcher/.local/state/jupyhop/hosts/aaaaaaaaaaaaaaaaaaaaaaaa/archive/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
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
