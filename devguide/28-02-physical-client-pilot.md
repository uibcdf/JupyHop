# 28 — 0.2.0 physical home-client pilot

Report date: 2026-11-10. Status: the authorized pilot is complete; its three
managed test servers were explicitly stopped and archived. The manually launched
test server was stopped through its original terminal.

## Scope and evidence provenance

The operator installed the published Conda client, ran commands on a physical
home computer, entered credentials in native SSH/Jupyter prompts and supplied
terminal/notebook observations. The route was home client → public SSH gateway →
private workstation. All three machines use Linux. These are guided operator
observations, not an automated test or an independently captured process audit.

Real aliases, addresses, accounts, environment/project paths, UUIDs, PIDs and
memory nonces remain outside this report. The project directories contained only
synthetic notebooks and variables. No remote reboot, network interruption,
SSH-service change, forced logout or scientific-session cleanup was authorized
or performed as part of this pilot.

The client reports JupyHop 0.2.0. Doctor reports the selected remote environment
as Python 3.14.7, Jupyter Server 2.21.1 and jupyter_core 5.9.1; tmux is available.
Notebook sys.executable confirms that selected Conda Python. Exact client Python,
OpenSSH, tmux and frontend versions were not collected in this pilot. No remote
JupyHop installation or scientific-environment installation was required.

This supplements [23](23-02-stabilization-evidence.md); it does not replace that
report's separate two-hour, installed-upgrade or automated compatibility evidence.

## Experiments and observed acceptance

| Experiment | Operator observation | Acceptance and boundary |
| --- | --- | --- |
| SSH preparation | Native ssh rejected an owned 0664 client config; changing that file to 0600 allowed the existing ProxyJump route. The .ssh directory was already 0700. | Ordinary SSH prerequisite corrected; a failing JupyHop invocation was not used to establish this finding. |
| Selected-environment doctor | Native SSH passwords were accepted on both hops; a mistyped password could be retried. Correct account, Python/Jupyter versions and accessible runtime were reported. | Actual home/gateway/workstation prerequisites; doctor alone does not execute a kernel. |
| Managed launch | start selected the existing Conda Python and a private test project, prompted for a per-server Jupyter password and opened JupyterLab. | Correct remote host, executable and directory confirmed by a notebook; toy result 45. |
| Managed reconnection | Closing only the home client's attached tunnel caused the expected browser connection error. A fresh open recovered the same kernel PID, existing memory nonce and result 45. | Same live kernel on the physical home route; initialization was not rerun to manufacture the comparison. |
| Managed completion | Exact-UUID stop reported stopped/managed_stopped; archive returned the private archive destination. | Explicit lifecycle completion of the first test server; notebooks retained. |
| Crowded ordinary runtime | Initial discovery returned a bounded sample of stale metadata, entry_limit and no verified server. After a manual launch, it found a verified unmanaged endpoint. | Stale observations were not running-server counts. Existing runtime metadata was neither deleted nor used to authorize process control. |
| Existing Conda server | A server started manually in a second SSH terminal was found by plain open HOST, without selecting a port or passing the environment again. Normal Jupyter token login succeeded. | Real manual-server discovery across environments using a known ordinary runtime. The observation ID was not an authentication token. |
| Unmanaged reconnection | After closing only the JupyHop tunnel, fresh open recovered the same kernel PID, existing nonce and result 45. The original server-launching SSH terminal remained open. | Access did not adopt the server or restart its kernel. Survival after closing the original foreground launcher was not tested. |
| Unmanaged completion | The operator interrupted the manual server in its original terminal and confirmed the remote shell prompt returned. | No JupyHop stop/archive was applied to an unmanaged server. |
| Two managed servers | A and B were started with no-open, distinct names and private subdirectories in the same selected environment. Both reported ready. | Two distinct remote ports, UUIDs and notebook kernel PIDs; correct roots and toy results 45 and 145. |
| Interactive choice | Plain open HOST offered two numbered verified managed endpoints. A was selected; B was then opened by its exact UUID from another home terminal. | Existing multiple-candidate picker and simultaneous independent forwards work; the picker omits useful display names. |
| Independent tunnel closure | Closing A's tunnel left B executing with the same PID/nonce/result. Reopening A recovered its own original PID/nonce/result. | Tunnel lifetimes are independent of both kernels and of the other local tunnel. |
| Selected-server stop | After A's confirmed stop, B still executed with its original PID/nonce/result 145. | Stopping one managed test server did not stop the other. |
| Final lifecycle | B reported stopped; both A and B returned successful archive destinations. A native password retry during archive succeeded. | All three managed test UUIDs have explicit stop/archive observations. No global process inventory or archive-directory audit is implied. |

## Unconfirmed start and safe recovery

The first attempt to start B printed a request UUID, then OpenSSH reported
Connection timed out during banner exchange. JupyHop correctly stated that the
remote outcome was unknown and required inspection before retrying.

Discovery showed only A. A subsequent successful status of the whole current
registry also showed only A, with no B record. Only after those observations did
the operator repeat B's start with --timeout 120, obtaining a new UUID and ready.
That new UUID, not the unconfirmed request ID, was used for all later actions.

The timeout's cause was not established. Later success with a larger connection
bound is not proof of network failure, a slow password entry or a fixed defect.
Terminal authentication and SSH connection/handshake have separate bounds; a
reproducer for their interaction on password jump routes remains future work.
No automatic retry, restart or removal of uncertain state was performed.

## Findings and justified follow-up

- [Issue 3](https://github.com/uibcdf/jupyhop/issues/3): make SSH ownership/write
  permission rejection actionable in runtime feedback as well as documentation.
  The public troubleshooting additions explain the current manual remedy; a
  runtime fix is not included in this report.
- [Issue 4](https://github.com/uibcdf/jupyhop/issues/4): prepare safe diagnostic
  reports and an optional notebook-context check. The manual cells were useful,
  but current doctor JSON is not an anonymized public issue attachment.
- [Issue 5](https://github.com/uibcdf/jupyhop/issues/5): users should not memorize
  UUIDs. Evaluate named selection and consistent interactive lifecycle pickers.
  Automatically opening the sole candidate also surprised the operator.
- Bounded discovery must distinguish sample limits from incomplete directory
  scans. The same entry_limit currently covers both; increasing a timeout cannot
  remove a diagnostic sample limit. Keep original metadata and all safety bounds.
- Explicit manual archive is easy to forget. Current status lists unarchived
  managed records, including stopped entries, but has no summary counts or archive
  inventory. Stopped records reserve names and use the 128-record budget. The
  follow-up should make retained/history status visible and integrate archival
  into an explicitly confirmed interactive completion flow.

These findings motivate [the 0.3.0 design proposal](29-03-session-ux-design.md).
They do not require another remote package, a central service, a credential cache
or changing the tmux/identity model demonstrated here.

## Limits and next step

The real physical home-to-lab route is now observed, supplementing earlier
laboratory/software-client tests. This pilot did not move the same live kernel
between two different physical client machines. Physical suspend/network moves,
last-logout behavior, reboot, a second simultaneous remote host, other operating
systems and additional authentication variants were not tested here.

Notebook files, their private project directories and managed archive evidence
were intentionally retained. Successful stop/archive output is the cleanup
evidence; do not describe the workstation or its entire runtime as globally clean.

The next increment is review and implementation of the bounded 0.3.0 usability
proposal, followed by disposable-fixture and installed-candidate acceptance.
M7 platforms, schedulers and central services remain separate scope decisions.

## Documentation closeout

The README, roadmap, acceptance ledger and earlier stabilization boundary link
this report so the previously pending physical-route observation is no longer
described as unperformed. Current-user guides retain 0.2.0 syntax and explain
permission rejection, timeout reconciliation, discovery limits and manual archive.
The separate proposal labels all new CLI behavior as unimplemented. The changed
files are README, the devguide index/roadmap/decisions/UX/acceptance and
stabilization reports, these two new reports, and the public SSH, sessions and
troubleshooting guides. Installed client code, package version and protocols
remain unchanged.

Observed local documentation checks:

- Strict Sphinx 9.2.0 / MyST 5.1.0 build in an isolated temporary mamba environment:
  27 HTML pages, no warnings; 1394 local links/resources/fragments and generated
  CLI command/option sections pass.
- The existing source gate accepts 65 CLI examples, two TOML configurations and
  five JSON examples without running those commands.
- All 11 focused documentation-checker regressions pass on development Python
  3.14.10. No product integration or remote scientific workload is run for this
  documentation-only closeout.
- Changed Markdown relative file links resolve, git diff --check passes and a
  private-pilot identifier scan finds none of the real aliases, accounts, paths,
  UUIDs or nonces in the changed documents.

These are local checks, distinct from the operator pilot and any later hosted
workflow/deployment result.

The documentation candidate d31aba25d8e50f50ced6cd8149da1a346e384afc passes the
[Pages workflow](https://github.com/uibcdf/jupyhop/actions/runs/42767471012),
including build/check and deployment. Independent HTTPS receiving verification
from the development environment returned 403; the web reader could not access
the guides either. Deployment success is observed, but public receiving content
was not independently confirmed in this closeout.

Its [source workflow](https://github.com/uibcdf/jupyhop/actions/runs/42767471013)
passes all six jobs: 321 tests on each Python 3.11–3.14, installed upgrades,
packaging, browser, native password/account cleanup and server comparisons.
These hosted observations refer to that candidate; later 0.3.0 implementation
requires its own acceptance rather than inheriting these results.
