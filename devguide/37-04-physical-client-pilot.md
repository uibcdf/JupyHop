# 37 — 0.4.0 physical-client pilot

The operator tested the development client from a home Linux computer through
an SSH gateway to a private Linux workstation. All session actions used named
test sessions, dedicated project directories and synthetic notebook variables.
This report records the guided terminal/browser observations supplied by the
operator. Infrastructure aliases, addresses, usernames, paths, session IDs,
kernel PIDs and memory nonces are omitted.

## Versions and setup

The client reported JupyHop **0.4.0** from the development installation. Its
exact checkout revision, Python, browser and OpenSSH versions were not collected.
The selected remote Conda Python reported **3.14.7**, Jupyter Server **2.21.1**
and jupyter_core **5.9.1**. Doctor found tmux and an accessible runtime directory.
Native OpenSSH password prompts authenticated both the gateway and workstation.
An incorrect password could be retried successfully.

Project directories were created with ordinary SSH before start. That setup and
the subsequent JupyHop command each required SSH authentication. Existing remote
Python/Jupyter and system tmux supplied the server prerequisites.

## Experiments and observations

| Experiment | Operator observation | Result |
| --- | --- | --- |
| Default managed start | A new named session A opened JupyterLab immediately after SSH authentication. The operator reached the notebook without choosing or entering a Jupyter password. | Automatic browser access worked on the physical jump route. |
| Notebook context | The notebook reported the selected remote Python and dedicated project directory. It produced a synthetic memory nonce and a result of 45. | Correct execution context established for later comparisons. |
| Named reconnection | After Ctrl-C closed the attached tunnel, resume with the exact managed name reopened A. A new cell reported the original kernel PID, existing nonce and result 45. | The original live kernel and memory survived reconnection. Initialization was not rerun. |
| Management overview | Manage showed one ready named session, no stopped/review records, one unarchived record and five existing archive records. | Names and counters were visible without copying a UUID. |
| Open from manage | The numbered action and session selections opened A. Its original kernel PID, nonce and result were retained. | The menu's access path reached the same live notebook. |
| Return to manage | Ctrl-C closed the owned forward, printed the return-to-management message and requested SSH authentication again before redisplaying the menu. The operator then selected Exit. | The menu returned and the session remained ready. Reauthentication follows the current D55 policy. |
| Expired access link | Named resume with --no-browser printed a private local file link. The operator left it unopened until the command reported expiry, gave the named resume command and returned to the shell. | Actionable expiry feedback observed. Wall-clock duration, exit status and filesystem cleanup were not measured in this physical test. |
| Recovery after expiry | Normal named resume reopened A. The notebook again reported the original PID, nonce and result 45. | Failed access delivery preserved the session and its memory. |
| Second managed session | Start with --no-open created named session B in another dedicated project directory and returned ready. | A second managed server could be prepared without attaching a browser. |
| Two-session selector | Host-only resume displayed A and B by name, each managed and ready. Partial-search and diagnostic-limit notices remained visible. | The operator could choose B by number. The detailed diagnostic codes were not collected. |
| Independent notebook B | B reported its own directory, a different kernel PID and nonce, and a synthetic result of 145. | Separate managed servers had independent notebook state. |
| Selected stop and archive | From a second client terminal, stop by A's exact name asked for confirmation, reported stopped and archived A. B still produced its original PID, nonce and result 145. Status showed only B ready, one unarchived record and six archives. | Confirmed completion of A preserved B's live computation. |
| Final completion | Stop by B's exact name confirmed stopped and archived B. The attached client tunnel was closed with Ctrl-C. The final status reported ready=0, stopped awaiting archive=0, review=0, unarchived=0/128 and archived=7. | Both test sessions completed and released their active names/record slots. The five previous archive entries and the two new ones were accounted for. |

The final counters describe the observed managed registry for that host/account.
They are not a system-wide process inventory or an audit of unmanaged servers.
Stop/archive retained session evidence. Removing notebook/project directories was
outside this pilot. No remote reboot, deliberate network interruption or forced
logout was included in the test sequence.

## Usability finding

The operator found manage's presentation dense and confusing. Its compact
counter line runs directly into numbered session rows and a second numbered
action list. The two lists restart at 1. The maintainer requested a cleaner
design, potentially using colours, for the next release after 0.4.0.

[Issue #6](https://github.com/uibcdf/jupyhop/issues/6) records the request with a
generic transcript and acceptance criteria. It covers spacing and hierarchy,
clear action/session selection, readable counts, optional accessible colours,
plain redirected output and NO_COLOR. A future presentation change must preserve
target pinning, confirmation and machine-readable results.

## Acceptance and remaining scope

These observations supplement [the source implementation evidence](36-04-implementation.md)
and [the acceptance plan](35-04-implementation-plan.md). They exercise the human
default-start, named return, menu, access-expiry recovery, two-session selection
and safe completion paths. Physical evidence supports A01, A09, A14–A17 and the
native-password ProxyJump portion of A21. Same-client continuity is a subset of
A04, whose independent installed-client checks are recorded separately.

This was a guided pilot. The maintainer subsequently authorized publication
using the current validation and collection of new-user feedback afterwards.
A23's unassisted new-reader walkthrough is deferred, with that decision recorded
in the [publication report](38-04-conda-publication.md).
This run did not repeat the external-server or existing password-session paths,
change the server's native token policy, or directly inspect private credentials.
Automated browser, cross-account, protocol, installed-upgrade and package checks
remain separate evidence. Conda staging, promotion and independent public
receiving belong to G6 and require the release workflow.

The requested physical test sequence is complete. The subsequent
[publication workflow and independent receiving](38-04-conda-publication.md)
passed for 0.4.0=py_0. Issue #6 is scheduled for the following version.
