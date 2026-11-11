# 39 — Post-0.4.0 usability review and improvement backlog

Reviewed on 2026-11-11 against repository snapshot
`e38ee60549cbd37fb0107277e04941a4c999e0f0`. JupyHop remains at **0.4.0**.
This is an implementation/documentation review with offline experiments and a
prioritized issue backlog. It does not approve a 0.5.0 implementation scope or
replace the [release acceptance evidence](38-04-conda-publication.md).

## Recommendation

Use 0.4.0 for ordinary work and collect recurring friction before selecting the
next feature release. The strongest existing presentation finding is
[manage's dense output](https://github.com/uibcdf/jupyhop/issues/6). The highest
value missing evidence is an independent person's first use of the documentation.
Actual defects can receive 0.4.x fixes without waiting for a larger release.

The core workflows already cover the immediate product promise: existing-server
access, named managed sessions, automatic browser access for new managed sessions,
same-live-kernel return, explicit stop/archive, profiles and support reports.
Further work should make these capabilities easier to understand and repeat.

## Method and boundaries

Reviewed the README, public first-use/configuration/diagnostic/history/recovery
guides, current roadmap and decisions, 0.3/0.4 design and implementation reports,
and the corresponding CLI, selection, configuration, discovery, inventory,
SSH/forwarding, browser-access and diagnostic code and tests. Open and completed
GitHub issues were checked before creating follow-ups; implemented issues #3–#5
were not duplicated.

Six offline observations used synthetic protocol responses, ordered directory
entries, terminal input and launcher/receiver doubles. They exercised current
code without opening an SSH route, starting a Jupyter server/kernel, changing
scientific sessions or installing dependencies. These are controlled examples,
not additional real-site or browser compatibility results.

The previous [physical-client pilot](37-04-physical-client-pilot.md) supplies
observational evidence for management readability and repeated authentication
after returning from an attached tunnel. Its new-reader validation remains
pending. This review is not an exhaustive security audit or a new four-version
release qualification.

## Existing strengths and remaining friction

- **Ordinary return no longer requires copying an identifier.** Exact managed
  names, selectors and resume already exist. A managed UUID is an identity, not
  an authentication secret; the native token stays remote in automatic mode.
- **New managed browser access avoids a second human secret.** The automatic
  cookie handoff is implemented and qualified. Existing unmanaged servers retain
  their native login and remain open-only.
- **Saved project settings already exist.** Profiles can remove repeated Python
  and working-directory arguments. The gap is preparing and understanding those
  settings, rather than inventing another settings mechanism.
- **Lifecycle completion already includes housekeeping.** Interactive stop
  normally archives after confirmed shutdown. The remaining history problem is
  finding useful context among retained records, rather than automatically
  deleting them.
- **Discovery and diagnostics retain honest boundaries.** Search is partial,
  counts can be unknown or lower bounds, and a checked interpreter does not prove
  kernel health. The next step is making those distinctions actionable.

## Findings and issue backlog

Priority below describes what to learn or design first. It is not a promise to
include every item in 0.5.0. Interface spellings and architectural alternatives in
the issues remain proposals until reviewed and tested.

| Issue | Proposal | Evidence | Recommended next step |
| --- | --- | --- | --- |
| [#6](https://github.com/uibcdf/jupyhop/issues/6), existing and expanded | Clearer manage layout and interaction; evaluate accessible colours | Operator found counters, session rows and action numbering confusing. Offline input check also found that a mistyped action exits management. | Prepare representative layouts and review invalid-input versus cancellation behavior. |
| [#7](https://github.com/uibcdf/jupyhop/issues/7), new | Independent quickstart validation and ordinary-use feedback | A23 was explicitly deferred at publication; the physical pilot was guided. | Start during dogfooding and record assistance honestly. |
| [#8](https://github.com/uibcdf/jupyhop/issues/8), new | Easier profile preparation, validation and effective-setting inspection | TOML is handwritten; distinct configuration errors produce the same generic message. | Design an offline inspector/template first; justify a writer separately. |
| [#9](https://github.com/uibcdf/jupyhop/issues/9), new | Workflow-specific prerequisite/readiness feedback | Doctor accepts package presence even when managed start needs a different Server version or tmux. A separate stdlib helper can also be valid without Jupyter. | Define open versus start checks and preserve existing JSON/exit semantics. |
| [#10](https://github.com/uibcdf/jupyhop/issues/10), new | Actionable feedback while browser delivery is pending | A successful launcher exit without proof redemption never offers the fallback link. The private page also lacks a visible manual submit control. | Keep successful access concise; design a bounded fallback and usable private page. |
| [#11](https://github.com/uibcdf/jupyhop/issues/11), new | Distinguishable archived runs after name reuse | Two different archived UUIDs with the same name render as identical ordinary rows. | Decide the smallest useful read-only date/project/environment context. |
| [#12](https://github.com/uibcdf/jupyhop/issues/12), new | Useful recovery when a runtime directory hits its scan bound | A candidate beyond 512 enumerated entries is not examined; another timeout or the same runtime path cannot enlarge that window. | Compare bounded targeted alternatives in disposable fixtures. |
| [#13](https://github.com/uibcdf/jupyhop/issues/13), new | Investigate retaining the owned connection when returning to manage | D55 deliberately permits fresh authentication after Ctrl-C; observed with two password-authenticated SSH hops. | Measure friction, then run a terminal/signal spike before changing policy. |
| [#2](https://github.com/uibcdf/jupyhop/issues/2), existing | Investigate a macOS client connecting to Linux | Separate platform validation is required; it does not directly resolve the Linux pilot's usability findings. | Keep as an independent future investigation. |

For an eventual 0.5.0, start with #6 and the findings from #7. Consider #8–#10
when their proposed interaction can be explained simply and acceptance is clear.
Use dogfooding to determine the priority of #11. Treat #12 and #13 as experiments
with a valid outcome of retaining the current design and documenting a better
recovery procedure. Avoid coupling all these items into one release gate.

## Offline experiment results

1. **Doctor versus launch readiness.** A mocked doctor wire response had supported
   Python, Jupyter Server 2.17.0, jupyter_core and tmux=false. diagnose returned
   ok=true and missing=[]. This matches the current package-presence contract;
   it is not confirmation of managed-launch readiness. Start requires Server
   >=2.20,<3 and tmux. No remote prerequisites were actually changed.
2. **Configuration feedback.** Unsupported schema, a missing referenced profile
   and an invalid relative Python executable each raised the same generic
   ValueError. Raw TOML suppression is valuable; safe error categories can still
   distinguish the remedies.
3. **Scan bound.** With an ordered scandir double, a synthetic jpserver entry
   after 511 ordinary files reached the candidate verifier. After 512 ordinary
   files it did not; scan_limit and entry_limit were reported. This is separate
   from the 64-record retained-sample limit, which already favors ready endpoints.
   It is not evidence that a real server was missed in the physical pilot.
4. **Repeated archive names.** A synthetic inventory contained two archived IDs
   named analysis. Ordinary history printed two identical rows. Verbose output
   can distinguish UUIDs, but the current history wire omits useful project/date
   context already available in some original records. Legacy records can lack
   creation times; neither stop nor archive time should be invented.
5. **Invalid terminal choice.** A nonnumeric input to choose raised SelectionError
   immediately. Manage catches that error at its action menu and exits. Retrying
   invalid input is a design proposal; Enter/EOF cancellation and action
   authorization must remain explicit.
6. **Successful launcher without delivery.** A launcher double returned 0 while
   a receiver double never redeemed the proof. With a controlled 50 ms deadline,
   Handoff.wait expired without invoking fallback. The production lifetime is
   still 60 seconds. This experiment did not run or diagnose a real browser.

The independent-user, macOS and retained-connection investigations were **not**
performed by these offline probes. Each issue states what evidence it still needs.

## Reproduce the principal observations

Run from the repository root. This stdlib-only example supplies synthetic data
and performs no SSH or network operation:

```sh
PYTHONPATH=src python - <<'PY'
import io
import json
import time
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from jupyhop import _discovery_probe as probe
from jupyhop.config import parse_config
from jupyhop.controls import show_inventory
from jupyhop.doctor import diagnose
from jupyhop.errors import BrowserAccessError, SelectionError
from jupyhop.handoff import Handoff
from jupyhop.selection import choose
from jupyhop.session_inventory import parse_inventory
from jupyhop.ssh import CommandResult, SSHTransport

wire = {"protocol": {"major": 1, "minor": 0}, "operation": "doctor", "data": {
    "identity": {"uid": 1000, "user": "researcher"},
    "python": {"version": "3.14.9", "executable": "/example/env/bin/python", "supported": True},
    "jupyter_server": {"version": "2.17.0"}, "jupyter_core": {"version": "5.9.1"},
    "runtime_dirs": [], "coverage": "selected-interpreter-only",
    "process_managers": {"systemd_user": "unavailable", "tmux": False},
}}
with patch.object(SSHTransport, "run", return_value=CommandResult(0, json.dumps(wire).encode(), b"")):
    report = diagnose(SSHTransport("workstation"))
assert report["ok"] and report["missing"] == []
print("doctor: package presence accepted, despite missing managed-launch requirements")

errors = []
for raw in (b"version = 2", b'version = 1\n[hosts.workstation]\nprofile = "absent"',
            b'version = 1\n[profiles.analysis]\nserver_python = "relative/python"'):
    try:
        parse_config(raw)
    except ValueError as error:
        errors.append(str(error))
assert len(errors) == 3 and len(set(errors)) == 1
print("config: three distinct failures, one generic message")

class Entries:
    def __init__(self, count):
        self.items = [SimpleNamespace(name=f"ordinary-{i}") for i in range(count)]
        self.items.append(SimpleNamespace(name="jpserver-424242.json"))
    def __enter__(self):
        return iter(self.items)
    def __exit__(self, *args):
        return False

for count in (511, 512):
    output = {"identity": None, "paths": [], "servers": [], "issues": []}
    with (patch.object(probe, "_small", return_value=b"fixture-boot"),
          patch.object(probe, "_paths", return_value=[("/example/runtime", "explicit")]),
          patch.object(probe, "_directory", return_value=999),
          patch.object(probe.os, "scandir", return_value=Entries(count)),
          patch.object(probe.os, "close"),
          patch.object(probe, "_candidate", return_value={"id": "fixture", "state": "ready"}) as check):
        probe.discover({"runtime_dirs": []}, output)
    assert check.call_count == (1 if count == 511 else 0)
    print("discovery:", count, "preceding entries; verifier calls:", check.call_count)

wire = {"protocol": {"major": 1, "minor": 5}, "operation": "inventory", "data": {
    "identity": {"uid": 1000, "user": "researcher", "scope": "b" * 24},
    "sessions": [], "complete": True, "error": None, "history_error": None,
    "history": {"entries": [
        {"id": "a" * 32, "name": "analysis", "record_state": "exited"},
        {"id": "c" * 32, "name": "analysis", "record_state": "exited"},
    ], "offset": 0, "next_offset": None, "complete": True},
}}
report = parse_inventory(json.dumps(wire).encode())
report["host"] = "workstation"
output = io.StringIO()
with redirect_stdout(output):
    show_inventory(report, history=True)
rows = [row for row in output.getvalue().splitlines() if row.startswith("analysis ")]
assert len(rows) == 2 and len(set(rows)) == 1
print("history: two distinct archived sessions produce identical ordinary rows")

with patch("sys.stdin", io.StringIO("x\n")), patch("sys.stderr", io.StringIO()):
    try:
        choose(["open", "exit"], str, interactive=True)
    except SelectionError:
        print("selection: invalid entry ends selection")
    else:
        raise AssertionError("Expected SelectionError")

relay = SimpleNamespace(used=False, delivered=False, deadline=time.monotonic() + 0.05,
                        handle_request=lambda: time.sleep(0.005), timeout=0)
offered = []
try:
    Handoff(relay, "file:///example/private-link").wait(
        SimpleNamespace(poll=lambda: 0), fallback=lambda: offered.append(True))
except BrowserAccessError:
    assert not offered
    print("browser: launcher exit 0, no delivery, expiry without fallback")
else:
    raise AssertionError("Expected BrowserAccessError")
PY
```

## Verification and changes

The existing focused unit suite passed **131 tests** on Python **3.14.9**:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q \
    tests/test_protocol_cli.py tests/test_config_fleet.py \
    tests/test_session_inventory.py tests/test_feedback.py \
    tests/test_session_ux.py tests/test_diagnostics.py tests/test_docs_check.py
```

Automatic third-party pytest plugin loading was disabled because an unrelated
installed plugin failed before collection. No environment dependency or other
repository was modified. This focused check validates current relevant
contracts; it does not qualify any of the proposed changes or repeat the
published release's integration/browser/platform matrix.

The exact reproduction block above also passed when extracted from this document.
All **79 relative Markdown file links** in this report, the development index and
the roadmap resolved locally. The public documentation's existing **71 CLI,
2 TOML and 6 JSON examples** passed the offline parser check. No public Sphinx
page changed, so the full site build and visual/browser checks were not repeated.

Created issues #7–#13 with source evidence, alternatives, explicit boundaries,
acceptance and scheduling. Expanded #6 with invalid-choice behavior rather than
creating another menu issue. Kept #2 as the existing platform investigation.
This report and the development-guide links are the only repository changes;
product code, package version and public command contracts are unchanged.

## Constraints on follow-up work

Keep OpenSSH/native authentication, invocation-owned tunnels, Linux/Python
3.11–3.14, zero mandatory Python runtime dependencies, selected-target verification
and explicit destructive confirmations. New convenience must preserve existing
JSON/script behavior and the distinction between managed and unmanaged servers.

Do not equate useful historical context with automated deletion or recoverable
dead memory. Do not cache SSH passwords, add a tunnel daemon or broaden discovery
into network/environment scanning to remove a prompt. Any connection-retention
change requires signal/TTY evidence; preserving D55 remains a legitimate choice.

Profiles, names, selectors, automatic new-session authentication and diagnostics
already ship. Their existence is a baseline for these proposals, not planned
functionality. No extra central service, scheduler or platform commitment is
needed to begin dogfooding.
