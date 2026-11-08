# 19 — M5: scientific, multi-host and account workflows

Date: 2026-11-08. **M5 complete; product acceptance and fixture cleanup verified.**
M6 has not started. This report records work, experiments, decisions, changed
files, tests, acceptance, limits and the next milestone.

## Shipped work and contracts

```console
jupyhop start workstation-a --env research
jupyhop list workstation-a workstation-b --json
jupyhop list
jupyhop open
jupyhop open workstation-a SESSION_ID
jupyhop archive workstation-a SESSION_ID --yes
```

Existing-server opening still needs only a working SSH alias and discoverable
prerequisites. Optional version-1 TOML is read from
`$XDG_CONFIG_HOME/jupyhop/config.toml` (default
`~/.config/jupyhop/config.toml`), or per-command `--config FILE`:

```toml
version = 1
[profiles.research]
server_python = "/absolute/remote/env/bin/python"
workdir = "~/projects/analysis"
[hosts.workstation-a]
profile = "research"
runtime_dirs = ["~/custom-runtime"]
[hosts.workstation-b]
remote_python = "python3"
```

Host addresses/users/keys/jumps stay in OpenSSH. Profiles select an existing
Python executable and directory; no activation, environment installation or
shell fragment. Explicit CLI server Python/workdir override profile values;
`--env` overrides the host's default profile. Helper Python is separate: CLI,
then host `remote_python`, then python3. CLI runtime paths extend per-host paths.
Server and notebook kernel environments remain distinct.

Config is an owned regular single-link file, at most 64 KiB, not writable by
others (`chmod 600` recommended). Final symlinks, unknown keys/schema, malformed
TOML and credentials are rejected without echoing raw input. A missing default
file is optional; an explicitly missing file is an error. Limits: 32 profiles,
16 hosts and 16 additional runtime paths. Tests isolate local XDG preferences.

`list [HOST ...]` probes explicit aliases or all configured hosts sequentially,
with a deadline per host. Its stable local JSON version-1 envelope contains
per-route successes/errors and `complete=false`; one failure does not hide other
results. Exit 0 means every selected host was inspected, even with no ready
servers; 14 means some hosts failed; 3 means all failed. This replaces M2's list
alias JSON shape. `discover HOST` preserves the original single-host contract.

Hostless `open` inventories configured aliases: one verified candidate can be
opened; multiple candidates need a TTY selection or explicit `open HOST ID`.
Errors from other routes remain visible. Same-machine aliases are explicit routes
to the same remote registry, not global host identifiers. No network guessing,
relay, SSH parser or cached-route repair is introduced.

`archive HOST UUID [--yes]` retires an inactive entry by atomically moving its
private session directory to `archive/UUID` under the same registry. It frees the
name and active-record budget while preserving all settings/runtime evidence.
It does not delete data, touch the scientific workdir or stop orphaned kernels.
Live PID/start identity, a live runner at the exact state path despite damaged
metadata, any live private tmux pane, and uncertain pre-PID launches are refused.
Repeated archive is idempotent. A new session may reuse a retired name, with a new
UUID; archived UUIDs cannot be reused by new clients. Unknown schema/unsafe state
fails before a move. Transport interruption leaves outcome unknown; retry the
same archive UUID to reconcile.

Registry schema remains 1.0; archive RPC is 1.4. Start remains 1.2 and discovery/
status/stop 1.3. Archive source is sent only for archive, keeping bootstrap within
64 KiB. No archived code is executed, runner replaced or schema migrated.

## Architectural decisions and alternatives (D34–D37)

**D34 — Minimal TOML profiles/preferences.** Stdlib tomllib preserves zero mandatory
Python dependencies. Strict bounded data and explicit CLI precedence avoid a
second SSH inventory or shell launcher. Considered alternatives: invoking Conda
activation/env enumeration, generic command templates, host credentials in TOML
or required configuration for basic open. These add dependencies, ambiguity or
unnecessary execution surface. Activation hooks/kernel-selection extensions are
not implemented.

**D35 — Bounded per-route inventory.** Sequential ordinary OpenSSH requests are
simple to interrupt and preserve owned transport cleanup. A maximum of sixteen
aliases bounds the work; total duration can be host count times timeout. Parallel
workers/cancellation plumbing, automatic host enumeration and central discovery
are not needed for this slice. Explicit route labels prevent conflating aliases
or hiding a failed destination. The pre-alpha list JSON change is documented;
single-host consumers retain discover.

**D36 — Archive instead of delete.** The 128-active-record bound and reserved
names demonstrated a practical retirement need. Moving verified inactive state
under the existing lock, with directory fsync, releases capacity without erasing
possible orphaned-kernel connection evidence. Rejected alternatives: automatic
stale deletion, PID-only inactivity assumptions, deleting keys after a crash,
restarting/adopting a process, or rewriting the stored state machine under old
runners. Files keep their private permissions. Permanent archive deletion needs
its own retention/recovery policy.

**D37 — Real account fixture separate from the product.** The operator explicitly
created two unique temporary Unix users/groups and a separate loopback-only sshd,
using generated independent keys and an offline-pinned host key. Root-owned state
binds cleanup to generated names, UID/home/marker and the pinned listener process.
Root is needed only for this test infrastructure, never by JupyHop. The normal
SSH service/configuration and pre-existing scientific users were not changed.
CI defines equivalent provisioning/acceptance and always-cleanup steps on 3.14;
that GitHub run has not been observed locally.

Alternative investigated: no Docker/Podman was available and unprivileged user
namespace mapping was refused. QEMU 10.2.1 and Ubuntu libraries were extracted
only into /tmp. An official Alpine 3.23.8 BIOS cloud image was SHA512/signature
verified against Alpine's published fingerprint and booted two real UIDs.
Jupyter Server 2.17.0 launch under TCG returned unconfirmed launch_unknown;
imports measured 4.43 s and password hashing 1.07 s. The cause was not established:
this does not prove version incompatibility or satisfy account acceptance. At
the user's suggestion, native temporary accounts replaced that experiment. The
VM prototype, image and extracted tools were removed, not shipped as dependencies.

References: [stdlib TOML parsing](https://docs.python.org/3.11/library/tomllib.html),
[Alpine official images](https://alpinelinux.org/cloud/),
[QEMU user networking](https://www.qemu.org/docs/master/system/devices/net.html).

## Experiments and observed behavior

- Two disposable SSH destinations, one direct and one through ProxyJump, launch
  the same display name with distinct UUIDs/listeners. CLI profiles select a
  Conda executable and a separate venv executable. Relative HOME paths, symlink
  canonicalization, tilde, spaces, Unicode and literal shell metacharacters are
  verified. Two simultaneous forwards execute separate kernels; fresh connections
  recover each original kernel/memory marker.
- A route-change case edits the same SSH config from direct to ProxyJump while
  an earlier tunnel stays open. Fresh OpenSSH requests retain the same server
  identity. Duplicate aliases expose the same UUID/registry; a same-name start
  through the second alias conflicts instead of creating a duplicate process.
- Live archive is refused. After native graceful stop, records/settings are moved
  intact; repeated archive works and a new UUID can reuse the name. Unknown
  schema, unsafe files/symlinks and damaged identity cannot authorize a move.
- The real-account experiment uses native Python 3.14.4 as stdlib helper and a
  temporary shared Conda Python 3.14.10/Jupyter Server 2.21.1 environment. Both
  actual UIDs independently create the same display name in separate scopes.
  Both kernels/notebook associations run concurrently and preserve memory after
  all initial tunnels/HTTP clients close and fresh password login is established.
- Each actual account fails to enumerate the other's session even with an explicit
  foreign runtime path, cannot read its record, cannot pass open ownership checks,
  and receives not_managed for foreign stop/archive UUIDs. Both healthy servers
  remain alive after rejected requests. Distinct Jupyter passwords reject the
  other account's password. Own stop/archive then succeeds for both roles.
- Clean wheel clients have no local Jupyter. They exercise profiles, two-route
  inventory, existing-server access, managed start/open/status/idempotent stop/
  archive through ProxyJump and owned-tunnel cleanup. Their installer/client
  environments exclude inherited PYTHONPATH/PYTHONHOME and isolate XDG config.

## Tests and results

Linux, OpenSSH 10.2p1, tmux 3.6, Jupyter Server 2.21.1, ipykernel 7.4.0;
JupyterLab 4.6.4 and Chrome 157.0.8103.38 for browser acceptance.

| Python | Full unit/integration regression | Clean wheel, no local Jupyter |
| --- | --- | --- |
| 3.11.18 | 258 passed | Passed |
| 3.12.16 | 258 passed | Passed |
| 3.13.18 | 258 passed | Passed |
| 3.14.10 (development) | 258 passed | Passed |

The full final suite has 258 cases (206 unit, 52 integration), including the
route-change/alias case and isolated XDG test defaults. All earlier M1–M4
regressions are retained. The account fixture's thirteen unprivileged tests are
included in unit counts; actual privileged provisioning and real-account checks
are separate observed evidence, not mocked account-isolation claims.

`experiments.m5_account_acceptance` passed twice using only the explicitly
provisioned accounts. `experiments.browser_smoke --managed --reconnect` passed:
actual Chrome/default sandbox/private profile, password login, Lab, cookie
WebSocket execution, no token query in history, browser/tunnel closure, then a
fresh independent client recovers the same live kernel memory.

Ruff lint/format, mypy, wheel/sdist, MIT metadata and zero mandatory dependencies
are required checks. Source artifacts include tests/experiments/guides. All 65
scenario IDs remain mapped in the acceptance ledger. GitHub CI is updated but
has not been observed in this local iteration. Compatibility environments were
created temporarily with mamba; the development 3.14 environment is preserved.

## Files created or modified

New client modules: config.py, fleet.py; remote archive source _archive_remote.py.
Updated CLI, managed reservation guard and lifecycle response handling. Added
unit config/fleet/archive tests and M5 workflow integration; developer config is
isolated in conftest/package smoke. Added the guarded account fixture, its guide
and tests, plus real-account acceptance. Updated package smoke, CI and source
manifest (experiment Markdown instructions included), README, current architecture/
security/UX/protocol/roadmap/decisions and acceptance ledger. Historical milestone
reports remain unchanged. MIT license and zero mandatory runtime dependencies
are preserved.

## Acceptance and remaining limits

M5's bounded software acceptance is demonstrated: selected existing Python and
project directory, two destinations/forwards/kernels operating simultaneously,
reconnection without manual ports, per-route failures without unsafe relays,
and isolation between two actual Unix accounts. All code/test acceptance gates
pass. Operator account-fixture cleanup is confirmed and verified. Stop before M6.

Physical LAN/WAN moves, laptop suspend, host reboot/PAM last-logout policy,
hours-long scientific loads and additional platforms remain unmeasured. The two
SSH destinations are disposable loopback targets on one OS, not a claim about a
specific institution's physical workstations. UID isolation uses actual distinct
users, not only separate HOME variables. Site process-killing policy can defeat
tmux persistence; no systemd/linger changes or automatic restart is shipped.

Archives retain private password hashes/connection evidence and can consume disk
until explicitly managed; no permanent deletion command is implemented. A
pre-PID unconfirmed start cannot safely be retired, and one corrupt registry entry
still fails managed state closed. Incompatible schema is refused without migration.
Other Jupyter/auth/version/platform combinations require M6 review; the unresolved
Alpine/TCG observation is not hidden behind a universal Server 2 compatibility
claim. Profiles do not apply arbitrary Conda activation hooks or select a kernel.

## Account fixture operation and cleanup

See [the operator guide](../experiments/m5_accounts.md). From the repository:

```console
python -m experiments.m5_accounts prepare
sudo /usr/bin/python3 -m experiments.m5_accounts provision --root PATH_FROM_PREPARE
python -m experiments.m5_accounts check --root PATH_FROM_PREPARE
python -m experiments.m5_account_acceptance --root PATH_FROM_PREPARE --server-python ABSOLUTE_SHARED_PYTHON
sudo /usr/bin/python3 -m experiments.m5_accounts cleanup --root PATH_FROM_PREPARE
```

The operator provisioned the accounts and check/acceptance passed. All test
sessions were stopped/archived. The operator then ran privileged cleanup and
confirmed its success. Independent checks verified that both generated users
and groups, their processes, the private loopback listener and privileged fixture
state were absent. Remaining temporary client keys/configuration and the dedicated
shared server environment were removed. Temporary compatibility environments were
also removed; the development 3.14 environment is preserved. This is test
infrastructure, not a feature or privilege requirement of the installed product.

## Next recommended milestone

M6 — public beta, compatibility and release preparation: broaden supported
version/platform evidence, complete security/UX review, resolve explicit remaining
compatibility observations and prepare reviewed release artifacts. Publishing is
not part of M5, and M6 has not started.
