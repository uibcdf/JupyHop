# 36 — 0.4.0 source candidate

The 0.4.0 source candidate implements automatic browser access for managed
Jupyter sessions, named selection and recovery. The published Conda release
is 0.3.0. The [implementation plan](35-04-implementation-plan.md) specifies the
acceptance cases and release workflow.

## Implemented contracts

- New managed sessions generate a 256-bit token in their remote runner. The
  runner uses native Jupyter authentication and keeps the token in private
  runtime metadata. `--auth password` and `--password-stdin` select password mode.
  Private launch settings declare the mode and have their own version. Existing
  registry schema 1.0 and the runner command shape support older clients.
- The private browser operation verifies the current Unix account and boot,
  selected UUID, runner digest, process start and listener. The remote helper
  asks Jupyter for a cookie using the verified local forward's Host header.
  It checks identity again before returning the cookie. The local client
  verifies the cookie through the owned SSH forward.
- A private file contains a single-use proof for a 60-second loopback POST.
  The receiver serves one connection at a time, with a four-connection backlog,
  bounded reads and an absolute deadline. It sends the cookie and redirects to
  the selected forward. The command closes the receiver and removes the file
  after delivery, expiry or graceful cancellation. Browser acceptance is tested
  separately from successful delivery.
- Human managed access defaults to automatic login. Exact named access reads
  the selected managed record without scanning unrelated runtime directories.
  Manual access, unmanaged servers and existing password sessions use the
  native Jupyter login page. The initial password-based start can reuse its
  supplied password for native cookie issuance.
- `--json` defaults to manual login and retains its public shapes. Explicit
  automatic JSON waits for delivery. Human `--no-browser` offers the private
  link for the same computer. Browser access errors return 15 and give a
  reconnection step after a confirmed start.

## Implementation findings

Jupyter Server 2.21.1 exposes `no_browser_open_file` as a trait that does not
read its value from `traitlets.Config`. The runner sets it directly before
initialization. The integration test verifies private runtime permissions
and checks for extra redirect files and credential output.

The file's CSP allows the receiver and the fixed final forward origin in
`form-action` so that the browser can follow the 303 across the two loopback
ports. The client uses the Linux system launcher for GUI access. Tests use
isolated profiles and a private application selection. Native browser cookies
retain Jupyter's lifetime and [HTTP port-scope limits](https://httpwg.org/specs/rfc6265.html#section-8.5).
The trust boundary includes local loopback services. A stopped process can
leave a private proof-only file after SIGKILL. Redemption requires its original
live receiver.

## Evidence and reproduction

The feasibility experiment and the production start/resume browser flow were
observed on Linux with Python 3.14.10, Jupyter Server 2.21.1, Chrome
157.0.8103.38 and Firefox 160.0 with geckodriver 0.37.0. Both browsers used
disposable profiles. The production experiment starts Jupyter, opens a
notebook, disconnects and uses another SSH identity and browser profile to
verify the same session, kernel and memory. It also tests fresh password input.
The Linux launcher experiment passes the private file to a selected application
via `xdg-open` and verifies that explicit automatic JSON emits the connection
object after delivery. An interrupted access attempt removes its private file
and a fresh resume recovers the same kernel.

The initial local regression suite passed 407 tests. The separate browser
access checks passed 11 cases, including invalid HTTP requests, concurrent
redemption, elapsed expiry, SSH reply redaction, anonymous HTTP/WebSocket
refusal, private metadata and target mismatch. The documentation builds
with warnings treated as errors and passes example and reference checks.
The full 60-second production expiry and a system launcher failure both
returned code 15, removed the private link and preserved the ready server.

```console
pytest --run-integration
python -m experiments.managed_browser
python -m experiments.managed_browser --firefox /path/to/firefox --geckodriver /path/to/geckodriver
make -C docs check
python -m build
python -m experiments.release_check
```

The checks workflow runs source and installed upgrade acceptance on Python
3.11–3.14. Its 3.14 job covers the disposable two-account credential boundary,
direct and jump SSH password prompts, and both browsers using the installed
candidate wheel. Compatibility jobs include Server 2.20.0 and the 2.17.0
managed-launch refusal. All test hosts, keys and notebooks are generated
fixtures. The local unprivileged environment cannot provision Unix accounts.

The installed wheel from `91300cc` passed both Chrome and Firefox and the
two-way 0.3.0 upgrade check. The private Conda build from the same source used
the existing recipe. Its archive `jupyhop-0.4.0-py_0.tar.bz2` passed metadata and
source inspection and the installed smoke test on Python 3.11, 3.12, 3.13 and
3.14. Its SHA256 was
`851fb172040606ea3c37cb45975dcff0c2debc5dd8e953aa43d5b42f049f7cb7`.

The [first hosted run](https://github.com/uibcdf/jupyhop/actions/runs/42929289691)
passed both server compatibility jobs, real account isolation and the native
SSH password cases. It exposed shared test state when a retained managed record
appeared in a subsequent unmanaged discovery test. The new credential test now
owns a separate SSH lab. Both tests passed together locally after the change.

## Release status

Source revision **18009b1c6f7b54da073d0f2e08946e8b041573f7** passed all six
[source qualification jobs](https://github.com/uibcdf/jupyhop/actions/runs/42930654711),
including Python 3.11–3.14, the server compatibility cases, disposable Unix
accounts, native SSH password routes and installed Chrome/Firefox access.
The [documentation build and deployment](https://github.com/uibcdf/jupyhop/actions/runs/42930654613)
also passed for that revision.

The final local Conda archive from this revision passed source/metadata
inspection and clean installed checks on Python 3.11–3.14. Its SHA256 was
`2465edd9c9a17314d565a686b75a14340caa35a078ab75988086599d4b0497cd`.
The corresponding wheel SHA256 was
`4ddbf53323bf8e4add455aef902177ec4ac8c3ddcd0f13786f24040c433a2895`.
These identify the private qualification artifacts. G6 qualifies the exact
staged archive again through the publication workflow.

The [guided physical-client pilot](37-04-physical-client-pilot.md) passed its
automatic access, continuity, menu, expiry/recovery and independent completion
sequence. It ended with zero unarchived managed records. Its menu readability
finding is recorded in [issue #6](https://github.com/uibcdf/jupyhop/issues/6) for
the next version.

The source implements G0–G4. The maintainer accepted G5's automated qualification
and guided physical pilot for 0.4.0, explicitly deferring A23's unassisted
new-reader walkthrough to subsequent feedback. G6's authorized publication and
independent public installation are tracked in the
[publication report](38-04-conda-publication.md). See [the release procedure](../docs/releasing.md).
