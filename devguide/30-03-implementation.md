# 30 — 0.3.0 implementation and acceptance

Status: 0.3.0 source candidate in qualification, following [29](29-03-session-ux-design.md).
The 0.2.0 physical pilot is closed in [28](28-02-physical-client-pilot.md).
No 0.3.0 publication or complete feature acceptance is claimed yet.

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
default 0600/0644 acceptance, 0664 refusal and the actual classifier, then removes
only its newly created config by inode. It refuses ordinary accounts and an
existing config. Its native account result is pending hosted observation.

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

Public documentation, full installed candidate qualification, the native
default-config account experiment and four-Python hosted acceptance remain to
be completed before calling 0.3.0 operational.

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

Candidate hosted acceptance and native default-config account results remain
pending. No 0.3.0 Conda/PyPI publication is authorized by these tests.

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
