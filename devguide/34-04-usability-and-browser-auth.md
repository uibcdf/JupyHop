# 34 — 0.4.0 direction: fewer decisions, transparent browser authentication

Date: 2026-11-10. Baseline: published **0.3.0**, source **ce63bf7**.
Experiment commit: **8e0d5e1**.
Status: **historical analysis with an experimental proof of feasibility**.
The requested release now has a detailed [0.4.0 implementation plan](35-04-implementation-plan.md).
That plan is authoritative for scope, CLI/wire/settings choices and gates; it
refines the design to issue cookies remotely instead of bringing the native token
to the client. The original analysis/evidence below is retained by date. No 0.4.0 client,
managed authentication mode, package or release is implemented by this document.
The current [authentication](09-session-lifecycle-and-auth.md),
[security](04-security-and-reliability.md) and [UX](12-user-experience.md) contracts
remain the shipped behavior. This analysis follows the
[0.3.0 usability work](30-03-implementation.md) and
[documentation rewrite](33-documentation-onboarding-implementation.md).

## Recommendation

Make 0.4.0 a consolidation of the everyday journey: **authorized SSH access →
choose a named project → work in Jupyter**. Preserve the CLI verbs and current
lifecycle safeguards. Prioritize:

1. Automatic browser authentication for **new compatible managed sessions**, with
   no human-chosen Jupyter password by default. Let standard Jupyter authenticate;
   remove the user's repeated secret-entry work.
2. Names and useful context in ordinary human output. Keep UUIDs internally and
   in automation/recovery details, rather than requiring users to memorize them.
3. Brief successful output and precise, phase-specific recovery instructions.
   Reuse existing optional profiles instead of adding a mandatory setup wizard.

The recommended authentication candidate is a native server-generated credential
read privately through verified SSH, exchanged for a Jupyter-issued browser
cookie. The local browser handoff below has worked in disposable experiments.
It needs production hardening, version/browser qualification and a reviewed
remote credential protocol before adoption as a release default.

## What is actually causing friction?

| Item | Meaning | Proposed everyday treatment |
| --- | --- | --- |
| Managed UUID / unmanaged observation ID | Identifies a server; does not grant login | Names and numbered choices. Full IDs remain available for scripts and uncertain operations. |
| Jupyter token | Bearer credential granting server access | Internal where a reviewed automatic flow is supported; never ordinary list/discover output. |
| Jupyter password | Another way to authenticate to Jupyter | Optional deliberate password mode or compatibility fallback; avoid entering the same secret twice. |
| SSH key, agent or account password | Authenticates the SSH connection | Continue delegating to OpenSSH; neither Jupyter nor Python receives the private key or SSH password. |

0.3.0 already supports names, resume and selectors. The remaining identifier
problem is presentation: ordinary rows, URLs, confirmations and start progress
still emphasize UUIDs. Changing that does not require replacing stable IDs or
overloading positional IDs with names. A UUID in a base path is not a token and
need not be memorized; its unique path is also useful for cookie separation.

The current start sequence asks for a new password, confirmation, SSH login and
then the same Jupyter password in the browser. The password choice in M3 protected
credentials at rest and made independent-client login predictable; the normal
login page was a deliberately conservative baseline. It is not a requirement
that every future release repeat that interaction.

## How SSH can make browser login transparent

SSH and Jupyter are different authentication systems. A browser does not normally
understand an SSH key, and merely being on the computer that created a server is
not proof of authorization. Other local processes can reach loopback too.

Reuse the **authenticated SSH channel**, not the key material:

1. OpenSSH verifies host trust and authenticates the desired remote Unix account,
   through any configured gateway. Keys/agent and native SSH passwords both work.
2. JupyHop resolves the chosen session and verifies its account, managed provenance,
   process/listener identity and endpoint. The name is resolved to one exact UUID.
3. For a supported new managed server, a dedicated private operation obtains its
   native credential from the account's restricted runtime data. It is not added
   to discovery, ordinary JSON, registry summaries or support reports.
4. Through the verified tunnel, the client authenticates to normal Jupyter and
   obtains a cookie **issued by Jupyter**, not forged from its signing secret.
5. A protected, short-lived local handoff delivers that cookie to the browser,
   which then opens the existing SSH-forwarded Jupyter endpoint normally.

No mandatory remote JupyHop installation, browser extension, JupyterHub or central
service is needed by this candidate. The ordinary SSH forward continues carrying
HTTP and WebSockets. It works with password-authenticated SSH too; keys are not
an additional prerequisite. A new invocation still needs valid SSH access. This
does not turn past authorization into a permanent device authorization.

Jupyter documents token authentication by header/form and cookie-based subsequent
requests in its [security guide](https://jupyter-server.readthedocs.io/en/stable/operators/security.html).
The installed Server 2.21.1 source also confirms that a valid token-authenticated
request can issue a login cookie. The flow uses that standard behavior.

## Proposed authentication cases

| Server | Proposed 0.4.0 behavior | Important limit |
| --- | --- | --- |
| New compatible managed server | Native random credential; automatic browser login by default | Credential exists internally, with a reviewed private retrieval/storage policy. Authentication is not disabled. |
| Existing 0.3.0 managed server, password-only | Preserve it; use normal browser login, or accept the password once in an explicit client-assisted flow and hand off the resulting cookie | SSH does not recover a plaintext password from Argon2. No automatic reset, runner rewrite or restart. |
| Deliberately selected password mode | A supplied/new password can authenticate the immediate browser automatically | Future clients still need that password unless another reviewed credential path exists. |
| Existing unmanaged token server | Keep current normal login initially; evaluate explicit opt-in private token access separately | Discovery never grants lifecycle control or authorizes arbitrary credential harvesting. |
| Password-only unmanaged server, custom provider or unsupported browser | Clearly explained normal login fallback | Do not reconfigure the server, weaken authentication or claim universal automatic login. |

An old hash-only server cannot become fully transparent just because its client
was updated. A managed-auth default applies to **new launches**. Existing running
sessions and their kernels must remain untouched.

The internal token is not eliminated or made a one-use credential by this design.
It has native Jupyter's lifetime; so does the browser cookie. Only the local
handoff proof is one use and short lived. Remote plaintext bearer material is a
real tradeoff against the present hash-only managed settings. Native runtime
permissions are access control, not encryption; backups, logs, archive retention
and credential rotation need an explicit review. No new permanent client vault
is proposed.

## Candidate browser handoff

Opening a normal HTTP URL through a system browser does not supply arbitrary
headers or install a cookie by itself. Authenticating a Python HTTP client alone
is therefore insufficient. Avoid solving this with the user's real browser
profile/debugger, which would add broad access and fragile browser dependencies.

The prototype uses a narrow, transient loopback HTTP endpoint, inside the client
invocation, plus a private HTML launch file:

1. Obtain a native authenticated cookie for the actual forward's host/port/path.
2. Start a bounded-lifetime handoff endpoint on another owned loopback port.
3. Write a mode-0600 file under a mode-0700 temporary directory. It contains an
   unpredictable 256-bit one-use proof, not the Jupyter token/password/cookie.
4. Open that file. Its HTML form POSTs the proof; the proof is not in the URL or
   browser-launch arguments. The endpoint checks the target, method, host, origin,
   proof, expiry and one-use state.
5. Return the native Set-Cookie and a redirect to the real forwarded Jupyter URL.
   Retire the proof/file/endpoint. No sustained HTTP/WebSocket reverse proxy is added.

Cookies are **not isolated by TCP port**; they are matched by host/path and other
attributes. This property enables the relay, but it is also a security limitation,
as described in [RFC 6265](https://httpwg.org/specs/rfc6265.html#section-8.5).
Jupyter's [cookie-name behavior](https://jupyter-server.readthedocs.io/en/stable/api/jupyter_server.auth.html#jupyter_server.auth.identity.IdentityProvider.get_cookie_name)
uses the request host, including its port, by default. Obtain the cookie against
the final forwarding URL and preserve its exact scope; do not invent a generic
cookie for every server. Retain unique managed base paths. Ignore incoming cookie
headers at the local relay and never echo/log them.

This mechanism is a **candidate**, not production-ready code. In particular,
file-to-loopback desktop-browser behavior, request timeouts/concurrency bounds,
expiry-driven cleanup, hostile local traffic, cookie scope/cross-session isolation
and native browser launching need further validation. A local Origin:null request
alone is not authorization; only the unguessable private proof can authorize this
handoff. The prototype's browser automation is test tooling, not a product dependency.

A smaller complementary option deserves a separate test: configure a stable
**per-managed-session cookie name** through native IdentityProvider.cookie_name.
It could keep the same browser logged in when a new forward chooses a different
port, without fixing local ports or storing a client password. It does not
solve the first login or a fresh client's login, and cannot be imposed on an
old running launcher. Never use one global cookie name for every server; verify
cookie/path/signing isolation and logout behavior before relying on this. The
current spike uses Jupyter's default host/port-dependent names, so this option
is not yet experimentally qualified.

## Alternatives considered

| Alternative | Benefit | Cost / disposition |
| --- | --- | --- |
| Reuse a just-entered password to log in once and hand off the cookie | Small transition that removes the immediate browser repetition | Demonstrated; retains password creation and later password knowledge. Useful fallback, not the full default UX goal. |
| Native random token + protected cookie handoff | No new Jupyter password to remember; independent authorized clients can retrieve access over SSH | Recommended candidate. Requires dedicated credential handling and review of remote bearer material. |
| Put a native token in the browser URL | Standard, simple implementation | Long-lived bearer exposure in launch arguments/history; not the recommended default. A private token redirect file avoids argv exposure but still places the token in browser URLs. |
| Cache a user password/token on each client | Could reduce later prompts | Creates a secret store, revocation and new-client restoration problem. Not required by the SSH-authorized model. |
| Derive Jupyter credentials from an SSH private key or authenticate against authorized_keys in Jupyter | Appears to reuse identity directly | Couples secrets and risks reimplementing SSH key/certificate/command restrictions. Keep verification in OpenSSH. |
| Read Jupyter's signing secret and manufacture a cookie | Could bypass a missing password | Bypasses native login, couples to internals and expands secret handling. Reject. |
| Custom remote IdentityProvider / Unix-socket credential broker | Could support server-issued short-lived grants without a reusable runtime token | More remote code/protocol/compatibility burden. Revisit only if native mechanisms cannot meet the reviewed boundary. |
| Disable Jupyter authentication because SSH succeeded | Removes prompts | Reject: loopback is not account authorization. |

## Release priorities and boundaries

| Priority | Work | Done when |
| --- | --- | --- |
| P0 | New-managed automatic authentication and compatible fallback | A prepared user starts and later resumes from a fresh authorized client without choosing, copying or entering a Jupyter secret in automatic mode. |
| P0 | Human-oriented selection/output | Normal open/resume/manage/stop needs names/numbers and recognizable project context, with no UUID copying. Exact target pinning and confirmations remain. |
| P1 | Clear success and failure phases | SSH, launch readiness, forwarding and browser authentication are distinguishable. Browser handoff failure leaves the server intact and suggests reopen, never a blind second start. |
| P1 | Reduce irrelevant discovery noise | Retain explicit partial-coverage information and useful warnings; stop flooding a successful named resume with unrelated stale metadata. Consider direct verified managed lookup for --name before a broad search. |
| P1 | Predictable first setup and repeat use | Use existing optional profiles, explain helper/server/kernel roles and guide a missing prerequisite. No automatic Conda installation/activation or mandatory wizard. |
| Separate spike | Keep SSH authentication alive inside manage after closing only a forward | Demonstrate native terminal passwords/cancellation and clean owned-resource lifetimes before changing D55. Do not block the main auth/UI improvement on an unproven job-control refactor. |

The menu already reuses an invocation-owned connection, and pooled tunnel close
can cancel only a forward. The remaining complication is real: Ctrl-C can also
signal the foreground OpenSSH master, so 0.3.0 explicitly discards it. Keeping it
alive requires terminal/process-group work, not simply removing discard. Preserve
private native SSH prompts and cancellation; do not introduce Python password
capture, adopt arbitrary masters or reconnect silently after an unexpected lost
socket. Keys/agent remain the simple OpenSSH option for repeated invocations.

Keep the current verbs and the terminal chooser even for one candidate (explicit
pilot feedback). Exact --name can skip the chooser. An unarchived name collision
must not silently resume, replace or create another server. Prefer useful name,
project/environment and state context in human rows; show full IDs in details,
automation and uncertain-operation recovery. Option spelling for any details mode
is not decided here.

Do not expand this increment into macOS, Slurm, another supervisor, cross-user
sharing, a central portal, background tunnel management or kernel restoration.
Archive completion already exists in 0.3.0; automatic deletion is not needed to
solve this authentication/usability problem.

## Compatibility and security acceptance before adoption

- Negotiate a dedicated private credential capability/result; preserve ordinary
  CLI JSON schemas and never route a secret reply through generic diagnostics.
  Use explicit capabilities/auth-mode metadata rather than guessing from the
  legacy runtime password flag or an empty token alone (see the M0 observations).
  Define headless/JSON opt-in and no-browser launch-file behavior before coding it.
- Preserve --password-stdin script intent and existing stop/archive UUID/--yes
  semantics. No invisible interactive prompts or implicit target choices.
- Verify selected remote UID/host/boot, immutable managed runner, PID start and
  listener identity, runtime directory/file ownership/modes/no-symlink rules and
  bounded parsing. Revalidate before credential delivery; refuse stale or wrong
  targets. Neither a PID nor a loopback URL is sufficient.
- Exercise launch/relay failures, missing or changed runtime tokens, unsupported
  providers, browser absence, replay, expiry, concurrent opens, cross-session
  cookie confusion and other local Unix users. A same-UID compromise/root remain
  outside the existing trust boundary, not solved by this feature.
- Keep unauthenticated API/WebSocket access refused. A token-mode launch must
  establish a nonempty native credential, never an empty-token/empty-password
  configuration.
- Keep tokens, passwords, cookies and proofs out of normal stdout/stderr, argv,
  environment variables, URLs and support reports. Protected launch-file proof
  and normal browser cookie storage need their own documented lifetime; no claim
  of erasing browser history bodies or securely wiping immutable Python strings.
- Handle Ctrl-C/SIGTERM/HUP and timeouts without orphaning local handoff services,
  exposing a reusable file or stopping a healthy remote server/kernel.
- Qualify native SSH passwords and keys/agent, direct and ProxyJump routes, custom
  supported base paths, all Python 3.11–3.14 clients, Server 2.20/2.21.1 and chosen
  maintained patches, at least the supported desktop browsers, and the actual
  installed candidate. The current experiment is not that matrix.
- Test 0.4 clients against unchanged 0.3 runners/registry and explicitly decide
  the older-client behavior on new token-mode servers. Do not rewrite live runners
  or edit schema versions to make a compatibility check pass.
- Run the unassisted walkthrough from the documentation audit against the new
  interaction: first start, second-client resume, two named projects, safe finish
  and one failed handoff. Observe prompts, wrong turns and external help; do not
  substitute an API test for reader comprehension.

## Reproducible evidence observed

Run from the checkout with existing experiments dependencies, OpenSSH server/client,
tmux and Chrome:

```console
python -m experiments.browser_handoff
```

Observed on Linux with Python 3.14.10, Jupyter Server 2.21.1 and Chrome
157.0.8103.38/default sandbox:

- A fixture-scoped private read reused the current ownership/process/listener
  checks and retrieved the native runtime token through the selected verified
  SSH connection. It returned only to the experiment, not normal discovery output.
  A mismatched selected identity and a temporarily nonprivate fixture file were
  refused. This is not a general production managed-credential operation.
- Native token authentication returned a Jupyter-issued HttpOnly login cookie.
  A protected file POSTed only a one-use proof to the local relay; Chrome then
  reached JupyterLab without a login form. No insecure browser flag or disabled
  Jupyter XSRF/host checks was introduced.
- Browser cookie-authenticated HTTP/session creation and WebSocket execution
  succeeded. After closing every first-client browser/tunnel/relay, a different
  key/config and clean browser profile recovered the same notebook session,
  kernel ID and in-memory marker, printing **42**.
- A current 0.3 managed password-only fixture also reached an authenticated browser
  through the relay. Its synthetic password was still needed by the native
  login exchange; it was not reconstructed from SSH or its stored hash.
- GET, an invalid proof, wrong Origin and wrong Host were refused without setting
  a cookie. Consumed and deliberately expired proofs were refused too. The expiry
  test advanced the prototype's deadline; automatic expiry cleanup is not thereby
  established.
- Browser navigation-history **URLs** contained neither the Jupyter credential
  nor the one-use proof. All fixture servers, kernels, brokers, browser profiles
  and client connections were cleaned. No scientific server/session was used.

This proves feasibility on one server/browser combination. It does not establish
Firefox/desktop-portal behavior, the production headless contract, adversarial
cross-account isolation of the new broker, native SSH-password composition,
production request-resource bounds or a release-ready credential protocol.
No published client or user authentication configuration was changed.
The optional experiment passed its local execution plus Ruff lint/format and
whitespace checks; 83 local Markdown file links and private-identifier checks
also passed. No new full hosted/release qualification is claimed by this design
spike. Public guide inputs and product code are unchanged.

## Decisions still to make

1. Accept the usability goal and select the native-token candidate after its
   security review; retain password-only compatibility without weakening it.
2. Choose the private credential capability, auth-mode metadata and version
   negotiation rules; avoid a registry migration unless actually necessary.
3. Choose supported browser launch/fallback behavior and the expiry/resource
   bounds. The prototype's 60-second proof is an experimental value, not policy.
4. Define exactly what normal output shows and which details remain explicit;
   preserve the established one-candidate chooser and lifecycle safety.
5. Treat management-connection retention and any first-use profile helper as
   independent, evidence-driven work rather than expanding the P0 release scope.

Next recommended work: review this proposal, then implement the private auth
capability and one complete start/resume vertical slice behind explicit gates.
Only after security, compatibility, installed-package and reader acceptance
should **0.4.0** be published. This document creates no version tag or upload.
