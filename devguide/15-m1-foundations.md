# 15 — M1 SSH foundations and diagnostics

Date: 2026-11-07. Status: complete within the acceptance scope below. M2 has not
started. This is the implementation report and the exact shipped CLI contract.

## Work and architecture

The supported Python matrix is **3.11, 3.12, 3.13 and 3.14** on Linux; the
development environment uses 3.14. Other Python versions are not yet advertised
as tested. The `src/jupyhop/` package uses setuptools, `pyproject.toml`, MIT metadata,
version `0.1.0.dev0`, and the `jupyhop` console script. The installed client has
zero Python runtime dependencies; Jupyter is needed only by the chosen remote
environment, or by experimental/integration fixtures.

```console
jupyhop --help
jupyhop --version
jupyhop doctor workstation
jupyhop doctor workstation --remote-python '/absolute/remote env/α/bin/python'
jupyhop doctor workstation --ssh-config /path/to/ssh_config --timeout 15 --json
```

Only these diagnostics ship. No `discover`, `list`, `open`, `start`, `status` or
`stop` product command is implemented. Their appearance elsewhere is a proposal.

OpenSSH receives the alias intact and handles `Include`, `Match`, `ProxyJump`,
User, keys, known_hosts and crypto. There is no SSH configuration parser, remote
service, configuration rewrite or remote installation. `--ssh-config` is passed
as OpenSSH `-F`; the default uses its ordinary configuration. Aliases accept
ASCII letters/digits/dot/underscore/hyphen; configure User in SSH config rather
than supplying `user@host`, URIs, SSH flags or shell syntax as the alias.

Doctor uses `BatchMode=yes` and strict target host-key verification. Trust new
hosts with the normal `ssh` workflow after independently verifying fingerprints;
unlock encrypted keys in an agent before diagnostics. This deliberate M1 limit
prevents hidden password/passphrase prompts. Jump-host trust/authentication uses
the configuration resolved by OpenSSH; configure it securely too.

For this read-only probe, configured forwards, agent/X11 forwarding, local
commands, remote default commands, and control-master sharing are disabled on
the target invocation. This avoids side effects, attaching to someone else's
forward, and background master lifetime. Trusted user SSH `ProxyCommand`/`Match
exec` may themselves execute local commands as ordinary OpenSSH configuration;
JupyHop does not sandbox that configuration.

The transport uses local subprocess argv and POSIX quoting for the single
remote-shell command. A POSIX-compatible remote login shell is required. Code
travels over stdin to `python3 -I -B -` or an explicit absolute interpreter
path: no shell activation, helper file, cache or registry. `-I` avoids Python
environment/path injection; `-B` prevents bytecode writes by the probe.

## Diagnostics and wire contract

The selected remote Python reports the current OS UID/name, Python executable
and version, installed Jupyter Server/core distribution versions, its configured
runtime directory, and systemd-user/tmux availability. It never reads Jupyter
runtime records, tokens, notebook files or process inventories. Installed package
metadata does not prove a server can launch or is ready. A systemd manager check
does not guarantee last-logout persistence; finding tmux does not prove a
particular session policy permits persistence.

Runtime directory states are `accessible`, `missing`, `inaccessible`. Missing
runtime storage is not evidence of no running servers. Coverage is always
`selected-interpreter-only`, including when the report is successful. Select
another known environment by absolute executable path if needed. The probe never
selects unrelated environments or installs missing dependencies.

SSH stdout contains one UTF-8 JSON object:

```json
{
  "protocol": {"major": 1, "minor": 0},
  "operation": "doctor",
  "data": {
    "identity": {"uid": 1000, "user": "researcher"},
    "python": {"version": "3.14.10", "executable": "/env/bin/python", "supported": true},
    "jupyter_server": {"version": "2.21.1"},
    "jupyter_core": {"version": "5.9.1"},
    "runtime_dirs": [{"path": "/home/researcher/runtime", "source": "selected-python", "status": "missing"}],
    "coverage": "selected-interpreter-only",
    "process_managers": {"systemd_user": "unavailable", "tmux": true}
  }
}
```

Examples are fictional. Missing packages have `version: null`. Manager status is
`available`, `unavailable` or `missing`. Version negotiation rejects major !=1
and accepts additional minor fields without reflecting them. All required 1.0
fields must still be present. Registry schemas are a separate future contract.
Local `--json` adds `host`, `ok` and a `missing` prerequisite list; it rebuilds
the data from an allowlist instead of echoing raw remote JSON. General errors
leave stdout empty. Successful JSON and missing-prerequisite reports remain
machine-parseable; human diagnostics go to stderr.

Limits: stdin/stdout 64 KiB each; stderr 32 KiB; individual reported strings
4096 characters; at most 32 runtime paths. Invalid UTF-8, banners/trailing text,
invalid field types, duplicate keys, Unicode control/format/surrogate characters,
and oversized output fail closed.
Total timeout defaults to 20 seconds, accepts 1–300, and includes remote stdin
backpressure and process completion. Output-limit/timeout/interruption cleanup
targets only the owned local SSH process group. No remote stop is sent. Raw SSH
stderr and exception payloads are never forwarded; known host-key/auth failures
receive curated recovery instructions. Unknown transport failure says remote
session state is unknown.

| Exit | Meaning |
| --- | --- |
| 0 | SSH/probe completed; selected Python and installed Jupyter prerequisites present |
| 2 | Invalid CLI/input |
| 3 | SSH executable/access/trust/auth/network/timeout failure |
| 4 | Remote Python probe could not run, unsupported Python, or missing Jupyter distribution |
| 5 | Oversized/malformed/incompatible probe output |
| 130 | Interrupted local diagnostic |

## Experiments, tests and results

The [M0 report](13-m0-validation.md) records live Jupyter/WS/Conda/persistence
spikes. M1 tests focus on its shipped read-only slice:

| Test evidence | Observable assertions |
| --- | --- |
| `test_doctor_direct_and_proxyjump` (two cases) | Real OpenSSH, direct/jump, selected UID, installed Jupyter version and partial coverage |
| `test_include_match_and_proxyjump_resolved_by_openssh` | OpenSSH resolves Include/Match/jump; JupyHop does not parse config |
| `test_unknown_host_key_is_refused`, `test_changed_host_key_is_refused` | Trust failures are refused, not bypassed |
| `test_remote_shell_injection_is_literal` | Metacharacters round-trip; sentinel file never created |
| `test_absolute_interpreter_path_with_spaces_and_unicode` | Explicit noninteractive environment executable works |
| `test_missing_remote_python_is_actionable`, `test_fresh_python_without_jupyter_is_reported` | Missing Python/Jupyter diagnosed without install |
| `test_unavailable_jump_does_not_claim_server_stopped` | Failure preserves unknown remote state |
| `test_cli_integration_stdout_is_json` | Actual CLI through jump emits valid JSON only |
| Unit transport tests | Input rejection, quoting, deadline/backpressure, bounded stdout/stderr, owned process cleanup, redacted errors |
| Unit protocol/CLI tests | Major mismatch, optional minor extensions, malformed output, wrong types, secret-field filtering, correct exits and interruption |
| `experiments.package_smoke` | Wheel installed offline into clean venv; no local Jupyter; console script and packaged remote probe work through jump |

Final local `pytest --run-integration -q` results (56 unit + 11 integration each):

| Python | Unit + integration | Clean wheel client through ProxyJump |
| --- | --- | --- |
| 3.11.18 | 67 passed | Passed, no local Jupyter |
| 3.12.16 | 67 passed | Passed, no local Jupyter |
| 3.13.18 | 67 passed | Passed, no local Jupyter |
| 3.14.10 | 67 passed | Passed, no local Jupyter |

Compatibility environments were created with mamba in temporary storage; the
existing 3.14 development environment received the development tools with mamba
and JupyHop itself through `pip install --no-deps --no-build-isolation -e .`.
`ruff check .`, `ruff format --check .`, `mypy` and `git diff --check` pass.
Build creates wheel and source archive with MIT license; the source archive
includes guides, experiments and all tests. Offline wheel installation into a
fresh client environment verifies that local Jupyter is unnecessary and that
the packaged probe and console script work through ProxyJump.

All **65/65** scenario IDs in 08 have release gates/evidence in 14; most session
feature gates deliberately remain pending. Relative Markdown links resolve.

CI is defined for Linux/Python **3.11, 3.12, 3.13 and 3.14**, using only disposable SSH fixtures,
quality checks, package build and clean-wheel smoke. The workflow has not been
observed on GitHub; local results are the evidence for this milestone.

## Files and acceptance

- Package/build: `pyproject.toml`, `MANIFEST.in`, `src/jupyhop/`.
- Tests/CI: `tests/`, `.github/workflows/checks.yml`, `experiments/package_smoke.py`.
- M0 fixture formatting follows the now explicit project Ruff configuration.
- README, guide index, CLI/security/runtime specifications, roadmap, decision
  records and acceptance ledger reflect the implemented slice and future scope.

M1 acceptance is satisfied: direct and jump access to disposable Linux SSH
endpoints, strict host-key checks, verified selected OS account, safe argument
handling and actionable missing prerequisites. Product diagnostics require no
elevation, no installed service/helper and no SSH config change. Test harness
prerequisites (`sshd`, `/run/sshd`, loopback permission) are distinct from product
requirements. No test connected to scientific infrastructure.

## Limits, risks and next milestone

Linux/POSIX shells and batch SSH authentication only. The test jump and target
are separate sshd processes on the same host/account, not isolated OS instances.
Cross-user authorization, actual browser integration, account logout/linger,
real reboot, IPv6 and HTTPS are unvalidated future gates. Managed state,
supervision, helper upgrades and concurrency are not implemented. Doctor does
not prove Jupyter readiness, discover all Conda environments, or infer server
liveness from SSH access.

Next: **M2**, after reviewing this report. Implement read-only partial discovery
and verified loopback forwarding/open with normal Jupyter login, preserving
managed/unmanaged boundaries. Do not infer M2 acceptance from M0 spikes. Work
stops after M1 in this development iteration.
