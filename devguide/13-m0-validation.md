# 13 — M0 design validation

Date: 2026-11-07. Scope: design feasibility, **not a shipped discover/open or
managed-session implementation**. Read together with [decisions](07-decisions.md)
and [traceability](14-acceptance-ledger.md).

## Reproduction and isolation

In an isolated Linux development environment, install experimental dependencies:

```console
mamba install -c conda-forge pytest ruff mypy python-build setuptools jupyter_server ipykernel requests websocket-client
python -m experiments.m0_spike --second-python /absolute/path/to/another/conda/env/bin/python
```

The second interpreter must already have Jupyter Server, jupyter_core and
ipykernel. No environment is activated or modified by the experiment. OpenSSH
client/server and tmux must be installed. Run as a non-root account; `/run/sshd`
must exist. Tests need permission to create loopback sockets.

`experiments/lab.py` creates two unprivileged loopback sshd processes with fresh
keys, pinned host keys and private temporary configuration. `Include`, `Match`
and `ProxyJump` are resolved by OpenSSH. Both endpoints use the current Unix
account on the **same machine**: this proves the SSH jump mechanism, not physical
network isolation or cross-account isolation. No production SSH config is read.
The fixture alone sets server `StrictModes no` because this sandbox maps `/tmp`
to a non-root owner; generated keys remain in a private 0700 directory with
0600 permissions. Client host-key checking remains strict.

Only private tmux sockets and randomly named transient systemd units created by
the experiment are stopped. Jupyter configuration, runtime data and logs live
under the temporary directory; tokens are never printed. Kernels are explicitly
deleted through their fixture server before cleanup. Never run destructive
reboot/logout or process-control tests on a scientific host.

## Observed matrix and results

Linux; OpenSSH 10.2p1; Python 3.14.10 and 3.14.9 in two existing Conda
environments; Jupyter Server 2.21.1; jupyter_core 5.9.1; ipykernel 7.4.0;
websocket-client 1.9.2; tmux 3.6. These are observations, not a universal support
matrix. See the final M1 report for automated compatibility coverage.

| Experiment | Result | Consequence |
| --- | --- | --- |
| Direct SSH and two sshd endpoints through ProxyJump | Correct UID on target | Delegate routing and identities to OpenSSH |
| Remote argument containing spaces, Unicode, quotes and shell substitutions | Literal round trip | Local argv alone is insufficient; quote remote argv for the POSIX login shell |
| Two Conda interpreters with the same HOME | Same default runtime directory | Environment prefixes are not runtime inventories |
| Explicit custom runtime directory | Not visible from the other interpreter's defaults | Probe explicit interpreters/paths; report partial coverage |
| Two manually launched servers in different Conda environments | Distinct ephemeral remote ports, runtime JSON 0600 / directory 0700 | Jupyter can allocate ports with `port=0`; runtime identity still needs validation |
| Stale fixture runtime metadata passed to `list_running_servers()` | Jupyter deletes the file | Do not use that API for read-only unmanaged discovery |
| Unauthenticated API and invalid token through jump | HTTP 403 | Tunnel never replaces Jupyter authentication |
| Generated token POSTed to `/science/login` with XSRF cookie | Cookie-authenticated API succeeds | Normal form login works without token query strings |
| Password configured through modern identity provider | Empty token; successful password login; legacy runtime `password` flag false | Neither field establishes auth mode or an auth-disabled server |
| Kernel API + WebSocket through jump and custom `/science/` path | Execute succeeds | Preserve base paths in HTTP and WS URLs |
| Client A forward closed, client B new forward and WebSocket | Same kernel ID; variable value 12345 survives | Tunnels can be independent of server/kernel; this is an API client simulation, not GUI acceptance |
| Occupied local port | OpenSSH exits on bind failure | Prechecks cannot reserve a port; retry after actual bind failure |
| Concurrent forwards and remote servers | Distinct local/remote ports | Ports identify routes, not sessions |
| Private tmux server launched through SSH | Jupyter and kernel survive launching SSH exit and later tunnel exit | Viable persistence candidate under tested session policy |

Probe output also records user-manager availability and tests a disposable
`systemd-run --user` unit across the launching SSH command's exit when available.
This does **not** test the final login session ending.

Observed here: the user manager was active in the development shell, but the
disposable **no-PAM SSH context could not start a user unit**. The fixture does
not inherit the client's bus/session environment. No backend assumption may be
based merely on finding `systemctl` or on local-shell availability. This negative
result is a reason to retain capability checks and evaluate realistic login
sessions before M4, rather than force systemd or copy a client's bus environment.

## Decisions and security boundaries

1. **M1/M2 need no installed remote package or daemon.** Send a small read-only
   Python probe over SSH stdin. M1 diagnoses one explicit interpreter (default
   `python3`); M2 may add explicit runtime paths/interpreters. Never enumerate all
   scientific environments or install anything remotely without authorization.
2. **Discovery is read-only and partial.** Later M2 reads bounded JSON itself,
   with ownership, mode, symlink, schema, process and endpoint checks. Never use
   PID-only checks or loopback reachability as ownership proof. Never stop an
   unmanaged server. Metadata and server output are untrusted.
3. **Authentication baseline: normal Jupyter login.** Open a token-free login
   URL; the user supplies their existing password/token. No JupyHop credential
   cache and no tokens in generic stdout/JSON/argv. Automatic token handoff is
   deferred until a browser-specific protected flow is reviewed in M2. POST
   feasibility alone does not solve transferring cookies into a user's browser.
   A token redirect file would introduce local plaintext storage/history risks;
   direct token URLs expose secrets in browser-launch arguments/history. Neither
   is selected as the default. An independent authorized client can authenticate
   normally using the same credentials without any previous client's state.
4. **Foreground tunnels for the initial M2 implementation.** Keep `open`
   attached, document Ctrl-C/terminal close, create a fresh owned forward on each
   invocation, and close only that forward. No daemon/control-socket reuse in
   product code yet. The experimental control socket is only a fixture readiness
   mechanism. No automatic server restart after reconnect or network loss.
5. **Process-manager selection stays capability-dependent until M3/M4.** Prefer
   systemd user services where the manager and logout policy support them; tmux
   is a candidate fallback, not a universal guarantee. Explicit `Restart=no`
   avoids concealing kernel loss. Never enable linger or change logind policy.
   Bare `nohup`/double-fork would make ownership, logging and recovery harder;
   do not add a custom supervisor before evidence requires it.
6. **Versioned read-only probe, no registry writes.** JSON envelope
   `{"protocol":{"major":1,"minor":0},"operation":"doctor","data":{...}}`.
   Major mismatch fails closed, extra minor fields ignored, stdout bounded to
   64 KiB, stderr to 32 KiB; banners/trailing text/malformed UTF-8 fail closed.
   Parsed fields are allowlisted. SSH errors never echo raw remote output.
   Installed lifecycle helper and registry schemas remain separate future
   contracts; no bootstrap/cache/update races exist for stdin probes. Reject
   unsupported registry writes before any future update; never upgrade a helper
   or stop workloads automatically.
7. **Python baseline:** local/remote Python >=3.11, Linux first; no local Jupyter
   runtime dependency. This is a narrow compatibility target requiring CI at the
   floor. Remote discovery Python and server/kernel Python may differ.
8. **Future managed identity:** random UUID scoped to verified remote account,
   independent of alias/display name/port. Persist under XDG state in 0700
   directories using atomic writes, per-account locks and versioned records.
   Validate boot ID + PID start time + supervisor identity + endpoint before
   stop. Reboot invalidates prior live identity. These are requirements, not
   implemented persistence. Workdir `~` expands only for the remote current
   user, relative paths resolve against its home, explicit interpreter paths
   avoid activation, and whitespace/Unicode remain literal; validate permissions
   remotely before future launch.

## Alternatives and primary references

An installed helper offers a stable lifecycle API but introduces maintenance,
upgrade and state-migration costs unnecessary for read-only diagnostics. A
copied cached helper additionally needs secure atomic installation and concurrent
update tests. An stdin probe avoids both for M1/M2, at the cost of requiring a
known Python interpreter and bounded strict serialization.

OpenSSH joins remote arguments into a command interpreted by the remote shell;
see [ssh(1)](https://man.openbsd.org/ssh). Its existing
[configuration](https://man.openbsd.org/ssh_config) handles host identity and
route selection. Jupyter documents token/password login and browser cookies in
[server security](https://jupyter-server.readthedocs.io/en/stable/operators/security.html).
Its [runtime paths](https://docs.jupyter.org/en/latest/use/jupyter-directories.html)
are configurable. Source inspection of installed Jupyter 2.21.1 additionally
confirmed the stale-file side effect and legacy password field behavior above.

systemd's [linger contract](https://www.freedesktop.org/software/systemd/man/latest/loginctl.html)
and [logind policy](https://www.freedesktop.org/software/systemd/man/latest/logind.conf.html)
explain why surviving one SSH command is weaker than surviving the last logout.

## M0 acceptance and deferred evidence

Every scenario has a release gate and planned test in the ledger. NET-08 is an
explicit connectivity boundary: JupyHop cannot create an inbound authorized route
to an unreachable client. Managed and unmanaged authorization remains distinct.
The login fallback and no-install probe remove security blockers to M1/M2.
M0 acceptance is **design-baseline complete**, not M2/M4 feature acceptance.

Still required before advertising support: actual browser cookie/history and
WebSocket UX, different physical clients, last-login logout/linger policy on a
disposable OS, two real Unix accounts, IPv6, HTTPS hostname mismatch, host reboot,
interrupted managed start/stop, state locks and migrations. Reboot and logout
were deliberately not performed on this development host. None blocks read-only
M1; they remain explicit M2–M6 gates. Next milestone: M1 SSH foundations.
