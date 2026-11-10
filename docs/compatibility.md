# Compatibility and version policy

JupyHop 0.3.0 is the current public Linux Conda release. Compatibility means the specific
workflows/versions observed below, not every Jupyter Server 2 deployment. The
client needs OpenSSH and CPython 3.11–3.14; it has zero mandatory Python packages
and needs no local Jupyter. Free-threaded Python, macOS and Windows are untested.
The Conda recipe restricts installation to Linux via __linux and Python
>=3.11,<3.15, and supplies OpenSSH. Noarch describes the Python payload, not a
claim of macOS/Windows support. See [Conda evidence](https://github.com/uibcdf/jupyhop/blob/main/devguide/24-conda-publication.md)
and [the future macOS investigation](https://github.com/uibcdf/jupyhop/issues/2).

## Endpoint and remote requirements

| Operation | Requirements / supported boundary |
| --- | --- |
| SSH | Existing authorized alias, trusted host keys, POSIX-compatible remote shell. Keys/agent and native terminal password/passphrase prompts; headless/--batch requires noninteractive access. OpenSSH handles Include/Match/ProxyJump. Jump-host configuration is trusted too; individual MFA variants are untested. |
| Discover/open | Linux remote helper Python >=3.11 (stdlib sufficient), readable private current-user runtime metadata, verified current-user process and IPv4 loopback TCP listener, recognizable Jupyter 2 API/auth behavior. |
| HTTP/URLs | `127.0.0.1`, HTTP, normal password/token login and simple ASCII base paths including WebSockets. No automatic credential handoff. |
| Unsupported endpoints | Public/wildcard listeners, IPv6-only, HTTPS, Unix sockets, legacy nbserver metadata, exotic auth/proxies. Refused or labeled unsupported; no TLS/host-key bypass. |
| Managed start | Existing Python >=3.11, Jupyter Server >=2.20,<3, usable kernelspec, tmux and a readable stable Linux machine ID; selected directory must exist. Server 2.21.1 is the recommended tested stack. |
| Safe stop | Linux pidfd support (kernel >=5.3), exposed by Python or named libc wrappers. Otherwise refused. No PID-only or forced-kill fallback. |
| Persistence | Private tmux, subject to site PAM/cgroup/last-logout policy. Browser/tunnel closure and two hours of real-site disconnected computation are tested. Configured site KillUserProcesses=false/Linger=no was observed; physical last logout/reboot/network moves remain unmeasured. |

Remote helper Python and server Python may differ. Conda/venv/system executables
are selected directly, without activation or remote installation. Notebook kernels
are chosen by their kernelspec and may use another environment.

SSH configuration is resolved for a transport-only master (`ssh -N`). Use aliases
with a stable destination/account; per-command Match rules cannot switch routes
or identities between RPCs on that authenticated connection. Mux clients use only
the owned socket and cannot fall back to a fresh connection if it is lost.

## Observed matrix

M5 verified all 258 earlier tests and clean-wheel workflows on CPython 3.11.18,
3.12.16, 3.13.18 and 3.14.10 with Server 2.21.1. M6 adds signal handling, live
password rotation, an 8 MiB content roundtrip and 64 executions with 64 KiB output
each on one sustained WebSocket through ProxyJump. See
[the M6 report](https://github.com/uibcdf/jupyhop/blob/main/devguide/20-m6-beta-readiness.md) for the local experiments and
[the hosted CI follow-up](https://github.com/uibcdf/jupyhop/blob/main/devguide/21-m6-github-ci.md) for the M6 270-test
baseline on each supported Python. Subsequent [0.2.0 stabilization evidence](https://github.com/uibcdf/jupyhop/blob/main/devguide/23-02-stabilization-evidence.md)
records additional tests, native terminal authentication and real-site observations.
The [physical home-client pilot](https://github.com/uibcdf/jupyhop/blob/main/devguide/28-02-physical-client-pilot.md)
observes the 0.2.0 gateway route and concurrent sessions. The
[0.3.0 implementation report](https://github.com/uibcdf/jupyhop/blob/main/devguide/30-03-implementation.md)
separately records the new candidate's local/hosted/installed qualification; old
passing runs do not substitute for that acceptance.

| Server / server Python | Existing open + kernel | Managed start/status/stop/archive |
| --- | --- | --- |
| 2.17.0 / 3.11.18 | Passed with an explicitly started server port | Refused before registry creation; native port=0 metadata is incorrect |
| 2.20.0 / 3.11.18, Tornado 6.5.8 | Passed | Passed |
| 2.21.1 / 3.11.18, 3.12.16, 3.13.18, 3.14.10 | Covered by the four-version regression / clean-wheel acceptance | Covered by the same tests |
| 2.17.0 / 3.12.11, real Linux target | Manual open/private login passed; no kernel was executed in this manual fixture | Below the managed minimum; not launched |
| 2.21.1 / 3.14.7, real Linux target | Manual open/private login passed | Start/reconnect/same live kernel after 7200 disconnected seconds, graceful stop and archive passed |

These are feature-compatibility observations, not a recommendation to install old
server versions. Upstream fixes matter: Server 2.20 corrected reporting the bound
port for port=0; 2.21.1 corrected compatibility with Tornado 6.5.9+. Prefer an
up-to-date supported server stack. The older 2.20 comparison pins Tornado below
that change; no compatibility with every newer dependency is claimed. See the
[Jupyter Server changelog](https://jupyter-server.readthedocs.io/en/stable/other/changelog.html).

The native 2.17 observation explains why an ephemeral-port managed launch cannot
be supported by simply accepting any 2.x release. It does not invalidate opening
an existing 2.17 server with correct private runtime metadata. The earlier
Alpine/QEMU attempt did not establish a platform-wide incompatibility; musl/Alpine
managed operation remains unvalidated.

Local Linux and Ubuntu hosted GitHub CI results are both observed; the linked
CI follow-up records successful four-Python regression/clean-wheel jobs,
server-version comparisons, Chrome/JupyterLab and actual Unix-account isolation
with cleanup. Chrome acceptance is separate from API tests. This evidence does
not establish compatibility with other operating systems, real-site logout
policies or physical network moves. Those boundaries and the installed-client
upgrade are tracked in [0.2.0 scope](https://github.com/uibcdf/jupyhop/blob/main/devguide/22-02-stabilization.md) and
[observed acceptance](https://github.com/uibcdf/jupyhop/blob/main/devguide/23-02-stabilization-evidence.md). The tested
real-site OS is x86_64 Ubuntu 26.04.1; other Linux distributions are not certified
by that observation. Physical-client and site-policy limits remain explicit.

## Client, wire and state versions

| Contract | Current version / behavior |
| --- | --- |
| Client package | Published Conda 0.3.0=py_0, qualified on Python 3.11–3.14; no PyPI publication |
| Doctor wire | 1.0 |
| Managed start wire | 1.2; version refusal is a new allowlisted error |
| Discovery wire | 1.6; distinct sample/scan limit diagnostics, retaining legacy entry_limit |
| Status/stop wire | 1.3; existing scripting output preserved |
| Archive wire | 1.4, sent only for explicit archive |
| Managed/history inventory wire | 1.5, read-only with bounded archive pages |
| Support report / managed inventory JSON | Independent version-1 output contracts; opt in with doctor --report or status --history --json |
| Remote registry | Schema 1.0; exact known schema required for writes |
| Local TOML / list JSON | Separate version-1 contracts; discover keeps its single-host shape |

Read-only parsers validate majors, types, bounds and allowlisted fields; unknown
secrets are not copied into generic output. The client sends its own source
bootstrap through verified SSH; there is no installed remote package to upgrade.
Managed servers retain their original immutable runner/hash. Changing the client
does not rewrite a running launcher, migrate state or install dependencies.

Legacy M3 and M5 runners are tested with the beta client's status and idempotent
stop without replacement or schema migration. Unknown/incompatible state fails
closed. Arbitrary historical/future client combinations, migrations and downgrade
after a future schema change are not promised. Back up private recovery evidence
before any explicitly reviewed future migration; never edit version numbers to
force compatibility.
