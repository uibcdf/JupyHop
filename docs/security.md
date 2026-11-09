# Security and credentials

Jupyter grants code execution to authenticated users. Use JupyHop only with
accounts and SSH routes you are authorized to access. The supported security
boundary trusts your client, OpenSSH configuration, selected remote Python/
environments and authenticated remote account.

## Two authentication steps

- **SSH:** OpenSSH handles keys/agent and native terminal password/passphrase
  prompts. Python does not read/cache the SSH password. Verify host fingerprints
  through a trusted channel, including gateway hosts.
- **Jupyter:** use its normal login page with the existing password/token. For a
  new managed server, choose a separate new Jupyter password. Its hash is stored
  privately; plaintext is not retained by JupyHop.

JupyHop opens token-free local URLs. It does not bypass login, put credentials in
argv or silently adopt another user's server. Browser-cookie validity remains
Jupyter's policy. Headless/`--batch` operation needs authorized noninteractive SSH.

## Ownership and local access

Supported Jupyter endpoints and local forwards use IPv4 loopback. Discovery checks
current-account ownership, private runtime metadata, live process/socket identity
and recognizable authentication behavior. Existing metadata is never deleted.

Only exact verified managed UUIDs authorize stop. Stop uses graceful pidfd
signalling and refuses uncertainty. Archive requires inactivity and retains
private records/settings and possible kernel recovery files. Keep archives
private; they may contain sensitive material. Neither operation acts on an
unmanaged server or provides cross-user sharing.

Loopback prevents public listening but is not an account-authentication boundary:
other processes/users on the same computer may be able to reach a loopback
listener. Keep Jupyter authentication enabled on both the remote endpoint and
the locally forwarded route. A printed token-free URL alone is not a credential.

An invocation owns its private SSH connections and explicit forwards. Unrelated
listeners or arbitrary shared masters are not adopted. SSH agent/X11 forwarding,
host-key bypass and automatic credential handoff are not introduced.

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
