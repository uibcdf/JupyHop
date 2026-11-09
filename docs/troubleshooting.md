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
| No verified candidate (6) | Discovery is partial. Add known `--runtime-dir` paths or repeat `--remote-python`. Check private metadata permissions and the supported endpoint matrix. Do not infer that no server exists. |
| Multiple candidates (7) | Select on a terminal or give an exact server ID. For hostless open, choose an explicit route with `open HOST ID`. Names/PIDs are not session selectors. |
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

## Reporting a problem

Include the client/helper/Python/Jupyter/OpenSSH/tmux versions, command shape,
exit code, platform and a redacted description of direct versus ProxyJump access.
Replace aliases, account names and paths with examples. Do not attach raw runtime
JSON, settings, kernel connection files, browser profiles, cookies, private keys,
token URLs or server logs. Follow [SECURITY.md](../SECURITY.md) for security reports.
