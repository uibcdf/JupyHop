# 35 — 0.4.0 implementation plan

Date: 2026-11-10. Baseline: released **0.3.0**, analysis commit **57ad340**.
Status: **implementation baseline for 0.4.0**. See the
[implementation report](36-04-implementation.md) for the candidate, test evidence
and remaining qualification.
This plan supersedes unresolved choices in [34](34-04-usability-and-browser-auth.md),
which retains the historical analysis and original feasibility evidence.
The published 0.3.0 package follows its original commands and security contract.

## 1. Outcome and scope

A prepared user starts a new named managed session, opens Jupyter and returns
from a second authorized client **without choosing, copying or entering a
Jupyter secret**. OpenSSH still authenticates each route using native passwords,
keys or agents. Ordinary human workflows use names/numbers and recognizable
context; UUIDs remain the internal identity and automation target.

Required for 0.4.0:

| ID | Requirement | Acceptance reference |
| --- | --- | --- |
| R01 | New managed servers use a fresh remote-generated native token by default; no Jupyter password prompt | A01, A02 |
| R02 | Automatic access delivers a native Jupyter cookie; the server token stays remote | A03, A04 |
| R03 | Explicit password mode, password-stdin scripts and legacy sessions remain usable | A05, A06 |
| R04 | Existing unmanaged servers remain open-only, with normal login and no automatic credential extraction | A07 |
| R05 | JSON/headless behavior has explicit rules; ordinary output never contains a credential | A08, A09 |
| R06 | A private one-use browser handoff expires and cleans up within defined bounds | A10–A13 |
| R07 | Normal selection/completion needs no UUID copying; confirmations still pin the exact target | A14, A15 |
| R08 | Successful named access avoids unrelated runtime-directory noise; uncertainty remains explicit | A16 |
| R09 | Auth/browser failures have phase-specific recovery and never stop or replace a server | A17, A18 |
| R10 | Old clients/runners/registry and existing output contracts have an installed compatibility gate | A19 |
| R11 | Linux/Python/browser/SSH/server and real Unix-account boundaries are qualified | A20–A22 |
| R12 | Current guides, demonstrated output, packages and publication evidence agree | A23, A24 |

Out of scope: unmanaged token extraction, legacy password-recovery/reset,
permanent local credential storage, stable cookie-name optimization, SSH key
provisioning, changing SSH/PAM/systemd policies, a profile wizard, a new terminal
framework, persistent/background tunnel services, automatic archive deletion,
other supervisors, macOS/Windows, Slurm, cross-user sharing and kernel restoration.
Keep manage's current Ctrl-C/possible SSH reauthentication policy (D55). Retaining
its master across terminal signals is a separate spike, not a release dependency.

## 2. Review of the earlier proposal

The previous analysis established direction and feasibility. It was not yet an
implementable release contract. This plan closes these gaps:

| Gap | Resolution here |
| --- | --- |
| Token or cookie crosses SSH? | Issue the native cookie remotely; return only that cookie in a dedicated private operation. |
| Default auth and password compatibility? | Two explicit server modes and deterministic CLI precedence; password-stdin retains password mode. |
| What about JSON/no-browser/no-open? | Freeze the mode table below; no secret or launch-file field is added to legacy JSON. |
| Old servers and metadata? | Separate versioned launch settings; keep registry schema 1.0 and immutable old runners. |
| Where do bounds and cleanup come from? | Fixed initial budgets, lifecycle states, failure codes and negative tests. |
| Does delivery prove browser login? | No. Production reports delivery/readiness; browser acceptance is verified by acceptance tests and the reader. |
| What if the broker or browser fails? | Close owned local resources, retain remote state and give resume/status recovery. |
| Is a nice prototype enough? | No. Explicit security, real-account, browser, installed-upgrade and reader gates block publication. |

The refinements are design selections, not new implemented features. A failed
gate requires a recorded revision; it must not silently weaken controls or remove
R01/R02 while still declaring this 0.4.0 plan complete.

## 3. CLI contract to implement

**All new options in this section are planned 0.4.0 syntax.** Preserve current
verbs, positional UUID meanings, exact `--name`, host selection, profiles and
one-candidate terminal chooser. No new public command is needed.

### 3.1 New-server mode: start --auth {token,password}

| Input | Effective mode / behavior |
| --- | --- |
| No --auth or --password-stdin | token; generate the credential remotely, without a Jupyter password prompt |
| --auth token | token |
| --password-stdin without --auth | password; preserve the existing protected-input script intent |
| --auth password in a terminal | password; choose/confirm privately as today |
| --auth password --password-stdin | password; read the existing bounded UTF-8 input format |
| --auth token --password-stdin | Invalid input (2), before reading stdin or sending SSH |
| Password mode without a TTY or protected stdin | Invalid input (2); never fall back to echo |

The Python `managed.start(..., password=...)` callers used by fixtures retain
password mode when no explicit mode was supplied. New CLI code passes its resolved
mode explicitly. Token mode rejects an unexpected password instead of ignoring it.
Keep current password length/control-character limits and path validation.

### 3.2 Browser behavior: --login {auto,manual}

Add this option to open/resume/start/manage. It controls access delivery, not
the server's authentication configuration. Resolve an omitted value to **auto for
human output, manual with --json**. This preserves existing machine-output flows.

| Invocation / selected server | Required behavior |
| --- | --- |
| Human auto, new token-mode managed server | Obtain a native cookie privately and perform the protected handoff |
| Human auto immediately after a password-mode start | Use only the password already provided for this start to obtain a native cookie; do not ask again in the browser |
| Auto, existing password/legacy managed server | Open normal Jupyter login with one concise explanation; do not add a new CLI password prompt or read/return the hash |
| Auto, unmanaged server | Normal login; do not call the credential action or extract its token |
| --login manual | Normal token-free Jupyter login URL; no cookie acquisition, private launch file or handoff listener |
| --no-browser, human auto on an eligible managed server | Prepare the handoff and print a clickable private file URI for a browser on this same client; do not launch a browser |
| --json, no explicit --login | Keep existing connection/launch JSON and normal-login behavior, including current --no-browser semantics |
| --json --login auto, browser launch enabled | Explicit opt-in; emit the existing connection shape only after delivery succeeds; no additional secret/path field |
| --json --login auto --no-browser | Invalid new combination (2); a machine-readable launch-file API is outside 0.4.0 |
| start --no-open, with or without --json | Return the existing launch result; no forward, native cookie acquisition, file, listener or browser |

Reject an explicit --login with --no-open as contradictory input; an omitted
login policy is simply inactive. Validate these combinations before remote work.
JSON alone must not introduce a selection/password prompt. Ordinary JSON keeps
its exact existing fields/types, including `authentication: "jupyter-login"`:
that describes native Jupyter authentication, not whether a person typed a secret.
Default JSON/manual result timing stays unchanged. Explicit auto is an opt-in to
waiting for delivery; its success still does not certify browser cookie acceptance.

Manual mode requires an existing native browser cookie or a separately obtained
Jupyter credential. A default token-mode start has no chosen Jupyter password:
manual login does not create one or reveal the native token. Explain this in
advanced/headless guidance rather than telling the user to enter their SSH
password into Jupyter. Prefer the protected same-client file flow for automatic
access without a GUI launcher.

On normal browser-launch failure, a human auto invocation can offer the same
protected file URI for the remaining deadline. JSON auto returns 15 instead of
inventing a new output shape. Manual-mode missing-browser fallback remains today’s
printed normal URL/attached tunnel. A remote/gateway file URI is not access from
a different computer; JupyHop must run on the browser computer.

### 3.3 --verbose and everyday output

Add a per-command --verbose to the existing connection-argument group. Default
human selectors/summaries show **number, name, origin and state**, with host when
several routes are involved. Show verified abbreviated project/interpreter
context after selection when available. Unknown unmanaged context stays unknown;
a Python path is not automatically a Conda environment name.

- Keep full UUIDs, observation IDs, endpoints and detailed coverage in verbose
  output, incident recovery and existing JSON. No fuzzy/prefix lifecycle targeting.
- Named/numbered stop confirmation shows the full name, host, available project
  context and the effects on all kernels. Internally pin/revalidate the UUID.
- An explicitly supplied UUID still appears in its confirmation/result. Preserve
  its confirmation-before-SSH ordering; do not fetch context first for that case.
- Missing name keeps current generated naming; no new mandatory naming prompt or
  implicit resume on a name collision. A terminal can always select by number.
- Token-free URLs can contain a UUID base path; this is not a credential to remember.
  Avoid printing the URL during successful automatic GUI access unless verbose.
- --verbose is curated detail, never raw SSH stderr, settings, cookies or a debug
  dump of objects. Reject doctor --report --verbose so the report path cannot
  acquire identifying verbose attachments by accident.
- Human wording such as “Jupyter is ready; continue in your browser” is appropriate
  after delivery. Never infer “browser authenticated” from a redeemed proof alone.

### 3.4 Reference human journey

Use this planned journey as the basis for CLI snapshots, demo assets and A23.
Assume an authorized SSH alias, an existing remote Jupyter Python, tmux and the
project directory; prerequisite failures remain doctor/SSH guidance, not installs.
All names/paths below are illustrative.

```console
jupyhop start workstation --server-python /opt/envs/research/bin/python --workdir '~/projects/analysis' --name analysis
# Native SSH prompts if needed; no new Jupyter-password prompt.
# Starting analysis on workstation...
# Jupyter is ready; continue in your browser.
# Ctrl-C closes this tunnel. The remote session is kept.
```

After Ctrl-C, return from the same or another authorized client:

```console
jupyhop resume workstation --name analysis
# Native SSH prompts if needed; automatic browser access, same live kernel.
jupyhop manage workstation
# Existing named inventory, counts and menu; select by number.
jupyhop stop workstation --name analysis
# Confirm the named pinned session, kernel termination and offered archive.
```

These are separate terminal interactions, not a shell script: resume stays
attached until Ctrl-C. An external server or an old password-only session keeps
normal Jupyter login with a clear explanation. A failed handoff says that start
was confirmed when applicable, gives `resume workstation --name analysis` and
leaves the session available; it never advises starting a duplicate session.

## 4. Authentication architecture

Keep stdlib-only client runtime, source bootstrap through OpenSSH and private
session runners. Add narrow modules, provisionally `auth.py`, `_auth_remote.py`
and `handoff.py`; reuse existing verification/transport code. No generic plugin
registry, browser debugger in production or permanently installed remote service.

### 4.1 New settings and remote launch

Registry header/records retain schema **1.0**, current UUID/base-path rules and
runner argv shape. Do not edit any old launch.py/settings.json or scientific
environment. New per-session settings get an independently named format:

```json
{
  "settings_schema": {"major": 1, "minor": 0},
  "lab": true,
  "auth": {"mode": "token"}
}
```

Password mode adds only a native Argon2 `password_hash` inside auth. No plaintext
password, token or cookie is written into these settings or registry records.
The remote loader explicitly recognizes the old unversioned password_hash/lab
format as legacy-password. Unknown formats/modes fail closed; never infer the
mode from the legacy runtime password boolean or an empty token alone.

For token mode, the **remote runner** generates `secrets.token_hex(32)` (256 bits)
for native PasswordIdentityProvider token authentication. Configure empty hashed
password, password_required=False, that nonempty token and
allow_password_change=False. This uses Jupyter's native token checking, not a new
authenticator. Clear JUPYTER_TOKEN/JUPYTER_TOKEN_FILE as today and retain isolated
configuration/imports, loopback binding, trust_xheaders=False and XSRF checking.
Password mode retains password_required=True, a native hash and token="".

Jupyter persists its token in its normal private runtime metadata; verify 0700
runtime/0600 files. Keep native cookie naming based on the final Host/port and
unique UUID base path. Qualify native HttpOnly/Lax cookie settings for this
controlled server mode. Stable per-session cookie names are deferred.

Assert nonempty token mode and refusal of unauthenticated protected API/WS access
before declaring ready. Keep private logs free of printed tokens/configuration
reprs: preserve the existing CRITICAL logging policy, explicitly supply the
runner-generated token, suppress unused native browser-open files, and check
startup/failure logs in A02 instead of assuming native defaults are secret-free.
No per-open token rotation: that could disrupt existing clients. Token and
cookie lifetimes remain native; the short-lived handoff proof is a different object.
Review runtime/log/archive/back-up exposure explicitly: file permissions are not
encryption. Do not add automatic evidence deletion or promise instant revocation
of existing SSH/browser sessions after an SSH key is revoked.

### 4.2 Native cookie issuance, with the token kept remote

After selection and verified forward allocation:

1. The client binds the exact UUID, observed endpoint and current remote identity
   to that owned connection; all later operations use its checked SSH master.
2. The remote operation derives the session from the current host/account registry,
   validates state/runner/settings/process/listener/runtime ownership and reads
   only the token for that selected declared token-mode session.
3. On **remote loopback**, it authenticates normally to the recorded Jupyter port.
   Compute the HTTP Host as `127.0.0.1:LOCAL_FORWARD_PORT`, so Jupyter issues its
   default cookie for the eventual browser Host. The integer port is the only
   client-supplied HTTP target component; no arbitrary URL/Host/path/file is accepted.
4. Accept only the native login redirect to the selected base path and the one
   expected auth Set-Cookie. Do not follow redirects or return arbitrary headers,
   response bodies, _xsrf cookies, native tokens or password hashes.
5. Revalidate identity before returning the cookie through the private SSH result.
   The client verifies its name, path, flags and scope, then probes the verified
   forward using this cookie without Authorization before preparing delivery.

For an immediate password-mode start only, the client can perform native
GET/login/XSRF/POST using its already-held password through the owned forward.
Use the same native-cookie validation/delivery code, then release references to
the password. No secure-memory-wipe claim or persistent client password cache.

Use stdlib HTTP with fixed loopback targets, explicit Cookie/Authorization
handling and no proxy environment or redirect following. Neither branch reads a
cookie-signing secret or manufactures a signed cookie. Jupyter's native
[IdentityProvider API](https://jupyter-server.readthedocs.io/en/stable/api/jupyter_server.auth.html#jupyter_server.auth.identity.IdentityProvider.get_cookie_name)
is the issuer; its Host-dependent naming is a compatibility gate, not an assumption
about all custom identity providers.

### 4.3 Private wire and payload contracts

Reserve **browser_auth wire 1.7** and **start wire 1.8** for this plan; these are
not shipped versions. Other operation minors retain their current contracts.
The registry version, settings format and CLI JSON are separate namespaces.

Start 1.8 has an explicit auth_mode token/password. Password is required only in
password mode and forbidden in token mode. The reply acknowledges that mode,
which the client checks before opening. Keep support for known legacy start 1.2
password requests in the new implementation/tests. Public launch JSON remains
the current projection: host/id/state/error/record_path/server/identity.

browser_auth accepts only protocol, operation, action, a bounded budget and
expected_identity, plus the action-specific fields below. A name may resolve a
nonsecret inspect request; the credential action always requires a pinned UUID.
No PID, prefix, filename, URL or arbitrary Host selector is accepted.

| Action | Additional input | Result |
| --- | --- | --- |
| inspect | Exactly one id or exact managed name; no endpoint/port/credential input | Nonsecret mode, name, abbreviated display context and a validated nonsecret managed candidate when available; no login or credential extraction |
| cookie | Exact observed_id and owned local_port | One opaque native Set-Cookie for that ready token-mode session, or a fixed refusal/manual-required result |

Expected identity is the already observed UID/user/current-boot scope; compare
it to the actual account/boot. Only the first inspect on an as-yet-unobserved
route may supply expected_identity=null: its actual reply then pins identity
for all later inspection/cookie/forward operations. Cookie always requires a
nonnull expected_identity and an already selected endpoint observation. **Never use identity.scope as a registry pathname**:
state_root computes its stable machine/account scope independently. The helper
checks immutable runner hash/argv/private manager evidence, PID start/socket
identity, no-symlink single-link file rules, native mode and known schemas. No
readiness reconciliation, registry mutation or server restart happens here.

A password/legacy mode returns manual_required without returning a hash. Missing,
unsafe, incompatible, changed or unconfirmed token-mode state is a refusal, not
an excuse to return another session's credential or fall back silently. Unmanaged
candidates never enter the cookie action.

Freeze request key names as `id`, `name`, `expected_identity`, `observed_id`,
`local_port` and `budget` (alongside protocol/operation/action). `expected_identity`
has uid/user/scope exactly as the current observation contract. Reject extra keys.
For inspect, exactly one of id/name is present and observed_id/local_port are
absent; cookie requires id, observed_id and local_port and forbids name. Reject bool
as a port/budget, nonfinite budgets and values outside 0.1–10 seconds. An
illustrative cookie request uses only synthetic nonsecret data:

```json
{
  "protocol": {"major": 1, "minor": 7},
  "operation": "browser_auth",
  "action": "cookie",
  "id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "expected_identity": {"uid": 1000, "user": "researcher", "scope": "bbbbbbbbbbbbbbbbbbbbbbbb"},
  "observed_id": "cccccccccccccccccccccccc",
  "local_port": 49152,
  "budget": 5
}
```

The response envelope has exactly protocol/operation/data. Data has the fixed
keys `id`, `identity`, `auth_mode`, `context`, `server`, `cookie`, `error`:

- id is the resolved/pinned UUID, or null when input/selection failed. Identity is the
  actual validated uid/user/scope, or null when it could not be established.
- auth_mode is token/password/legacy-password, or null on refusal. Context is
  null or name/project_display/python_display; the two path strings are display
  abbreviations only. Server is null or an existing validated nonsecret managed
  candidate shape, never raw runtime JSON.
- cookie is null for inspect, manual_required and every error. It can be a single
  bounded native Set-Cookie string only for a successful token-mode cookie action
  with matching identities and a verified ready candidate.
- error is null or one fixed code: invalid_request, not_managed, name_not_found, not_ready,
  manual_required, target_changed, unsafe_state, corrupt_state,
  incompatible_registry, incompatible_settings, credential_unavailable,
  native_login_failed, response_limit or budget_exceeded. Manual_required is
  legitimate only for a verified password/legacy mode. Other refusals return no
  context/server/cookie; they cannot authorize a manual downgrade.

Reconstruct these fields into checked types. Native token/password/hash/signing
secret fields are forbidden in the response, even if an untrusted reply tries
to label them diagnostic metadata. Unknown new operations or settings formats
require explicit support, not a guessed interpretation. The experimental branch
that returns tokens is comparison tooling and must not enter production.

Use a dedicated parser/type for the private result, with redacted repr and no
JSON/public-report serializer. Reject unknown versions/fields, duplicates,
nonfinite numbers, invalid Unicode/CRLF and wrong target identities. Separate
nonsecret context from the opaque cookie; generic discovery/diagnostic parsers
must never receive a secret response. Initial limits:

- Existing SSH stdin/stdout caps stay **64 KiB**; private auth replies at most
  **16 KiB**, one auth cookie at most **4096 bytes**. Display-only project/Python
  strings at most **256 UTF-8 bytes each**, explicitly abbreviated and never
  used for target resolution or filesystem access.
- Existing directory/record/name/registry bounds remain. Budget native HTTP work
  within min(5 seconds, remaining operation deadline); no unbounded retry.
- Measure actual JSON-encoded source bundles before adding code. Current discovery
  + managed sources consume 50,862 bytes before request fields; adding inventory
  uses 56,918. Password/path/Unicode encoding and new source all count toward 64 KiB.
  Reuse/extract small state-reading primitives if needed, without changing old
  runner bytes. Do not raise the cap or install a remote agent to avoid this work.
- Combined size limits can reject oversized inputs with a clear error before SSH;
  never truncate a credential/path used for an action. Test actual serialized
  payloads, not only individual field lengths.

### 4.4 Targeted access and display context

For an explicit managed name, resolve the current registry name once and pin its
UUID. For a known managed UUID, inspect that exact record. Use inspect's verified
candidate for this target. The current generic probe adds default paths even
when explicit sources are supplied, so merely passing fewer sources is not a
targeted verification. Add an explicit managed verification branch to
opening.open_connection: re-run inspect for the pinned UUID through the owned
Tunnel connection, compare identity/observed_id/state, and keep the local
endpoint/version/authentication check. Reuse existing remote _candidate and
managed provenance checks, never duplicate weaker versions of them. No unrelated
global runtime directories are scanned in this branch. A non-ready
record is not implicitly restarted/reconciled. Give the exact status/recovery
step when readiness is unconfirmed.

Manual login/default JSON retain the existing discovery/verifier path and do
not call browser_auth; this also preserves explicit normal access to otherwise
supported servers whose authentication metadata is not understood. Targeted
lookup is required for compatible managed targets in human/explicit-auto mode.
Do not quietly use manual discovery to recover from a failed automatic security
check; the user can deliberately choose manual login after a fresh verification.

Host-only open/manage still performs bounded discovery and shows the existing
chooser, including unmanaged candidates. Hostless open retains configured-route
inventory, per-route failures and ambiguity. Do not deduplicate duplicate aliases
by guessing that they grant interchangeable authority. Managed context is
optional display data; its absence never grants authority or changes a target.
Show project context only when already obtained; do not add auth RPCs to status,
stop/archive scripts or explicit-UUID confirmations just for formatting.

Default successful output can summarize partial coverage briefly and put details
behind --verbose. Zero candidates, failed routes, missing selected targets and
scan/time/registry limits still get explicit actionable uncertainty. A direct
lookup says which named managed record was checked; it does not claim exhaustive
discovery. Keep ordinary JSON coverage/diagnostics unchanged and unmanaged entries
clearly distinct from managed counts.

## 5. Local handoff contract

Implement the limited relay using stdlib HTTP parsing and independently tested
byte/deadline/concurrency wrappers, not a reverse proxy or a fork of an HTTP
parser. The prototype handler is evidence, not production code to copy unchanged.

| Property | Initial 0.4.0 contract |
| --- | --- |
| Listener | One invocation-owned IPv4 loopback listener, OS-selected port; never 0.0.0.0 or a shared arbitrary listener |
| Lifetime | 60 seconds from publication of the launch file, independent of SSH authentication timeouts |
| Proof | 32 cryptographically random bytes, single use, bound to exact UUID/forward/cookie and deadline |
| File | Exclusive no-symlink creation, mode 0600 under a new mode-0700 directory; proof/static form only, never native token/password/cookie |
| Browser launch | Private file URI via normal system browser handling; no secret in argv/URL; no access to a real browser profile/debugger |
| Accepted request | POST /handoff, exact loopback Host/port, Origin:null, form content type, one ASCII proof, exact Content-Length |
| Rejections | GET/HEAD/other paths/origins/hosts, duplicate/unknown form fields, malformed framing, Transfer-Encoding, excess body/headers, replay and expiry |
| Bounds | 16 KiB total request headers, 1 KiB body, at most 4 active connections, 2-second idle reads and 5-second absolute request deadline; global 60-second deadline always wins |
| Delivery | Atomically consume proof before headers, send only the validated Set-Cookie, no-store, no-referrer and a fixed 303 to the selected forward/base path |
| Success condition | Handoff response delivered; native cookie was validated through the forward. This is not a browser-login/kernel-health assertion. |
| Cleanup | Close accepted sockets/listener/workers and delete the private file/directory after delivery, expiry, graceful signal or failure; do not leave a broker attached for the entire notebook session |

Use correct error statuses with no cookie/header/body reflection. Add a restrictive
file CSP permitting only the static submit script and that form target. Disable
request logging; errors expose fixed codes, never request/header/body reprs. A
proof authorizes only cookie delivery, not any lifecycle operation. Ignore incoming
Cookie headers and forbid CORS wildcard/credential responses.

If the process is killed ungracefully, a private proof-only file can remain. It
must be expired/unredeemable without the owning broker; do not promise cleanup
under SIGKILL or secure deletion. No broad age-based cleanup of others' files.
TTL/limits are fixed initial constants, not a new set of everyday CLI knobs;
change them only with recorded gate evidence and updated tests/docs.

Cookie security retains native Jupyter/HTTP limits: [cookies do not isolate ports](https://httpwg.org/specs/rfc6265.html#section-8.5).
Tests must prevent broker/proof access by another UID and cross-session confusion;
they must not claim general isolation from hostile HTTP services at other ports
on the same loopback host. A UUID path/name is not an authorization secret. Record
this existing browser-cookie limitation in the security review; stop at G0 if the
accepted trust boundary cannot accommodate it. Never silently relax that boundary.

## 6. State, errors and recovery

Controller stages are explicit and bounded, not a new persistent state machine:
selected → forward_verified → native_cookie_ready → waiting_for_browser →
handoff_delivered → tunnel_attached → local_closed. Any pre-delivery stage can
fail/cancel. Manual login skips native-cookie/handoff stages. These stages are
local observations, never new remote registry states.

For start, retain request UUID plus whether a ready reply was actually confirmed.
If start is unconfirmed, show the exact request ID and status-before-retry step.
If readiness was confirmed and access delivery fails, report those outcomes
separately. Preserve the remote record/runner/server and offer resume by name
(or exact UUID when reconciliation needs it). Never stop/archive a new server
because browser launch or authentication delivery failed.

| Failure | Exit / resource behavior |
| --- | --- |
| Invalid flags or bounded input | 2; no SSH for locally detectable contradictions |
| SSH/access failure | Existing 3; no inference of current remote process death |
| Missing prerequisites | Existing 4 |
| Malformed/private incompatible/unsafe or wrong-identity result | Existing 5; fixed redacted diagnostic, refuse transfer |
| No candidate / selection ambiguity | Preserve existing 6/7 distinctions, including explicit missing UUID versus missing name/hostless selection |
| Forwarding failure | Existing 8 |
| Lifecycle, launch and partial-inventory outcomes | Existing 11–14; preserve their meanings |
| New browser-access issue/delivery failure or expiry | **15**, after disposing owned local handoff and forward; remote lifecycle unchanged |
| User cancellation / signal | Existing 130, phase-appropriate recovery and owned local cleanup |

Map private refusals consistently: name_not_found retains name-selection 7;
not_managed/not_ready retain no-candidate 6 for an explicit target. A received
invalid_request, target_changed, unsafe_state, corrupt_state, incompatible_registry,
incompatible_settings or response_limit is 5. credential_unavailable,
native_login_failed and budget_exceeded are 15. Locally rejected input is 2;
manual_required for a verified password mode selects normal login, not an error.
Transport exceptions keep their transport code rather than being wrapped as 15.

An SSH failure during an unconfirmed start remains launch-unknown (12). After a
ready reply, a subsequent SSH failure is an access-phase transport error, not a
claim that the start never happened. Local failure messages say what was last
observed and that no stop was requested; they do not assert continued server
liveness without a fresh successful observation.

A known password/legacy/unmanaged manual-required capability is a supported
fallback. Corrupt/unsafe/mismatched token state or a failed native login is not:
return the specific refusal/15 and an explicit safe recovery step. Do not issue
a secret URL or disable auth as a fallback. An auto timeout returns control to
the terminal after cleanup; resume never creates another server.

After successful delivery the forward remains attached. In manage, access errors
return to the menu through shared handlers. Keep D55 for Ctrl-C and possible
native SSH reauthentication; canceling a forward alone must not signal remote
Jupyter. Preserve unknown/lower-bound counters and archive behavior.

## 7. Work packages, dependencies and stop gates

Proceed **G0 → G1 → G2 → G3 → G4 → G5 → G6**. Human-formatting work can be developed
independently, but cannot stand in for authentication acceptance. Each package
needs a small coherent commit, its relevant tests and an evidence update.

| Gate | Deliverables / likely files | Exit criteria |
| --- | --- | --- |
| G0 — Close feasibility and threat review | Extend experiments/browser_handoff.py; review this plan and 04/09/10/12 contracts | Remote-only token/native-cookie Host proof, native browser launching, file/origin behavior on Chrome and Firefox, explicit trust/at-rest/expiry review. Record failures; no default switch on a failed gate. |
| G1 — Launch/settings foundations | managed.py, _managed_remote.py, protocol.py; shared state-reader extraction only if byte budget demands it | Both modes, settings reader, 1.8 acknowledgments, old Python callers, private runner permissions/immutability and serialized payload limits tested. Token mode initially opt-in during development. |
| G2 — Private native-cookie path | Proposed auth.py/_auth_remote.py; reuse existing state/process/forward checks | browser_auth 1.7 inspect/cookie, strict secret type/parser, cookie-only reply, unsupported/manual distinction, read-only registry and hostile-data/refusal tests. |
| G3 — Production handoff | Proposed handoff.py plus native browser-launch adapter | Real expiry-driven cleanup, strict framing/bounds, one-use races, signals, missing browser, no credentials in artifacts/output and actual browser HTTP/WS acceptance. |
| G4 — CLI/default/UX integration | cli.py, opening.py, controls.py, selection.py, discovery.py, fleet.py, errors.py | Complete option table, default switch only after G0–G3, code 15/phase recovery, names/context, targeted managed lookup, JSON/confirmation compatibility and shared manage path. |
| G5 — Qualification and documentation | tests, existing fixtures/upgrade/account/browser tools, docs, README, CHANGELOG and docs assets | All A01–A23 below observed; current UI/docs generated against implemented CLI, installed candidate, real account/SSH-password composition and unassisted reader review. No scientific workload fixture. |
| G6 — Numeric release/publication | Version/metadata, release checks, existing Conda and Pages workflows, evidence report | A24, reviewed 0.4.0 candidate, green exact-source jobs, one staged archive/four installed clients/digest-bound promotion/public receiving after explicit publication instruction. |

Keep the local config schema unchanged and optional; no auth secret is a TOML
field. Avoid clobbering shared names in the current exec-based remote source
bundles and test each bundle independently of a remote JupyHop installation.

Keep implementation work isolated until each coherent change is reviewable; direct
commits/pushes remain the maintainer's workflow and no PR is required. Do not
announce an implemented/default 0.4.0 capability while only a spike exists. A
candidate can use numeric 0.4.0 with clear unpublished status; never use b1/rc/dev
suffixes or create a tag/upload merely to test it.

Recommended commit units: launch wire/settings; shared read primitives if needed;
private auth/parser; bounded handoff; CLI/mode/error integration; human formatting
and direct lookup; cross-account/browser/upgrade gates; docs/assets/candidate
metadata; separate exact-file publication evidence. Do not combine all work into
one security-sensitive release commit.

## 8. Acceptance matrix

Evidence names below describe required cases, not tests that already passed.
Implement meaningful checks at the indicated boundary; do not duplicate private
helpers into tautological unit tests.

| ID | Required observation | Layer |
| --- | --- | --- |
| A01 | Default start never calls getpass/reads a Jupyter password; explicit/password-stdin mode and every invalid combination behave as section 3 | Unit + actual CLI/PTY |
| A02 | Token-mode API and WS reject anonymous/invalid credentials; valid cookie works; no token/hash in registry/settings/logs/argv | Managed integration |
| A03 | Cookie-only private reply for exact target, checked through the forward; source/runtime token sentinel absent from SSH reply/client diagnostics/public JSON | Private protocol + integration |
| A04 | Fresh independent keys/HOMEs/configs/browser profiles after all first-client resources close recover the same server/session/kernel/memory | SSH + browser + installed client |
| A05 | Password start asks/reads once and hands off without browser reentry; password is not retained locally | PTY + browser |
| A06 | 0.3 password-only sessions stay untouched and use browser login; no hash extraction/reset/restart | Legacy fixture + browser |
| A07 | Unmanaged token/password servers use normal login; spy proves no cookie credential action; stop/archive remain refused | Integration |
| A08 | Golden existing JSON shapes/exit codes/selection/stdout/stderr ordering and password-stdin automation stay compatible; explicit auto changes only documented delivery timing | CLI + installed |
| A09 | no-open creates no local resources; no-browser human file flow works; JSON/manual remains old flow; contradictions fail before SSH/stdin | Unit + browser/CLI |
| A10 | GET/HEAD/wrong target/Host/Origin/method/framing/content type, duplicate fields, oversized input, slow trickle and concurrent requests cannot obtain a cookie | Adversarial HTTP |
| A11 | Only one concurrent redemption succeeds; replay/real elapsed expiry fail, with no credentials in URLs/logs/errors | Relay + browser |
| A12 | Inject failure at each creation/verification/launch/delivery stage; graceful signals leave no file/socket/thread/forward; crashed proof-only leftovers cannot authorize another session | Failure injection + PTY/process tests |
| A13 | Native cookie scope/name/path/flags/redirect validation rejects substitution; interleaved sessions/ports/clients never deliver the wrong cookie | Protocol + multi-session browser |
| A14 | One/many/zero choices, exact names, UUID-looking names, truncated/Unicode contexts and multi-route duplicates are understandable without UUID copying | Selector tests + reader walkthrough |
| A15 | Name reuse/concurrent stop/archive cannot retarget the pinned UUID; explicit UUID still confirms before SSH; all-kernel effects and script --yes semantics preserved | Existing/new lifecycle integration |
| A16 | Many unrelated stale runtime files do not flood named access; missing/limited/failed coverage remains explicit; JSON information retained | Bounded lookup/discovery tests |
| A17 | Refusal/expiry/browser failure after ready returns the correct stage/code (5 for unsafe/incompatible results, 15 for delivery failures) without stopping server/kernel; immediate resume reaches same live computation | Integration + browser |
| A18 | SSH loss before ready versus after ready, port collision, state replacement, missing token, unsupported mode/provider and readiness uncertainty give truthful recovery | Fault injection |
| A19 | Installed 0.4 opens/manages unchanged 0.3 runners; 0.3 can still inspect/open-manually/stop/archive new compatible records; old 0.1/0.2 gates retained | Installed upgrades/older clients |
| A20 | Real distinct Unix accounts cannot read other's runtime/state/launch file/proof or obtain cookie for it; same-UID clients remain authorized; no privileged product action | Existing disposable account fixture/CI |
| A21 | Native SSH passwords and keys/agent, direct and ProxyJump routes, wrong fingerprints/cancellation; no Python SSH-password handling or fallback sockets | Native PTY/account/SSH acceptance |
| A22 | Required Python/Jupyter/browser combinations below pass; full browser login/HTTP/WS is separate from controller's delivery observation | Source + installed + browser matrix |
| A23 | New reader completes first start, named return, two-project choice, safe finish and one failed-handoff recovery without UUID/Jupyter-secret copying in auto mode | Unassisted disposable walkthrough |
| A24 | MIT/numeric metadata, exact candidate/upgrade/source/docs gates, one Conda archive and independent public install/docs receiving all agree | Release/publication |

Matrix minimum: all unit/SSH/API tests on Python **3.11/3.12/3.13/3.14**; new managed
modes on **Server 2.20.0 and 2.21.1**, plus a reviewed current maintained patch at
release time. Preserve existing older-server open/refusal comparisons. Full Chrome
and Firefox browser flows run at least on Python 3.14, including direct/ProxyJump,
automatic token, fresh password, legacy/unmanaged fallback and protected no-browser
file launch. Compose native SSH password auth with the new browser flow, not only
separate tests of each. Record exact versions/platform/package bytes.

Use the existing disposable real-account CI workflow where local provisioning is
unavailable; two keys for one UID are not proof of two-UID isolation. No lab
reboot, forced scientific disconnect/logout or real user's server is a fixture.
Reader observations are qualitative tasks, not a claimed conversion/time guarantee.

## 9. Compatibility and publication decisions

- Registry schema 1.0, runner argv shape, host/account scoping and pidfd/archive
  guards stay stable. No migration/rewrite of living launchers or older settings.
- Older 0.3 clients retain lifecycle and manual-open operation on compatible new
  records; automatic access needs 0.4.0. This is a required test, not permission to
  relax checks if an older client refuses a new runner.
- A 0.4 client uses manual login for old password sessions; it cannot derive their
  password from SSH/Argon2. Existing browser cookies follow native Jupyter policy.
- Keep ordinary JSON versions/fields and legacy status reconciliation separate
  from read-only summaries/context. No new secret field or implicit unmanaged adoption.
- Docs to update with implemented behavior: index/quickstart/installation,
  managed/existing/recovery/SSH/security, scripting/JSON/compatibility,
  troubleshooting/diagnostics/upgrading/releases/contributing. Regenerate parser
  help and demo assets; show both new automatic and legacy/manual paths.
- Source qualification includes wheel/sdist/clean client, current upgrade gates,
  packaging metadata and strict Sphinx/example/link/render checks. Preserve zero
  mandatory client Python dependencies and no mandatory remote installation.
- Publication uses the existing UIBCDF workflow: verify a free numeric coordinate,
  build/stage once, qualify four installed Python clients, promote those exact
  bytes and independently receive/install them. Do not overwrite 0.3.0 or a staged
  0.4.0 artifact. A failed candidate needs a reviewed new coordinate/build number.
- Preparing this plan is not authorization to upload a new release or tag.
  Complete/review all gates first; publication follows a concrete maintainer instruction.

## 10. Evidence, checklist and first implementation action

Experiment revision: **3c6c7dd**, extending the original **8e0d5e1** spike.
Observed during this plan review: `python -m experiments.browser_handoff
--remote-cookie` passed on Linux/Python 3.14.10/Server 2.21.1/Chrome
157.0.8103.38/default sandbox. The native cookie was issued remotely for the local
forwarding Host, and neither client's private SSH reply contained the runtime
token. Browser HTTP/WS, fresh-client kernel/session/memory continuity, password
compatibility and refusal/replay/expired-proof cases passed. This is a fixture-only
extension of the original spike; it does not implement the protocol/settings,
server mode, strict budgets or cleanup contract in this plan.
The original comparison invocation without --remote-cookie also passed after
this extension; Ruff lint/format passed. Local documentation checks passed for
five Markdown files, 89 relative file links, two JSON examples, four illustrative
CLI examples, balanced fences/whitespace, generic examples and agreement between
R01–R12, A01–A24 and the G0–G6 work/checklist entries. These do not replace a
production security/browser/upgrade test or a new source/Docs CI qualification;
the unchanged public docs and product are not redeployed by these planning commits.

- [x] G0 threat/native-browser gate closed for the tested Linux setup.
- [x] G1 launch/settings/byte-budget foundation complete.
- [x] G2 private cookie path and secret-type/refusal acceptance complete.
- [x] G3 bounded handoff and browser acceptance on the tested browsers complete.
- [x] G4 default/CLI/UX behavior implemented and verified in the source fixtures.
- [ ] G5 all A01–A23, installed/source/docs and reader acceptance recorded.
- [ ] G6 A24 and separately authorized publication/receiving recorded.

The [implementation report](36-04-implementation.md) records the qualified
source revision and private package checks. The [physical-client pilot](37-04-physical-client-pilot.md)
adds guided operator evidence with successful automatic access, named/menu
return, expired-link recovery and independent completion. It does not close
A23's unassisted new-reader requirement.

The first implementation task is **G0**, followed by the source-bundle/settings
work in G1. Do not begin by wiring the experimental HTTP handler directly into
open or by changing the default password prompt before the bounded handoff is
qualified. Record each gate's changed files, commands, results, exact revisions,
remaining limits and next step in an implementation evidence report. **0.4.0 is
complete only when its required gates have observed acceptance**, not when the
prototype or this plan looks convincing.
