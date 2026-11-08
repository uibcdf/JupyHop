# 17 — M3: managed launch and readiness

Date: 2026-11-08. Status: M3 complete within the acceptance scope below. M4 has
not started. This report records the work, experiments, decisions, changed files,
tests, acceptance evidence, risks and next milestone.

## Shipped work and CLI contract

```console
jupyhop start workstation --server-python /absolute/remote/env/bin/python --workdir '~/projects/analysis' --name analysis
jupyhop start workstation --name batch --no-open --json
jupyhop discover workstation --json
jupyhop open workstation SESSION_ID
```

`start` creates one current-account owned server, chooses a remote port through
Jupyter's native `port=0`, verifies process/socket/HTTP/auth readiness, records
its identity and normally opens it through the existing owned SSH forward.
`--no-browser` keeps an attached tunnel and prints the login URL. `--no-open`
returns the launch result without a local tunnel/browser. No fixed port range,
environment activation, JupyHop TOML file or privileged service is needed.

The server environment must already exist. `--server-python` is an absolute
remote Python executable or `python3`; it defaults to `--remote-python`, whose
default is `python3`. The helper can be a separate stdlib-only Python. The target
needs Python >=3.11, Jupyter Server 2, available kernel specifications, and tmux
on the noninteractive SSH PATH. JupyterLab is enabled when installed; otherwise
the ordinary server/API view is available. Named `--env` profiles remain M5.

`--workdir` is evaluated remotely. `~` is the remote account's home; relative
paths resolve against that home. Existing workdir symlinks are canonicalized.
Spaces, Unicode and shell metacharacters remain literal data. `~other`, control
characters, absent directories and inaccessible directories are rejected.
Available kernels and the Python running Jupyter remain distinct concepts.

A new session password is prompted privately and confirmed. Noninteractive
start requires `--password-stdin`, consuming one UTF-8 line from a protected
source. There is deliberately no password argv option. Passwords must have
8–1024 characters without control characters; use a strong separate session
password. Existing-server `open` retains its normal login behavior.

Discovery now distinguishes verified `managed` servers from `unmanaged` ones,
shows display names and preserves UUID session IDs. Open uses the exact ID;
name-based resolution is not implemented. `stop` still refuses **all** lifecycle
control without sending SSH, including managed sessions. Use Jupyter's own
authenticated shutdown action until M4 implements verified managed stop.

## Experiments and architectural decisions

### Private tmux is the initial launch backend (D24)

M0 proved tmux detachment but could not use systemd user services from its no-PAM
SSH fixture. M3 selects tmux as a narrow, explicit initial backend rather than
build a custom supervisor or silently change linger/system policies. There is
one private socket per UUID and no reuse of the user's default tmux server.
`-f /dev/null` avoids user tmux configuration; multi-argument `new-session` executes
the selected Python directly. The runner changes workdir itself, avoiding tmux
format expansion of user workdir strings. Socket paths use an owned private XDG
runtime directory when usable, otherwise an owned private `/tmp/jupyhop-UID`.

This is an immediate launch/detachment guarantee for the tested SSH context,
**not a universal last-logout persistence guarantee**. systemd backend selection,
logout/linger policy, reboot handling and full kernel continuity remain M4.
No automatic restart-on-failure policy is added.

### Password authentication without a plaintext cache (D25)

The chosen password crosses only encrypted SSH stdin. A short program in the
selected Jupyter Python generates Jupyter's native Argon2 hash. Only that hash
is retained in `settings.json`, in a 0700 directory with file mode 0600. It is
separate from ordinary records. No token is generated for this password-only
mode; a nonempty password hash and `password_required=True` preserve Jupyter
authentication. Unauthenticated protected API access must return 403 before
readiness is accepted. Wrong-password denial and correct login are tested.

The client does not persist the password, send it through argv/environment,
expose it in generic JSON, or launch token-bearing browser URLs. A second
authorized client can use the known password in Jupyter's normal login form.
No new token retrieval, browser cookie transfer or keychain integration is needed.

Security review: a copied password hash permits offline guessing, so strong
passwords and restrictive OS permissions matter; permissions are not encryption.
The authenticated Unix account already controls its workload and settings.
Other accounts must not read the state; symlink, hardlink, FIFO and shared-mode
state is refused. Python does not promise secure erasure of transient strings.
The private log is 0600, server logging is limited, and credential material is
never included in JupyHop diagnostics or automatically tailed logs. Hash/config
cleanup is deliberately deferred to explicit lifecycle cleanup in M4.

Rejected alternatives: disabling auth, storing plaintext tokens for new sessions,
token URLs in browser arguments, or requiring restoration of an old client's
local credentials. Automatic protected browser handoff remains separate work.

### Versioned remote state with explicit ownership (D26)

State layout:

```text
$XDG_STATE_HOME/jupyhop/hosts/<host-account-scope>/
    registry.json                   schema 1.0
    .lock                           bounded flock, private regular file
    sessions/<UUID>/
        record.json                 nonsecret launch identity/state
        launch.py                   immutable versioned client-owned code
        settings.json               private native password hash
        server.log                  private diagnostics
        config/                     private ServerApp configuration search
        runtime/                    native Jupyter runtime files
```

Default state base is `~/.local/state`. Host scope hashes Linux machine ID plus
UID; raw machine IDs and hostnames are not stored in the layout. This prevents
shared HOME/NFS directories from merging different hosts. A readable stable
`/etc/machine-id` or `/var/lib/dbus/machine-id` is required for managed launching.
Cloned machine IDs on hosts sharing a home are unsupported; JupyHop never
creates or repairs OS identity automatically. Existing-server access remains
available even when managed-state prerequisites are missing.

Every app-controlled directory is private and owned by the account. Path
components are opened without following symlinks. Records/settings are bounded,
private, regular single-link files. Atomic replace plus file/directory fsync
protect updates; a bounded global flock serializes reservations and updates.
Names are 1–64 simple characters, unique within this host/account registry.
They stay reserved even for failed/exited records until explicit future cleanup.
Up to 128 entries are accepted; corruption or exhausted bounds fails closed.

A UUID is generated before the remote request, recorded before process launch,
and reported on uncertain transport outcomes. Records contain owner UID, boot
identity, name, Python/workdir, manager/socket, PID/start time, actual port,
socket inode and runner SHA256. Readiness is an observation, not an inference
from a file. A temporary HTTP failure never proves server death.

To label a live server managed, combine the existing current-UID/socket checks
with the record's boot/start/inode/port/base-path identity, exact runner argv,
immutable runner hash and private tmux pane PID. A copied runtime record cannot
grant lifecycle authority. Unexpected identity becomes unverified/unmanaged;
no process is stopped, restarted or adopted. Full stop authorization remains M4.

### Bootstrap, compatibility and configuration (D27)

There is no installed remote JupyHop package or central daemon. The SSH RPC
sends trusted packaged source and structured request data in stdin. It compiles
client-owned code only; registry/metadata content is never interpreted as code.
The new per-session runner retains an immutable copy of that source under the
remote account, with an integrity digest. Each new session gets its own copy;
upgrades do not replace running launchers or scientific environments.

Wire protocol is 1.2; registry schema is separately 1.0. Unknown registry major
or newer minor versions are rejected for writes before creating session data.
No migration or downgrade is attempted. Running Jupyter remains alive when a
new client encounters an incompatible registry. Read-only discovery reports
unavailable managed state while retaining its partial unmanaged search.

The runner isolates ServerApp's config search to its private directory, disables
automatic extension discovery, and explicitly enables only installed JupyterLab.
Loopback, auth, XSRF and proxy-related security settings are fixed. The prototype
showed that `runtime_dir` is not a configurable ServerApp trait: the runner sets
Jupyter's supported runtime/config environment before importing/initializing it.
Existing user Jupyter/SSH configuration and environments are not rewritten.

### Readiness, failures and recovery boundaries (D28)

The runner checkpoints its PID/start identity, then its bound port/inode on the
Jupyter IOLoop. The initiating helper verifies native runtime metadata and API
behavior before recording `ready`. `port=0` lets the OS allocate an actual free
listener atomically; no race-prone remote port reservation is introduced.

Initialization failures retain a `failed` record and bounded reason code.
Transport interruption/readiness timeout is uncertain: a server may continue
and the record may remain requested/starting. Fresh discovery can find it using
remote state, without an old client's ports/cache. It does not silently retry
start or rewrite partially known state. Name locking prevents two starts with
the same explicit name. Reconciliation, idempotent recovery and cleanup remain M4.

`--timeout` bounds each SSH request. Start transport uncertainty uses exit 12
rather than claiming no server was created. Missing prerequisites use 4;
incompatible state uses 5. Other M2 codes retain their meaning. Default start
opens only its new session; tunnel/browser failure does not stop it. Ctrl-C
closes the owned local tunnel and reports that the start request may remain
running. `--no-open --json` emits a nonsecret launch result.

## Tests and observed results

Local Linux, OpenSSH 10.2p1, tmux 3.6, Jupyter Server 2.21.1, ipykernel 7.4.0;
JupyterLab 4.6.4/Chrome 157.0.8103.38 for browser acceptance. All SSH targets,
homes, data, workdirs, credentials, tmux sockets and Jupyter instances in tests
are disposable; no real scientific server/session is targeted.

| Python | Unit + integration | Clean wheel existing/managed access |
| --- | --- | --- |
| 3.11 | 173 passed | Passed, no local Jupyter |
| 3.12 | 173 passed | Passed, no local Jupyter |
| 3.13 | 173 passed | Passed, no local Jupyter |
| 3.14 (development) | 173 passed | Passed, no local Jupyter |

Each run has 135 unit and 38 integration cases, including all prior milestone
regressions. CI defines the four versions, installs tmux only as fixture setup,
and runs both existing-server and managed browser smoke on 3.14. GitHub CI has
not been observed in this local iteration.

| Evidence | Assertion/result |
| --- | --- |
| `experiments.m3_launch_spike` | Private tmux, literal Unicode/metacharacter workdir, isolated config, native hashed password, no token and Lab availability |
| `test_managed_start_password_kernel_and_owned_registry` (direct/jump) | Correct remote workdir, private files, managed provenance, invalid-password denial, authenticated kernel WebSocket result 42 |
| `test_two_managed_sessions_have_distinct_ids_ports_and_names` | Two sessions coexist with distinct IDs/listeners |
| `test_concurrent_same_name_reserves_only_one_session` | Real concurrent SSH starts; exactly one launch and one conflict |
| Missing Python/workdir/dependency tests | Actionable refusal before creating a session record |
| `test_stdlib_helper_launches_and_opens_jupyter_in_a_separate_environment` | A helper with no Jupyter launches and opens the separately selected Jupyter Python |
| `test_failed_initialization_keeps_recoverable_record` | Controlled fixture initialization failure retains a visible failed record |
| `test_discovery_will_not_adopt_managed_record_with_wrong_process_identity` | No false managed authority; healthy process remains untouched |
| `test_newer_registry_is_not_modified_and_running_server_survives` | Incompatible schema blocks new writes without stopping the existing server |
| `test_cli_start_password_stdin_and_signal_keep_remote_process_alive` | Actual CLI password stdin, ready JSON, Ctrl-C cleanup; remote PID survives |
| Unit state/auth/protocol tests | Password absent from argv/output; unknown secret fields dropped; strict versions, unsafe lock/file handling, atomic replace failure, host scoping and uncertain-state reporting |
| `experiments.browser_smoke --managed` | Real Chrome default sandbox/private profile: password form, JupyterLab, cookie-authenticated WebSocket result 42; no token in history |
| `experiments.package_smoke` | Offline clean-wheel client with no local Jupyter; existing access and managed start/open through jump |

Required checks: Ruff lint/format, mypy, unit/integration matrix, wheel/sdist
build, clean client smoke, MIT metadata, source fixtures/guides and secret-path
checks. These pass locally; all 65 scenario IDs remain mapped in the ledger.
The client still has zero mandatory Python runtime dependencies.

## Files created or changed

Created `src/jupyhop/managed.py` and `_managed_remote.py`; `tests/test_managed.py`
and `tests/integration/test_m3_start.py`; managed fixture and M3 experiment scripts;
this report. Updated CLI/errors, read-only discovery/protocol/opening, isolated
SSH fixture, cookie-capable test WebSocket helper, browser/package smoke,
pyproject description, CI, README, decisions, roadmap and acceptance ledger.
MIT attribution/license is unchanged.

## Acceptance and remaining limits

M3 acceptance is satisfied: launch under the correct remote account/environment
and workdir, authenticated loopback-only native port allocation, stable owner/
provenance record, direct/ProxyJump connection and real kernel execution; two
sessions coexist; failed and incompatible starts preserve work and recoverable
evidence. No public listener, privileged central service, credential argv,
arbitrary shell interpolation or auth bypass is introduced.

Limits: tmux is the only initial launch backend; stable Linux machine identity
and canonical private state paths are prerequisites. Wrapper launchers, profile
configuration, custom extensions/auth, IPv6/HTTPS and other OSes are unsupported.
One corrupt registry entry can make managed discovery unavailable; unmanaged
search remains partial and an explicit runtime path may still be inspected.
No automatic record cleanup/name reuse is provided. Last logout/linger, actual
reboot, physical independent clients, live credential rotation, full kernel
continuity and safe managed stop remain unvalidated M4 gates. Detachment in the
disposable no-PAM SSH context does not resolve site logout policy.

Next recommended milestone: **M4 — persistent lifecycle, reconciliation and
reconnection**. Stop here for review before implementing it.

Primary references: [Jupyter security](https://jupyter-server.readthedocs.io/en/stable/operators/security.html),
[tmux](https://man.openbsd.org/tmux), and source inspection of the tested Jupyter
Server/core versions for configuration and bind/IOLoop behavior.
