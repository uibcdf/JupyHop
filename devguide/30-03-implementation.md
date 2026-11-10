# 30 — 0.3.0 implementation and acceptance

Status: 0.3.0 Linux source acceptance passed, following [29](29-03-session-ux-design.md).
The 0.2.0 physical pilot is closed in [28](28-02-physical-client-pilot.md).
The final acceptance section below identifies the exact qualified source/artifacts.
Earlier sections retain intermediate observations and findings. No 0.3.0 package
publication or new physical infrastructure pilot is claimed.

## Read-only managed inventory foundation

The new internal inventory RPC uses wire 1.5 independently of registry schema
1.0. It validates current private records/runner hashes, observes server state
without readiness writes and reads only allowlisted archive identity fields.
It never reads settings or kernel recovery contents for presentation.

Active results retain the 128-record bound. History is paged at 64 entries with
bounded offsets 0–4096 and a probe deadline. Only a complete initial page provides
an exact archive count; later or truncated pages remain explicitly partial.
Concurrent changes can alter directory enumeration between pages. Unknown or
unavailable inventory produces unknown counters, not zero. This introduces no
remote package, daemon, registry migration or archive mutation.

Observed on development Python 3.14.10: 21 focused unit tests pass, strict mypy
passes all 22 installed-source modules, and two disposable direct/ProxyJump SSH
integration cases pass. They cover live → stopped → archived observations,
record/runner byte preservation, private symlink boundaries, bounded history,
secret allowlisting, parser refusal and the unchanged 64 KiB RPC input bound.
No real workstation/session was used.

## Shared selection and lifecycle completion

Source CLI now has consistent terminal choices (including one ready candidate),
exact --name selection, resume as an open alias, a thin manage menu, status
summaries and explicit --history inspection. Stop/archive selectors pin the UUID
before confirmation. The interactive stop confirmation authorizes both stop and
archive by default; --keep-record keeps the stopped record. Existing UUID --yes
automation remains stop-only unless --archive is explicitly requested.

Compound completion reports its phases separately and archives only after a
confirmed stopped observation. An uncertain stop never proceeds to archive;
archive failure preserves a clear same-UUID recovery path. Menu open owns a
foreground forward; Ctrl-C returns to the menu, while termination propagates
through the owned connection cleanup.

All 273 existing/inventory unit tests pass plus 18 new UX regressions. Those
cover named/UUID selection, name reuse during confirmation, cancellation/EOF,
headless refusal, original JSON scripting, separate compound outcomes and menu
tunnel return. Strict types pass all 24 source modules. Three disposable SSH
integration cases pass, including actual named CLI open, terminal confirmed
stop-and-archive, history JSON, unchanged second-server state and stop-only script
compatibility. This is source acceptance, not publication of 0.3.0.

## Actionable and shareable diagnostics

The owned OpenSSH master now captures bounded stderr for curated classification,
including terminal runs. Password/passphrase input remains on native /dev/tty;
only a fixed retry notice is echoed. Default-config ownership and unsafe writes
have conditional remedies, while includes/jump-side errors do not get guessed
to be local. The default local path is derived from passwd, as OpenSSH does,
rather than assuming an overridden HOME controls its config location.

A disposable ssh -G -F experiment with OpenSSH 10.2p1 found that it accepts explicit-file
modes 0600, 0644 and 0664. That differs from the default config's write check:
do not add an independent rejection policy for --ssh-config or misattribute a
jump-side rejection to that explicit local file. A new CI-only acceptance driver
uses the existing exclusively provisioned Unix test account to check native
default 0600/0644 acceptance, native write-permission policy and the actual classifier, then removes
only its newly created config by inode. It refuses ordinary accounts and an
existing config. Its native-policy finding and final acceptance are recorded below.

Discovery wire 1.6 adds sample_limit/scan_limit while retaining entry_limit as a
legacy marker. Filling the sample no longer falsely marks a later fully scanned
directory limited. Human discover/list aggregate non-ready unmanaged rows;
--all restores individual diagnostics and JSON keeps the bounded detail.
Metadata/ownership/endpoint checks and scan/sample limits remain unchanged.

Doctor --report emits a versioned support JSON containing normalized client and
selected-remote versions/capabilities, including local results when SSH fails.
It allowlists output rather than scrubbing arbitrary logs: identities, addresses,
paths, credentials and scientific state are not collected for export. It never
uploads. The optional diagnostics.kernel_report API inspects this interpreter's
package metadata without SSH or Jupyter imports. A notebook import needs JupyHop
there; ordinary remote operation still requires no remote installation.

Observed: 15 focused feedback/report tests pass, including native-stderr capture
in both modes, wrong-owner/machine discrimination, unknown result preservation,
redaction and experiment account guards. Ten disposable native SSH terminal/key
tests pass, including echo restoration and independent forward cleanup. Two
crowded/multiple-runtime integration cases pass after retaining the compatible
noninteractive multiple-server diagnostic. Strict types cover 25 source modules.

At this stage public documentation, installed candidate qualification, native
default-config acceptance and four-Python hosted checks remained incomplete.

## Whole-suite and terminal follow-up

The combined suite initially exposed a duplicate unit/integration module basename;
the integration module is now test_session_ux_ssh.py. The complete disposable
regression then observed 378 passing tests in 227.63 seconds on Python 3.14.10.

Follow-up hardening checks inventory state/reason consistency, bounds exported
version strings and handles a missing local passwd entry without reflecting its
exception. A real terminal management test also exercises Ctrl-C and SIGTERM.
Ctrl-C can terminate the foreground SSH master as well as the attached open;
management explicitly discards only that owned route, then authenticates again
for a refreshed inventory. Unexpected socket loss still fails closed; there is
no automatic mux/network fallback. Both terminal cases pass and leave their
fixture server healthy. The focused affected suite observes 58 passing cases;
lint and strict types pass. Candidate CI must include these follow-up changes.

## Numeric candidate, installed gates and public documentation

Package/source version is now 0.3.0 with no suffix/tag. The actual-wheel upgrade
gate additionally uses trusted 0.2.0 source at
6e0438eeb39a3bc8b92acb48545e55b343b52279; the historical 0.1.0 gate remains.
Conda source qualification requires those executed steps plus native default
configuration permission acceptance. Installed smoke now checks the shareable
report, named open, managed/history counters and explicit compound completion
without local Jupyter. Temporary artifact-directory/wheel arguments avoid
replacing any earlier reviewed files in dist.

Current-user guides, README, changelog, security, architecture/protocol/CLI/UX
specifications, roadmap, decisions and scenario ledger describe the source
candidate and clearly retain 0.2.0 as the published Conda baseline. A new
diagnostics guide provides the optional notebook API and a copyable stdlib cell.
Strict Sphinx 9.2.0 / MyST 5.1.0 observes 28 HTML pages without warnings; all
1482 local links/resources/fragments and generated CLI sections pass. The source
gate accepts 77 CLI, two TOML and six JSON examples without executing them.
Shell examples with output redirection retain their separately reviewed scope.

The actual local 0.3.0 wheel/sdist pass safe-content, metadata/version, MIT,
entrypoint, Python classifiers and complete-source inspection. The clean
installed-wheel smoke passes without local Jupyter, including support report,
named open, history/counters, compound completion and preserved old UUID scripting
through ProxyJump. The installed 0.2.0-to-0.3.0 wheel experiment also passes:
upgraded, concurrent old and independent new clients retain the same live kernel,
session, PID, memory/progress and immutable runner/registry bytes; only its own
test UUID is stopped/archived.

The optional API is additionally exercised inside an actual disposable kernel,
with SSHTransport.run forbidden and a synthetic scientific memory marker present.
The report has the correct context/package metadata, excludes the marker and
leaves it unchanged. No real scientific environment/session is tested.

At this stage candidate hosted acceptance and native default-config results were
pending. These tests do not authorize a 0.3.0 Conda/PyPI publication.

## Registry capacity boundary

Review of the new slot overview exposed a missing old start guard: records()
accepted 128 entries, but reservation could then create a 129th, making later
bounded reads fail. Start now reads/counts under its existing exclusive lock and
returns the allowlisted registry_full error before creating a session directory.
It gives a known-negative outcome and status/archive remedy, not an unknown
launch claim. No new stored schema or automatic cleanup is introduced.

The regression prepares only synthetic failed records in a disposable SSHLab,
checks unchanged record bytes after refusal at 128, archives one verified inactive
entry and verifies that a real managed launch then fills exactly the freed slot.
Its failure cleanup is restricted to the experiment's own possible launcher.

## Hosted findings and pinned stop evidence

The first hosted candidate, 70559028e6adb41923261dcc2e54adebc995c41c,
ran [source checks](https://github.com/uibcdf/jupyhop/actions/runs/42784063151)
and [documentation deployment](https://github.com/uibcdf/jupyhop/actions/runs/42784063299).
Documentation and both server-compatibility jobs passed. The full suite observed
388 passes on Python 3.12–3.14; Python 3.11 observed 387 passes and one failure:
after stop, a subsequent process probe returned unreachable instead of stopped.
The precise transient /proc failure was not retained in that test output.

Review found that the stop RPC discarded its stronger verified pidfd exit proof
and used only a fresh, independently fallible observation for the reply. Stop
now retains the boot/PID/start-time tuple only after provenance checks, recorded
intent, SIGTERM and a confirmed exit of that pinned process. That proof can mark
only the same recorded identity stopped in this reply. It does not rewrite stored
identity/state, treat a pending stop as complete or affect read-only status.
Three deterministic regressions cover unavailable subsequent probes, unconfirmed
exit and changed identity. All 17 affected disposable lifecycle/session-UX SSH
integrations pass locally after this change.

The same hosted run passed both installed upgrades, installed smoke, browser
reconnection and real-account isolation on 3.14, then failed the new native
configuration experiment before password acceptance. Its always-run cleanup
removed both generated accounts and private sshd. The experiment now reports only
fixed failure stages/exception classes for diagnosis, suppressing raw output;
an additional temporary-file test exercises its complete classifier payload and
exclusive-file cleanup. Native acceptance remains pending and is not waived.

The follow-up at fc73e31116aca0a8206c96bf94f257d33c322540 observed all 393
tests passing on each supported Python, but native acceptance still failed.
The narrowed experiment at 3cdf6c2bd376881cfc76009fc4ad0ef5a125f7f2 verified
that the default config was loaded and the requested modes were present; Ubuntu
26.04's OpenSSH 10.2p1-2ubuntu3.8 then accepted 0664 in its private user group.
This is documented distribution behavior, not a JupyHop bypass: the
[Ubuntu ssh_config FILES contract](https://manpages.ubuntu.com/manpages/resolute/man5/ssh_config.5.html#FILES)
allows group write when that group contains only the owner. Upstream's
[readconf permission check](https://github.com/openssh/openssh-portable/blob/V_10_2_P1/readconf.c#L2496)
does not contain that exception.

The experiment now records either native private-group 0664 result and requires
0666 world-write rejection plus the curated remedy. Both variants execute the
actual classifier payload in unit regression. It does not infer distribution
policy in production, add accounts/groups, weaken permissions or change OpenSSH.
The conservative owned-file remedy stays chmod 600. Native fixtures run and clean
up before the longer suites, so a prerequisite failure is diagnosed promptly.

## Final source acceptance — 2026-11-10

The implementation acceptance anchor is
**8bca6ab4f7466fac6dceda0516f95427e71ef28d**. All six
[source jobs](https://github.com/uibcdf/jupyhop/actions/runs/42786776464)
and both [documentation jobs](https://github.com/uibcdf/jupyhop/actions/runs/42786776216)
completed successfully. Documentation closeout commits follow this anchor;
they do not replace the artifact identity recorded here.

| Check or experiment | Observed result |
| --- | --- |
| Complete Linux suite on CPython 3.11, 3.12, 3.13 and 3.14 | 394 passes per interpreter: 318 unit and 76 disposable SSH/kernel integrations |
| Lint, formatting, strict types | Passed in all four source jobs; 25 installed-source modules checked |
| Jupyter Server 2.17.0 and 2.20.0 | Existing access and supported/refused launch boundaries passed |
| Actual installed candidate without local Jupyter | Support report, named open, history/counters, compound completion and legacy UUID scripting passed through ProxyJump on all four Pythons |
| Installed upgrades from trusted 0.1.0 and published 0.2.0 source | Same live notebook/kernel/session/PID/memory/progress, concurrent old/new clients and immutable runner/registry passed on all four Pythons |
| Native private terminal SSH | Actual Unix password direct/jump open, managed start, retry, cancellation, deadline, terminal restoration and headless refusal passed |
| Two actual non-root Unix accounts | Private registry/kernel access and lifecycle isolation passed; only generated accounts/homes and private sshd removed |
| Native default config | Loaded 0600/0644; private-group 0664 accepted by Ubuntu; 0666 rejected and actual curated remedy passed; exclusive config removed |
| Browser | Ordinary and managed login, authenticated kernel WebSocket execution and independent-client same-memory reconnection passed |
| Sphinx and source examples | Strict build and deployment passed; 28 pages, 1482 local references, all generated CLI sections, 77 CLI/two TOML/six JSON examples |
| Distribution and Conda source gate | Hosted wheel/sdist inspected locally against exact clean source; check-source passed with the actual complete/executed hosted matrix; nothing uploaded to a package registry |

The [distribution artifact](https://github.com/uibcdf/jupyhop/actions/runs/42786776464/artifacts/13749478904)
contains the inspected wheel, sdist and SHA256SUMS. Its ZIP digest is
b9e229d15854c7ec55a547c8c8d3d479400e83670ee1a8674135008aa7f15e2d.
The individual artifact hashes are:

```text
c2310b708f9a08eeac81a3b38b63fea6552b0a6514a2a19af64505419e977c5d  jupyhop-0.3.0-py3-none-any.whl
3b154ba7cf18df99e7641ddd47288e11e39d12f5be37c4b1f490c8830f0788cb  jupyhop-0.3.0.tar.gz
```

The implemented decisions are D49–D55: one shared selector/lifecycle layer,
read-only bounded inventory, pinned UUID authority, explicitly confirmed compound
completion, allowlisted diagnostics and native OpenSSH policy/lifetime reuse.
The two additional correctness fixes enforce the existing 128-record boundary
before reservation and retain verified pinned-process exit evidence. Registry
schema 1.0, existing immutable runners, zero mandatory Python dependencies and
the no-mandatory-remote-installation model remain valid in the tested upgrades.

Files are reviewable in the
[complete implementation diff](https://github.com/uibcdf/jupyhop/compare/3b79a08...8bca6ab).
New source modules are selection.py, controls.py, session_inventory.py,
_inventory_remote.py and diagnostics.py. Existing CLI/discovery/fleet/SSH/
connection/managed/lifecycle/protocol modules implement the shared flow and guards.
The new native permission experiment, installed package/release/source gates,
four focused unit modules and test_session_ux_ssh.py provide the new acceptance;
existing lifecycle, connection, managed and publication tests were extended.
README, changelog, security, public Sphinx guides and the architecture/CLI/
security/testing/decisions/scenario/protocol/discovery/UX ledger are synchronized.

Accepted scope covers names/selectors, managed counters/history, explicit
stop-and-archive, native diagnostics and optional notebook reporting. It does not
include macOS, exhaustive discovery, automatic archive deletion, restoration of
dead memory, remote restart/logout-policy testing or new lifecycle authority over
unmanaged servers. Archive totals remain bounded/partial when necessary. Ctrl-C
inside management can require fresh native SSH authentication. The physical
infrastructure pilot remains evidence for 0.2.0; 0.3.0 uses isolated qualification.

The temporary Sphinx environment and its isolated package cache were removed;
validated HTML, local receipts and reviewed distributions were retained outside
the repository. No personal SSH configuration, scientific environment/session,
site network setting or real server was modified by this implementation work.

Next: review and explicitly promote a 0.3.0 Conda build through the existing
exact-file workflow, independently install it and repeat the guided physical
client usability pilot. The currently published coordinate remains 0.2.0=py_0.
No 0.3.0 Conda/PyPI upload, version tag or GitHub Release was created here.
