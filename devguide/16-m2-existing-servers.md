# 16 — M2: discover and open existing servers

Date: 2026-11-08. Status: M2 complete; M3 has not started. This report records
the implemented contract, experiments, decisions, files, tests and remaining
acceptance gates. M0/M1 reports remain historical evidence.

## Work performed and shipped commands

```console
jupyhop discover workstation
jupyhop list workstation --json
jupyhop open workstation
jupyhop open workstation SERVER_ID --no-browser
jupyhop discover workstation --runtime-dir '~/custom/runtime'
jupyhop open workstation --remote-python /env/one/bin/python --remote-python /env/two/bin/python
```

Only existing current-account servers are supported. No start, restart, adoption,
managed registry or process supervision is implemented. The `stop HOST ID` guard
always exits 11 **without sending an SSH command**. It is not a managed stop API.

`list HOST` is an alias for `discover HOST`, not multi-host inventory. One ready
candidate can be selected automatically. Multiple candidates require an explicit
exact ID or a numbered choice on stdin/stdout TTYs. JSON/noninteractive use never
prompts or guesses. Invalid/absent/stale IDs fail without changing remote state.

`open` prints a token-free URL to the normal Jupyter login page. The user supplies
their existing password/token. `--no-browser` prints the same useful URL and keeps
the tunnel attached; a missing browser also falls back to that URL. `--json`
prints one connection object, with progress on stderr. The URL is usable on this
client's loopback; it is not a sharing link for another machine.

The command stays attached. Ctrl-C, SIGTERM and SIGHUP close only its owned local
SSH process group and control socket. Repeated opens create separate connections
and local ports; no persistent tunnel daemon or shared master is adopted. A
network/SSH failure reports unknown remote state, not server death. A manually
launched server's original launcher is responsible for its persistence.

## Decisions and justification

### Discovery, identity and ownership (D21)

A standalone stdlib Python script travels over SSH stdin (`-I -B`); no remote
JupyHop package, files or helper cache is installed. Use known Jupyter runtime
paths from `jupyter_core` when installed; otherwise use configured environment
variables and Linux user-data defaults. Explicit additional paths/interpreters
extend coverage without scanning arbitrary processes or enumerating Conda.
The helper Python and the server/kernel Python may be different environments.

Coverage is **always partial** (`coverage.complete: false`), even after a
successful scan. Paths have `ok`, `missing`, `unsafe`, or `limited` status; issues
identify exhausted bounds or unavailable interpreters. Zero verified candidates
is never phrased as definitive absence. Multiple interpreter probes must agree
on remote account/host scope or discovery fails closed.

Read supported `jpserver-<pid>.json` files directly and never call Jupyter's
stale-file-deleting list API. Pin every directory component using `O_NOFOLLOW`,
require current-UID private directories (0700), and open regular single-link
files with `O_NOFOLLOW|O_NONBLOCK`, current UID and private permissions (0600).
Reject oversized, changing, malformed or duplicated-key records. Never follow a
metadata symlink/FIFO or change/delete a stale file. Symlinked runtime paths are
unsupported; provide the actual canonical path explicitly.

Metadata alone does not establish ownership. Confirm process UID, all UID fields,
start time, non-zombie state and the SSH process's network namespace. Join only
the declared PID's socket descriptors with Linux TCP tables. The chosen port
must belong to that PID, listen on IPv4 `127.0.0.1`, and have no owned public or
wildcard listener on that port in either address family. Confirm the public
Jupyter version API and unauthenticated denial on the protected status API,
then recheck process/socket identity. No arbitrary localhost port scan occurs.

IDs are opaque 96-bit hashes of host/account scope (boot ID + UID), PID/start
time, socket inode, port and base path. They are independent of a client's port
or alias and deduplicate identical live servers from multiple runtime paths.
They are not credentials and are not managed-session IDs. Changes in process or
listener identity require fresh selection; no kernel continuity is inferred.
All M2 records are `unmanaged`; states are `ready`, `stale`, `unsupported`, or
`unreachable`. Only `ready` records can be opened.

### Auth and supported URLs (D22)

Preserve Jupyter's normal login and authentication. Do not read credentials into
client results, disable authentication, persist a credential cache, or pass tokens
to browser argv. Runtime `token`, `password`, `url` and notebook-root fields are
not forwarded. Neither an empty token nor a legacy password flag establishes
authentication mode. Generic JSON is reconstructed from nonsecret fields.

HTTP checks use stdlib direct loopback connections without proxies or redirects.
An experiment found `/api/` redirects to `/api` in Jupyter 2.21.1, so validation
uses the canonical `BASE/api` endpoint directly. It must expose recognizable
Jupyter 2 version information, and `BASE/api/status` must deny unauthenticated
access with 403. Unprotected or unrecognized auth endpoints are not opened.
M2's selected baseline is explicit login, **not automatic token handoff**.

Simple ASCII base paths, including `/science/`, are preserved in login, HTTP and
WebSocket requests. Dot traversal, double slashes, encoded/complex base paths,
queries and fragments in metadata base paths are unsupported. IPv6-only, public
bindings, HTTPS, Unix sockets, older Notebook `nbserver` records and unusual
auth/proxy arrangements are labeled unsupported. No TLS/SSH check is weakened.

### Owned forwarding connection (D23)

Use one new OpenSSH master in the foreground and a private temporary control
directory. This refines D16's attached policy: control sockets are used only to
own/configure this invocation, never to reuse another invocation's tunnel.
The master uses the original SSH alias/config, keys, User and ProxyJump, with
strict target host trust and batch authentication as in M1.

`ClearAllForwardings=yes` avoids activating configured static forwards. Adding a
command-line `-L` on that same invocation would also be cleared, so add only our
explicit forward through OpenSSH's control protocol. Multiplex clients use a
minimal `-F /dev/null` configuration, a fixed owned socket, and
`ProxyCommand=false` to prohibit fallback to a different network connection.
`ssh -O check` must report the exact owned process PID. A port-open check alone
never establishes tunnel ownership. A successful `-O forward` establishes that
OpenSSH actually bound the loopback listener. Bind failure triggers bounded
retries with fresh ephemeral ports; unrelated listeners are untouched.

Revalidate the selected server through a command **on this same master**, then
validate the forwarded HTTP/auth endpoint before invoking the browser. An
unrelated connection resolving the same alias is insufficient. If the server
identity changes, fail and close only our tunnel. As with other HTTP clients,
these checks are observations at open time; they cannot prevent later server
exit or port reassignment while a browser remains open. Close/reopen to revalidate.

Alternatives considered: a bare `ssh -L` inherits unwanted configured forwards
or loses the requested forward when clearing them; socket prechecks alone race;
adopting any open port loses ownership; a detached local daemon introduces state
and cleanup requirements unnecessary for M2. OpenSSH's existing mux protocol
provides reliable binding feedback and exact-connection verification.

## Protocol, limits and errors

The `discover` SSH response uses protocol 1.1 and a `data` envelope containing
`identity`, `complete: false`, `paths`, `servers`, and bounded diagnostic codes.
M1 doctor's 1.0 operation is unchanged. Incompatible majors fail, extra optional
fields are ignored, and known fields are validated/reconstructed. Registry
schema negotiation remains future work because M2 performs no registry writes.

Each candidate includes only ID, origin, state/reason, PID, port, loopback
address, supported base path, version and runtime sources. Generic output never
contains token-bearing URLs, cookies, passwords or private keys. Raw SSH/remote
errors are suppressed in favor of curated diagnostics.

Bounds: up to eight explicit interpreters, sixteen extra runtime paths per
probe, 1024 characters/path, 16 KiB/record, 512 directory entries and 64 records
per probe, 4096 descriptors/candidate, 1 MiB/TCP table, and 64 KiB SSH stdout.
Output is reduced with an explicit limit diagnostic when needed. A remote alarm
bounds a probe to at most ten seconds, within the configured SSH deadline;
network responses are size bounded and each HTTP request has a two-second absolute read deadline, including trickled headers. `--timeout` is per probe/startup, not
the sum of all selected interpreters. Failed/unsupported observations remain
partial rather than being silently treated as absent.

Exit codes extend M1: 6 no verified candidate/selected ID; 7 ambiguous or invalid
selection; 8 tunnel/forward failure; 11 unmanaged stop refusal. Codes 0/2/3/4/5/130
retain their meanings. Discovery with zero ready candidates emits its nonsecret
JSON report but exits 6. Opening emits a ready URL and remains attached; Ctrl-C
returns 130 after cleanup. Browser absence does not stop an otherwise usable
headless tunnel.

## Experiments and tests

Linux/OpenSSH 10.2p1; Jupyter Server 2.21.1, JupyterLab 4.6.4, ipykernel 7.4.0.
Observed local matrix:

| Python | Unit + disposable SSH/Jupyter integration | Clean wheel doctor/discover/open |
| --- | --- | --- |
| 3.11 | 130 passed | Passed, no local Jupyter |
| 3.12 | 130 passed | Passed, no local Jupyter |
| 3.13 | 130 passed | Passed, no local Jupyter |
| 3.14 (development) | 130 passed | Passed, no local Jupyter |

Each run includes 103 unit and 27 integration cases. Tests never target real
SSH hosts or scientific sessions. Two temporary sshd processes run as the
current user on loopback, with fresh pinned keys and isolated HOME/runtime paths.
The fixture's server-side StrictModes exception from M0 remains isolated; client
host-key verification stays strict. Only owned fixture resources are cleaned.

| Evidence | Result/security assertion |
| --- | --- |
| `test_zero_config_discovery_and_open_existing_server` (direct/jump) | One manual server opens with no JupyHop config or selected local port; token login, invalid-auth denial, kernel WebSocket result 42 |
| `test_multiple_servers_custom_paths_and_duplicate_runtime_metadata` | Distinct candidates, no implicit selection, duplicate live metadata deduplicated |
| `test_password_authentication_is_preserved` | Ordinary password login/cookie auth through jump |
| `test_stdlib_helper_finds_jupyter_in_another_environment` | No Jupyter installation required in helper interpreter |
| `test_private_master_ignores_configured_forward_and_retries_collision` | Static conflicting forward suppressed; occupied unrelated listener untouched; retry succeeds |
| `test_concurrent_opens_have_independent_owned_tunnels` | Independent local ports and cleanup; server remains alive |
| `test_headless_cli_signal_closes_only_owned_tunnel` (three signals) | Actual CLI readiness JSON; local listener closes; original Jupyter PID survives |
| `test_http_header_trickle_cannot_extend_absolute_deadline` | Slow header bytes cannot extend the absolute HTTP deadline |
| `test_server_identity_change_refuses_open` | Changed identity never reaches browser |
| `test_ssh_policy_denies_forwarding_without_stopping_server` | SSH login success does not imply forward permission; actionable failure |
| Unit filesystem/proc/protocol/selection/browser tests | Reject symlink/FIFO/hardlink/oversized/shared metadata, other UID, wildcard socket or wrong inode, hostile URLs/fields, ambiguity and unsafe arguments; no secret reflection |
| `experiments.m2_conda_smoke --second-python ...` | Two real Conda interpreters (development 3.14 and temporary 3.11), two manual servers, custom runtime, explicit environment probes, jump and kernel execution |
| `experiments.browser_smoke` | Chrome 157.0.8103.38 headless with its **default sandbox**, private profile: normal form login, JupyterLab shell, cookie-authenticated browser WebSocket result 42; no token query in navigation history |
| `experiments.package_smoke` | Clean installed wheel with no local Jupyter; packaged doctor/discover/open probes through jump; owned tunnel cleanup |

Ruff lint/format, mypy, `git diff --check`, wheel/sdist builds, MIT metadata and
zero mandatory runtime-dependency checks pass. All 65 scenario IDs remain mapped
in the ledger and relative documentation links resolve.

Reproduction: install `.[dev,experiments]`, then `pytest --run-integration`.
`pytest` alone collects only dependency-independent unit tests. `ruff check .`,
`ruff format --check .`, `mypy`, build and clean-wheel smoke are required.
Browser acceptance additionally needs Chrome/Chromium; it uses no real browser
profile, credentials or server. CI defines the four Python versions and browser
smoke on 3.14; GitHub execution has not been observed in this local iteration.

## Files and acceptance status

Created: `src/jupyhop/_discovery_probe.py`, `discovery.py`, `tunnel.py`,
`opening.py`; `tests/test_discovery.py`, `tests/integration/test_m2_open.py`;
`experiments/jupyter_fixture.py`, `browser_smoke.py`, `m2_conda_smoke.py`; this
report. Updated: CLI/errors/protocol/SSH, test collection/earlier CLI tests,
isolated SSH fixture, package smoke, pyproject, CI, README and relevant guide
contracts/decisions/ledger. MIT license is unchanged and packaged.

M2 acceptance is satisfied: manually launched current-user Jupyter opens through
ProxyJump without manual local ports; multiple matches are distinguishable;
incomplete discovery stays explicit; invalid/unprotected auth is never bypassed;
stop is refused; one-server opening needs no JupyHop config; supported and
unsupported address/base/TLS cases are documented. See the per-scenario ledger.

## Limits and next milestone

No managed lifecycle or persistence guarantees, full account-sharing/isolation
acceptance, physical multi-machine coverage, HTTPS/IPv6 support, exhaustive Conda
discovery, arbitrary endpoint override, automatic credential handoff, or detached
tunnel manager. Open-time validation does not freeze a server's future identity.
The jump and target fixtures are processes on the same Linux machine/account,
not separate OS instances. Full live-kernel recovery remains M4; unrelated SSH
reachability cannot imply kernel health. Product runtime dependencies remain zero.

Next recommended milestone: **M3 managed launch and readiness**, after review of
this M2 report. Stop here in this iteration; do not infer managed ownership from
discoverability or advance to persistent lifecycle work yet.

Primary references: [Jupyter REST API](https://jupyter-server.readthedocs.io/en/stable/developers/rest-api.html),
[Jupyter security](https://jupyter-server.readthedocs.io/en/stable/operators/security.html),
[OpenSSH control/forwarding](https://man.openbsd.org/ssh),
[Linux proc](https://docs.kernel.org/filesystems/proc.html),
[Chrome headless](https://developer.chrome.com/docs/automation-and-testing/headless).
