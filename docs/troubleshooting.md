---
myst:
  html_meta:
    description: "Fix common JupyHop problems: SSH permissions, missing servers, password prompts, tmux visibility, timeouts and browser connection errors."
    "property=og:description": "Fix common JupyHop problems: SSH permissions, missing servers, password prompts, tmux visibility, timeouts and browser connection errors."
---

# Troubleshooting

Begin with `jupyhop --version`, `jupyhop COMMAND --help` and ordinary
`ssh workstation`. Commands use SSH aliases; put User, addresses, keys and
ProxyJump in OpenSSH config. Local SSH configuration, chosen Python executables
and the remote account are trusted inputs. Raw SSH logs can contain private
infrastructure details and must be reviewed before sharing.

## Find your next check

New to JupyHop? The [Quickstart](quickstart.md) shows the expected successful
route. If a step went differently, start here:

| What you see | Next check |
| --- | --- |
| “Bad owner or permissions” | [Inspect the exact SSH configuration file](#bad-owner-or-permissions-on-ssh-configuration) |
| No verified server found | [Locate the server's runtime directory or Python](#ssh-works-but-discovery-is-empty) |
| A password prompt you do not recognize | [Identify which login is asking](#which-password-do-i-use) |
| Connection timed out during start | [Inspect the printed request before retrying](#ssh-times-out-during-a-start) |
| tmux works in a shell but start cannot find it | [Check the noninteractive SSH PATH](#tmux-works-interactively-but-start-reports-missing-tmux) |
| A browser connection error after Ctrl-C | [Reopen the tunnel](#can-i-close-this-terminal) |
| Browser opens, but login or notebook execution fails | [Check the current URL, credentials and kernel](#the-browser-opens-the-wrong-page-or-cannot-log-in) |
| You need help reporting a bug | [Generate and review a support report](#reporting-a-problem) |

## Which password do I use?

| Where the prompt appears | Password to use |
| --- | --- |
| OpenSSH prompt in the terminal | That SSH account's password or key passphrase; a gateway can ask separately |
| New Jupyter session password during start | In 0.3.0 or with `--auth password` in 0.4.0, choose and confirm a password for this session |
| Jupyter's browser login page | The chosen managed-session password, or the existing server's own password/token |

If you never set a password for a manually started Jupyter, it may use a token
from its original private startup output. An SSH password is not that token.
JupyHop does not retrieve existing credentials or reset them. See the
[two authentication steps](security.md#two-authentication-steps).

## Can I close this terminal?

While open/start is attached, the terminal keeps your local tunnel alive.
Ctrl-C closes that tunnel and can leave the browser showing **Server Connection
Error**. This is expected; it does not by itself mean the remote server stopped.
Run open/resume again to get a current URL and log back in. Keep the command
running while using that URL.

Managed servers use tmux and existing servers use their original launcher;
site policy still controls remote process lifetime. To end a managed server
and its computations deliberately, use [stop](managed-sessions.md#stop-explicitly).
[Recovery](recovery.md) explains how to find the original living kernel again.

## Bad owner or permissions on SSH configuration

This message comes from OpenSSH before it can use the affected configuration;
it is different from a rejected SSH password or Jupyter login. JupyHop 0.3.0
classifies configuration failures and gives a conditional ownership/write remedy.
It identifies a local default file only when the native message and actual file
metadata support that conclusion. Unknown include/gateway locations remain
qualified; run ordinary SSH privately to see the exact native path. Earlier
0.2.0 feedback could be generic even when OpenSSH showed the original rejection.

For an error naming your local ~/.ssh/config, inspect it on the **client**:

```console
ls -ld ~/.ssh ~/.ssh/config
```

If this is your ordinary configuration file, owned by your account, and it permits
group/other writes, restrict that exact file and retry ordinary SSH:

```console
chmod 600 ~/.ssh/config
ssh workstation
```

Write access is the relevant issue: upstream OpenSSH rejects 0664, while 0644
normally passes; 0600 also keeps configuration private. Debian/Ubuntu can accept
group write when the group contains only the owner, as their
[manual explains](https://manpages.ubuntu.com/manpages/resolute/man5/ssh_config.5.html#FILES).
Keep OpenSSH as the authority rather than using the mode alone to predict a
failure. A .ssh directory already at 0700
needs no permission change for this file-specific failure. SSH configuration can
select destinations and commands, so unauthorized edits can affect connections.
The [OpenSSH manual](https://man.openbsd.org/ssh_config#FILES) describes the
configuration-file restrictions.

If ownership is wrong, chmod does not correct it: establish the intended owner
with your administrator before changing ownership. For --ssh-config, included
files or an error from a gateway-side SSH process, identify the exact file and
machine first. Avoid recursive permission changes or assuming every named path
belongs to the local client. Once ordinary SSH succeeds, retry JupyHop.
The default-file check is not a universal preflight for explicit -F files:
OpenSSH accepted 0664 for that separate case in the experiment. JupyHop retains
OpenSSH's policy, recommends private files and never silently repairs permissions.

## SSH times out during a start

A printed request UUID followed by **Connection timed out during banner
exchange** does not establish whether a remote server exists. Keep the request
UUID and inspect before repeating start:

```console
jupyhop discover workstation --timeout 120
jupyhop status workstation --timeout 120
```

Read warnings as well as session rows. If the existing request appears, inspect
that exact UUID and reconcile its state rather than creating another session.
An unsuccessful inspection, registry error or unknown/starting state is not
evidence that nothing started. A successful inventory establishing that the
request has no registered session can inform a deliberate retry; the new request
has a new UUID.

--timeout changes the connection/handshake and probe bounds; --ssh-auth-timeout
separately bounds terminal authentication. Both can matter on password jump
routes. Later success with --timeout 120 does not by itself establish why an
earlier attempt timed out. If SSH itself still fails, diagnose the route first;
increasing a deadline cannot repair an incorrect alias, host trust or permission.

## Paths, environments and authentication

`--remote-python` selects the helper; `--server-python` selects the managed server
environment. Profiles choose executables/workdirs, not Conda activation or kernel
environments. The notebook's chosen kernel may be from a different kernelspec.
Remote paths resolve on the remote account; quote `~/project` to avoid local shell
expansion. Workdirs allow canonicalized symlinks; security-sensitive runtime/state
paths reject them. This distinction is intentional.

When credentials change, use a fresh authorized login. JupyHop has no credential
cache or password reset feature. Existing browser-cookie validity is Jupyter's
policy. The same browser may retain a previous Jupyter cookie; open a private
window when diagnosing login. Never disable Jupyter authentication.

If a managed name remains reserved after a verified stop, archive that exact UUID.
Archives retain sensitive hashes and possible kernel recovery files: keep them
private. There is no permanent-delete or automatic orphaned-kernel cleanup command.

If the remote OS reboots, processes vanish, or site policy kills a workload, no
reconnect can recreate kernel memory. A network failure alone is not evidence of
such process loss. Explicitly recheck after access is restored.

## SSH works, but discovery is empty

1. In the remote shell/environment that launched Jupyter, locate its Python and
   actual runtime path using [Prepare the remote host](remote-setup.md#find-an-existing-environment).
   A helper with no Jupyter packages can still discover private runtime metadata.
2. On the local client, run `jupyhop discover workstation --runtime-dir /absolute/remote/runtime --json`.
   Read `coverage.paths`, `coverage.issues`, and any candidates' `state`/`reason`.
   For several known environments, repeat `--remote-python` with absolute paths.
3. If no server has been launched, choose a manual launcher or
   [managed start](managed-sessions.md). `open` only opens an existing verified
   endpoint. Missing metadata cannot be replaced with an arbitrary `--url` or
   `--port`; those options are not implemented.

| Diagnostic | What to check |
| --- | --- |
| Path `missing` | Confirm the runtime path visible to the actual server, including its launch-time environment variables |
| Path `unsafe` | Check ownership, private permissions and symlinks on that exact path; do not recursively chmod shared/scientific directories |
| `sample_limit` | The retained diagnostic sample filled. Later verified candidates are still considered within scan/time bounds. It does not mark a completely scanned directory limited or count every stale server/file. |
| `scan_limit` or path `limited` | A directory reached the 512-entry scan bound. That directory's coverage is partial. |
| `entry_limit` | Legacy combined marker, retained alongside the more precise limits in 0.3.0. More SSH timeout cannot enlarge scan/sample limits. |
| `time_limit`, `output_limit` | The probe deadline or output bound curtailed the result. Inspect known paths/environments and distinguish those bounds before changing a deadline. |
| `interpreter_unavailable` | At least one selected helper could not run; diagnose that interpreter separately with doctor |
| `managed_state_unavailable` | Managed registry access/validation failed; inspect status and private evidence, keeping incompatible/corrupt records intact |
| `unsupported_address`, `https_or_unix_socket`, `legacy_metadata` | The endpoint/metadata is outside the current compatibility boundary |
| `unverified_process_or_listener`, `process_or_file_gone` | Metadata does not currently establish a live owned listener; rediscover without removing unrelated records |
| `endpoint_unavailable`, `unsupported_jupyter_or_auth` | Check the selected server's readiness, supported API/authentication and endpoint configuration |

Original runtime metadata is never deleted by discovery. Stale entries in a
partial report are diagnostics; they do not authorize lifecycle control.
Dozens of stale rows do not mean dozens of servers need stopping. The retained
sample is not a count of every stale file or every live server on that host.
Human discover/list summarize these unmanaged diagnostics by default. Use --all
for individual rows or --json for the complete bounded result. Managed records
remain visible, including stopped/review entries; inspect status for their
overview and archive history.

## tmux works interactively but start reports missing tmux

From the local client, check the noninteractive remote command environment:

```console
ssh workstation 'command -v tmux'
jupyhop doctor workstation --remote-python /absolute/remote/env/bin/python
```

The `missing_tmux` launch diagnostic refers to that command environment.
An interactive Conda activation may expose tmux while ordinary SSH commands do
not. Selecting `--server-python` does not activate that environment or prepend
its bin directory to PATH. Make tmux available through the permitted remote
shell/site configuration, then recheck. Keep noninteractive startup output clean
for JSON probes. A doctor result of systemd-user available does not select a
systemd backend: managed launch currently uses private tmux.

## A module imports interactively but doctor or start cannot find it

If a module imports in an interactive shell but doctor/start reports it missing,
check the chosen Python with isolated imports as described in
[Environments](environments.md#match-the-interpreters-import-mode). User-site or
`PYTHONPATH` packages are not sufficient for the remote helper/server.

## The browser access link expired

In 0.4.0, open the private file link on the same computer within 60 seconds.
When it expires or the browser cannot open it, run resume again with the same
session name. The error message includes the command. You can add
`--no-browser` to choose a browser yourself.

```console
jupyhop resume workstation --name analysis --no-browser
```

If start reached readiness, resume creates a new tunnel to that session.
If readiness could not be confirmed, inspect the printed request UUID with
status before repeating start.

## The browser opens the wrong page or cannot log in

Use the exact current URL printed by the active invocation, on the same computer
that runs JupyHop. A URL saved from an earlier tunnel can have a different port.
Running `--no-browser` on a gateway does not expose that gateway's loopback to a
laptop; [run the client on the browser computer](ssh.md#replace-a-fixed-localforward-workflow).

Enter the Jupyter password/token in Jupyter's form; the SSH password does not
authenticate the Jupyter session. With an existing token-auth server, obtain the
token privately from its original authorized launcher. If browser cookies cause
confusion, try a private window and fresh login. Managed JupyHop has no password
reset feature. A plain Jupyter Server environment may provide only its server/API
view; notebook editing requires a frontend such as JupyterLab in that environment.

If login works but the notebook cannot execute, inspect the selected kernelspec
and its remote dependencies. Discovery/readiness do not execute a kernel.
[Register a separate kernel](environments.md#make-another-python-available-as-a-notebook-kernel)
when needed. A stopped/crashed kernel's memory cannot be recovered by opening its
notebook file.

## Reporting a problem

Use [doctor --report](diagnostics.md#prepare-an-issue-attachment) for versioned
shareable context, or the optional notebook-local check when a kernel is involved.
Review the output before sharing; ordinary --json is not the public-report mode.

Include the client/helper/Python/Jupyter/OpenSSH/tmux versions, command shape,
exit code, platform and a redacted description of direct versus ProxyJump access.
Replace aliases, account names and paths with examples. Do not attach raw runtime
JSON, settings, kernel connection files, browser profiles, cookies, private keys,
token URLs or server logs. Follow [SECURITY.md](security.md) for security reports.

## Error codes

For automation, see [Scripting and exit codes](scripting.md#exit-codes). These
checks retain uncertainty about remote state after a transport failure.

| Symptom / exit | Action |
| --- | --- |
| Invalid arguments/config (2) | Check command help, TOML version/known fields and file ownership/permissions. Config is at most 64 KiB, regular, single-link, without final symlink or group/other write access. |
| SSH/access/timeout (3) | Verify the route with ordinary SSH, including the gateway. Check selected User and host trust. Use a controlling terminal for native OpenSSH password/passphrase prompts; headless/--batch requires keys/agent or another noninteractive method. --ssh-auth-timeout bounds terminal authentication. No conclusion about remote session state follows. |
| Host-key mismatch | Verify the new fingerprint independently, then manage known_hosts through your normal SSH procedure. Never disable verification as a workaround. |
| Missing prerequisites (4) | Read the specific error. `doctor` checks Jupyter only in its selected interpreter. A stdlib-only helper can still discover a server in another environment. Managed start additionally needs compatible Jupyter, tmux, kernels and a valid remote directory. |
| Invalid remote JSON/schema (5) | Check login-shell banners and the supported helper/client versions. Unknown state versions are refused; do not edit schema numbers or delete state to force acceptance. |
| No verified candidate or selected ID absent (6) | Discovery is partial. Add known `--runtime-dir` paths or repeat `--remote-python`. Rediscover a replaced endpoint. Check private metadata permissions and the supported endpoint matrix. Do not infer that no server exists. |
| Selection failure (7) | Select on a terminal, give an exact server ID or use an exact current managed --name for open/status. Automated lifecycle still requires UUID/--yes. Hostless open/selection can also use 7; PIDs never select sessions. |
| Forwarding failure (8) | Check SSH server forwarding policy, local loopback access and the bastion. A new owned port is selected automatically. No remote server is stopped. |
| Lifecycle refusal (11) | Use an exact managed UUID in the selected account/host registry. Unmanaged servers cannot be stopped; live or uncertain entries cannot be archived. Recheck status and preserve evidence. |
| Launch unconfirmed/failed (12) | Record the printed request UUID and inspect status/discover before another start. A server may already exist. Check the remote Python, workdir, version and tmux availability. |
| Registry full (12, registry_full) | All 128 unarchived slots are used. Inspect status and archive a verified inactive entry. This refusal happens before creating the new request's record/server; existing records remain intact. |
| Automatic browser access failed (15) | In 0.4.0, resume the same session for a new link. Use --no-browser to open the link yourself on this computer. |
| Stop/archive pending (13) | The action's result is unknown. Inspect status after stop; retry archive with the same UUID. No forced kill or automatic deletion is attempted. |
| Partial fleet result (14) | Read each host's result; successful routes remain usable. `list` returns 3 when all selected routes fail, 0 when every route was inspected, even with no ready servers. |
| Interrupted (130) | Owned local SSH resources are closed. Remote start/stop may already have taken effect; reconcile before retrying. Closing an open forward does not stop remote Jupyter. |

**Next:** retry the relevant [Quickstart step](quickstart.md) after the check,
or use [Diagnostics](diagnostics.md) when you need a report.
