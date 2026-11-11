---
myst:
  html_meta:
    description: "Understand JupyHop SSH and Jupyter authentication, ownership checks, private settings, safe session control and vulnerability reporting."
    "property=og:description": "Understand JupyHop SSH and Jupyter authentication, ownership checks, private settings, safe session control and vulnerability reporting."
---

(security-and-credentials)=
# Passwords and security

Jupyter grants code execution to authenticated users. Use JupyHop only with
accounts and SSH routes you are authorized to access. The supported security
boundary trusts your client, OpenSSH configuration, selected remote Python/
environments and authenticated remote account.

## Two authentication steps

- **SSH:** OpenSSH handles keys/agent and native terminal password/passphrase
  prompts. Python does not read/cache the SSH password. Verify host fingerprints
  through a trusted channel, including gateway hosts.
- **Jupyter:** use the server's own password or token when its login page
  appears. JupyHop opens new token-based managed sessions automatically.
  Existing password-based sessions use their existing Jupyter credentials.

In 0.4.0, the managed server keeps its token in private remote runtime metadata.
After SSH authentication and session verification, Jupyter issues a native cookie
over remote loopback. JupyHop carries the cookie through the owned SSH connection
and delivers it to the local browser using a private, single-use file. The link
expires after 60 seconds. URLs stay free of credentials. Existing password
sessions and servers started elsewhere retain their native login. A password
chosen with `--auth password` is hashed in private remote settings.

Run JupyHop on the browser computer. Keep both computers and their loopback
services trusted. The browser scopes cookies by host and path, and cookies can
be sent to other ports on the same host. Jupyter sets the cookie's lifetime.
See [HTTP cookie port scope](https://httpwg.org/specs/rfc6265.html#section-8.5).

## Ownership and local access

Supported Jupyter endpoints and local forwards use IPv4 loopback. Discovery checks
current-account ownership, private runtime metadata, live process/socket identity
and recognizable authentication behavior. Existing metadata is never deleted.

Only exact verified managed UUIDs authorize stop. Stop uses graceful pidfd
signalling and refuses uncertainty. Archive requires inactivity and retains
private records/settings and possible kernel recovery files. Keep archives
private; they may contain sensitive material. Neither operation acts on an
unmanaged server or provides cross-user sharing.
Human names and numbered choices are resolved once to that exact UUID and checked
again by the existing backend. Name reuse cannot silently retarget an action.
Terminal stop offers archive only after confirmed stop; scripts authorize that
extra phase explicitly. Pre-selection inventory may authenticate through SSH,
but no lifecycle mutation is authorized before confirmation.

Loopback prevents public listening but is not an account-authentication boundary:
other processes/users on the same computer may be able to reach a loopback
listener. Keep Jupyter authentication enabled on both the remote endpoint and
the locally forwarded route. A printed token-free URL alone is not a credential.

An invocation owns its private SSH connections and explicit forwards. Unrelated
listeners or arbitrary shared masters are not adopted. OpenSSH continues to
verify host keys for each route.

## Protect your environment

Keep SSH, runtime, state and local application configuration permissions private.
OpenSSH configuration may execute trusted local commands, and remote Python can
execute code in its environment; select both deliberately. JupyHop does not
protect against root, a malicious same-UID process or a compromised authorized
remote host.

Remote logout policy, process loss and reboot can destroy workloads. A new tunnel
cannot restore kernel memory. JupyHop does not change site persistence policy or
restart a lost kernel automatically.

## Report a concern

Follow the canonical [security reporting policy](https://github.com/uibcdf/jupyhop/blob/main/SECURITY.md).
Use private vulnerability reporting when available; otherwise request a private
contact without disclosing details publicly. No independent-audit or guaranteed
response-time claim is made.

Do not attach real passwords, private keys, token URLs, cookies, raw runtime/
settings/kernel files, browser profiles or scientific infrastructure details.
Use generated examples and redacted versions/command shapes. General failures
can be reported through [GitHub issues](https://github.com/uibcdf/jupyhop/issues).
The [support report](diagnostics.md) excludes identities/paths and credentials by
construction; review it before sharing. Other JSON and terminal transcripts are
not automatically suitable for public reports.
