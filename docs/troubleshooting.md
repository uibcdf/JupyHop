# Troubleshooting

Begin with `jupyhop --version`, `jupyhop COMMAND --help` and ordinary
`ssh workstation`. Commands use SSH aliases; put User, addresses, keys and
ProxyJump in OpenSSH config. Local SSH configuration, chosen Python executables
and the remote account are trusted inputs. Raw SSH logs can contain private
infrastructure details and must be reviewed before sharing.

| Symptom / exit | Action |
| --- | --- |
| Invalid arguments/config (2) | Check command help, TOML version/known fields and file ownership/permissions. Config is at most 64 KiB, regular, single-link, without final symlink or group/other write access. |
| SSH/access/timeout (3) | Verify the route with ordinary SSH, including the gateway. Check selected User and host trust. Use a controlling terminal for native OpenSSH password/passphrase prompts; headless/--batch requires keys/agent or another noninteractive method. --ssh-auth-timeout bounds terminal authentication. No conclusion about remote session state follows. |
| Host-key mismatch | Verify the new fingerprint independently, then manage known_hosts through your normal SSH procedure. Never disable verification as a workaround. |
| Missing prerequisites (4) | Read the specific error. `doctor` checks Jupyter only in its selected interpreter. A stdlib-only helper can still discover a server in another environment. Managed start additionally needs compatible Jupyter, tmux, kernels and a valid remote directory. |
| Invalid remote JSON/schema (5) | Check login-shell banners and the supported helper/client versions. Unknown state versions are refused; do not edit schema numbers or delete state to force acceptance. |
| No verified candidate or selected ID absent (6) | Discovery is partial. Add known `--runtime-dir` paths or repeat `--remote-python`. Rediscover a replaced endpoint. Check private metadata permissions and the supported endpoint matrix. Do not infer that no server exists. |
| Selection failure (7) | Select on a terminal or give an exact server ID. For hostless open, inspect `list --json` and choose an explicit route with `open HOST ID`; zero fleet candidates also use 7. Names/PIDs are not session selectors. |
| Forwarding failure (8) | Check SSH server forwarding policy, local loopback access and the bastion. A new owned port is selected automatically. No remote server is stopped. |
| Lifecycle refusal (11) | Use an exact managed UUID in the selected account/host registry. Unmanaged servers cannot be stopped; live or uncertain entries cannot be archived. Recheck status and preserve evidence. |
| Launch unconfirmed/failed (12) | Record the printed request UUID and inspect status/discover before another start. A server may already exist. Check the remote Python, workdir, version and tmux availability. |
| Stop/archive pending (13) | The action's result is unknown. Inspect status after stop; retry archive with the same UUID. No forced kill or automatic deletion is attempted. |
| Partial fleet result (14) | Read each host's result; successful routes remain usable. `list` returns 3 when all selected routes fail, 0 when every route was inspected, even with no ready servers. |
| Interrupted (130) | Owned local SSH resources are closed. Remote start/stop may already have taken effect; reconcile before retrying. Closing an open forward does not stop remote Jupyter. |

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
| `entry_limit`, `time_limit`, `output_limit`, path `limited` | The bounded search was curtailed; narrow the known runtime paths or investigate the specific environment |
| `interpreter_unavailable` | At least one selected helper could not run; diagnose that interpreter separately with doctor |
| `managed_state_unavailable` | Managed registry access/validation failed; inspect status and private evidence, keeping incompatible/corrupt records intact |
| `unsupported_address`, `https_or_unix_socket`, `legacy_metadata` | The endpoint/metadata is outside the current compatibility boundary |
| `unverified_process_or_listener`, `process_or_file_gone` | Metadata does not currently establish a live owned listener; rediscover without removing unrelated records |
| `endpoint_unavailable`, `unsupported_jupyter_or_auth` | Check the selected server's readiness, supported API/authentication and endpoint configuration |

Original runtime metadata is never deleted by discovery. Stale entries in a
partial report are diagnostics; they do not authorize lifecycle control.

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

Include the client/helper/Python/Jupyter/OpenSSH/tmux versions, command shape,
exit code, platform and a redacted description of direct versus ProxyJump access.
Replace aliases, account names and paths with examples. Do not attach raw runtime
JSON, settings, kernel connection files, browser profiles, cookies, private keys,
token URLs or server logs. Follow [SECURITY.md](security.md) for security reports.
