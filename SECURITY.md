# Security policy

JupyHop 0.3.0 is the published pre-1.0 Conda release for Linux. It is not an
independently audited product. The
supported boundary is described in [compatibility](docs/compatibility.md) and the
[threat model](devguide/04-security-and-reliability.md). Use the current reviewed
release; historical public releases do not receive backported security fixes.

Jupyter grants code execution to its authenticated users. JupyHop trusts the
installed client, your local OpenSSH config (including ProxyCommand/Match exec),
selected remote Python/environments and the authenticated remote account. It
does not protect against a malicious same-UID process, root or a compromised
authorized remote host. Separate Unix users remain separate authorization scopes.

OpenSSH handles the route and host trust; target connections enforce strict host
checking. Configure trusted host keys on jump aliases too. Native terminal SSH
password/passphrase prompts and keys/agent are supported; headless/--batch needs
noninteractive access for every hop. Python does not read/cache SSH passwords.
An invocation owns its foreground masters and permits no mux reconnect fallback.
No host-key bypass, SSH agent forwarding, public Jupyter binding,
automatic token handoff or plaintext credential cache is introduced. Private
settings retain password hashes; runtime/archive evidence may contain kernel
secrets and must stay private. Normal Jupyter login/cookie policy still applies.

Only verified managed identities may be stopped, using graceful pidfd signalling.
There is no PID-only fallback or automatic SIGKILL. Archive preserves inactive
evidence; it is not a general cleanup command. Site logout policy and process loss
can defeat persistence, and no tool can recreate lost kernel memory by forwarding
a port. Read [troubleshooting](docs/troubleshooting.md) before manual recovery.
Terminal names/choices pin the exact managed UUID before confirmation; they do
not grant lifecycle authority. Interactive stop offers guarded archival after a
confirmed stop; script UUID/--yes remains stop-only unless --archive is explicit.
Overview/history reads never delete or archive. Shareable diagnostic reports
allowlist metadata and exclude identities/paths; ordinary JSON still needs review.

## Reporting a vulnerability

Use GitHub private vulnerability reporting if enabled for this repository. If no
private reporting channel is available, open an issue requesting a private contact
without disclosing vulnerability details or secrets. Do not put exploit details
or credentials in public issues while arranging that contact. No response-time
or independent-audit guarantee is made.

Provide affected versions, a minimal reproduction using disposable loopback
fixtures, expected/observed behavior and impact. Never send private keys, active
tokens/passwords/cookies, raw runtime/settings/kernel files, browser profiles or
institutional machine details. Retain sensitive evidence privately.
