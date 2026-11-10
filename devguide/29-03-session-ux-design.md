# 29 — Proposed 0.3.0 session usability

Date: 2026-11-10. Status: design proposal following the completed
[physical-client pilot](28-02-physical-client-pilot.md). The installed/public
client remains 0.2.0. None of the new interfaces below is implemented by this
document. Existing [UX](12-user-experience.md) and CLI contracts describe 0.2.0.

This is the historical design baseline, recorded before implementation. Current
source behavior and acceptance are now tracked in
[30](30-03-implementation.md) and the updated CLI/UX specifications. In particular,
the selected completion flags are --archive/--keep-record; the menu's Ctrl-C may
require fresh SSH authentication, and the chooser retains full UUIDs for reliable
copying/confirmation. The published Conda baseline remains 0.2.0 until promotion.

## Goal and priorities

Make normal session access and completion understandable without remembering
UUIDs or a separate housekeeping command. Reuse current OpenSSH, verified
discovery, registry, lifecycle and foreground-forward machinery. Keep the
client stdlib-only and remote package installation optional.

Suggested implementation order:

1. Actionable SSH permission/connection diagnostics and truthful discovery output.
2. One shared selector, exact managed-name lookup and visible inventory summaries.
3. An explicitly confirmed stop-and-archive interactive flow and history inspection.
4. A thin terminal manage entry point and bounded, reviewable diagnostic reports.

Issue references: [3](https://github.com/uibcdf/jupyhop/issues/3),
[4](https://github.com/uibcdf/jupyhop/issues/4) and
[5](https://github.com/uibcdf/jupyhop/issues/5). Additional macOS investigation
in [issue 2](https://github.com/uibcdf/jupyhop/issues/2) stays outside this increment.

## Selection contract to evaluate

| Proposed interaction | Behavior |
| --- | --- |
| Interactive open HOST without a selector | Show a numbered chooser even for one verified ready candidate. Zero remains a partial/no-candidate result; never start a server implicitly. |
| Explicit open HOST UUID or exact-name selector | Resolve one target and open directly; normal Jupyter login remains independent. |
| Interactive stop HOST without a selector | Offer only managed records relevant to stopping; show the chosen name/UUID and kernel consequences before authorizing any mutation. |
| Interactive archive HOST without a selector | Offer relevant inactive managed records; the existing backend still proves inactivity at execution time. |
| Interactive command with no host | Offer explicitly configured aliases or request an authorized SSH alias. No network scan or replacement OpenSSH configuration parser. |
| JSON/headless calls | Keep the existing direct UUID and ambiguity behavior; add no invisible prompts or implicit lifecycle targets. |

Display name, origin, observed state and a short ID in the chooser; show the full
UUID in confirmation/result details. Environment/workdir may be shown only when
supported metadata provides them. Clearly label unmanaged entries as open-only.

Prefer a mutually exclusive --name NAME option over overloading a positional ID.
Resolve an exact managed name in the chosen remote host/account's current
registry. A name resembling a UUID must remain unambiguous. No prefix/fuzzy
matching for lifecycle mutations. Archive releases a name; a replacement has a
different UUID. Resolve once, pin that UUID and revalidate ownership/provenance
after confirmation so name reuse or a changed listing cannot retarget an action.

The proposed always-visible interactive chooser intentionally revisits the
0.2.0 auto-open-one rule after direct user feedback. Explicit UUID/name selection
and noninteractive compatibility avoid adding unnecessary prompts to scripts.
Evaluate resume only as an optional alias of open; it must never restart a
stopped server or imply reconstruction of lost kernel memory.

## Inventory, counts and retained history

Current status HOST shows the unarchived managed registry, including stopped
records. Current list/discover may also show unmanaged observations. None offers
summary counters or archive enumeration. Archived records are not running
servers; archival describes where evidence is retained, not a new process state.

Propose an overview with separate managed categories:

- Verified ready servers, available to open.
- Confirmed stopped records still awaiting archive.
- Pending, unknown or other records requiring review, with detailed states.
- Archived historical records, available for evidence inspection only.

Show unmanaged discoveries separately and always qualify their counts as the
observed partial search, not a complete inventory of running processes. Missing
SSH access or corrupt/incompatible state yields unavailable/unknown counts, never
zero. Do not classify every non-ready or old record as stopped or archive-eligible.

Keep current machine-readable outputs compatible. A richer inventory needs an
explicit versioned shape; archive enumeration requires bounded private remote
reads and a protocol review rather than constructing paths from JSON identity.scope.
Archive history can grow beyond the active registry bound: paginate or cap
enumeration, expose truncation, and distinguish an exact count from a lower bound.
Do not migrate live registry/runner files merely to add presentation data.

## Make archival part of normal completion

The recommended interactive completion is **stop and archive**, with both actions
explained and authorized in the confirmation. Offer keeping the stopped record
when needed. Exact option spelling remains to be selected; existing UUID plus
--yes scripts must keep stop-only behavior unless archival is explicitly requested.

Implement this as two existing guarded operations on the same pinned UUID:

1. Perform graceful verified stop and report its observed result.
2. Only after confirmed inactivity, call the existing archive guard/move.
3. Report stop and archive outcomes separately. If archive fails, retain the
   stopped record, explain the remaining step and allow same-UUID archive retry.

An SSH failure or uncertain stop must not trigger archival. Later inventory can
show a retained stopped record and offer an explicit archive action. Merely
reading inventory must not archive, delete, restart or send process signals.
Readiness reconciliation in existing status is a separate documented metadata
write; use an observational inventory path for pre-confirmation selection.

This removes the need to remember housekeeping in ordinary interactive use
without adding a scheduler or cleanup service. Automatic archival based only on
age, stale status or client disconnection is rejected: none proves inactivity.
Unmanaged sessions remain outside stop/archive.

Archiving frees a name and active-record slot but retains private evidence and
possible orphaned-kernel recovery files. It does not delete notebooks or restore
kernel memory. History retention/deletion and bulk archival are separate future
decisions; do not add automatic deletion to solve an active-registry UX problem.

## Diagnostics and truthful feedback

- Identify known SSH configuration ownership/write failures and give conditional
  remedies. OpenSSH remains authoritative; no automatic chmod/chown or duplicate
  config parser. A jump-side error must not be guessed to be local.
- Distinguish terminal authentication timeout, connection/handshake failure,
  missing remote prerequisites and an unconfirmed launch. Preserve request IDs
  and status-before-retry guidance. The observed banner timeout is not yet a
  reproduced root cause or a reason to raise all defaults.
- Separate directory scan limits, retained diagnostic sample limits, time limits
  and output limits. Aggregate stale diagnostics in ordinary human output, retain
  explicit inspection/JSON detail, and never turn a bounded sample into a total.
- Collect client, remote selected environment and actual notebook-kernel context
  separately. Current doctor JSON contains identities/paths and is not a public
  bug-report attachment. A shareable report must redact and be user-reviewed.
- Provide a copyable stdlib notebook diagnostic cell before requiring a remote
  installation. An importable notebook API may be optional; it must not initiate
  SSH or dump environments, credentials, data or scientific memory.

A local temporary-directory control-flow experiment reproduced the discovery
wording problem: 64 synthetic stale candidates in one directory filled the
sample; one simulated ready candidate in the next directory was retained but
that one-entry directory was marked limited/entry_limit. Candidate verification
was mocked; this is not additional live-endpoint acceptance. The current source
sets the same marker for a 512-entry scan cutoff and a full 64-record sample.
The fix should improve meaning, not enlarge limits or delete original metadata.

## Architecture, alternatives and security

Use shared inventory → select → confirm → dispatch functions. A manage HOST menu
should call those functions and existing operations, retaining only invocation-
owned SSH connections. Attached open still owns a foreground forward; define
Ctrl-C to close that forward and return to the menu, and exit to close owned
connections. Do not introduce a detached tunnel daemon or parallel lifecycle.

A dependency-heavy terminal framework, central web portal, mandatory remote
package and automatic SSH key provisioning add no demonstrated value here.
Names and numbered choices are conveniences, not credentials or authority. The
remote account, verified UUID/process/runner and existing pidfd/archive guards
remain the safety boundary. Archived names must never reopen a replacement.

## Acceptance before calling 0.3.0 operational

- Single/multiple/zero candidates; exact names, UUID-like names, duplicate route
  aliases, name reuse and concurrent record changes are covered in unit and
  disposable SSH integration tests. Unmanaged mutation remains refused.
- Counters cover ready, stopped, pending/unknown, unavailable and bounded archive
  history without losing partial-result semantics. History never offers resume.
- Stop-and-archive covers success, declined authorization, EOF/signals, partial
  failure, lost replies, idempotent archive retry and name reuse. Failed stop does
  not silently archive; stop-only scripts remain compatible.
- Native password/key paths, terminal restoration and invocation-owned tunnel
  cleanup remain covered. Reproduce delayed jump authentication with disposable
  targets before changing timeout policy or claiming its cause.
- Diagnostic permissions, public-report redaction, differing kernel/server/helper
  environments and absent optional packages have meaningful regressions.
- All supported Python 3.11–3.14 clients, historical live runners, actual installed
  candidate, docs/examples and packaging pass their relevant gates. No scientific
  server, real user SSH configuration or remote logout policy is used as a fixture.

Update current-user docs and release notes when code exists. Publish a numeric
0.3.0 only after that candidate is qualified; this design creates no release,
tag, upload, state migration or claim of completed implementation.
