# 30 — 0.3.0 implementation and acceptance

Status: implementation in progress, following [29](29-03-session-ux-design.md).
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

A disposable ssh -G -F experiment found that this OpenSSH accepts explicit-file
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
