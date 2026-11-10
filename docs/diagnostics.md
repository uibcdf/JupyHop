# Diagnostics and support reports

There are three different Python contexts: the local JupyHop client, the selected
remote helper/server environment, and the actual notebook kernel. A successful
check of one does not establish the others' health. All checks below inspect
prerequisites/package metadata; they do not start, interrupt or restart kernels.

## Check remote prerequisites

```console
jupyhop doctor workstation --remote-python /absolute/remote/env/bin/python
```

Normal doctor shows the selected account/interpreter, installed Jupyter packages,
runtime access and process-manager capabilities. It does not discover servers or
execute a kernel. A stdlib helper with no Jupyter can still discover a server in
another environment. Systemd availability does not select a systemd launcher.

## Prepare an issue attachment

```sh
jupyhop doctor workstation --remote-python /absolute/remote/env/bin/python --report > support-report.json
```

--report emits versioned JSON with normalized client/OpenSSH/Python and selected
remote package versions, capability results, coverage and outcome. If SSH fails,
local diagnostics remain available. Exit codes retain their meanings: for
example, 3 for SSH failure and 4 for missing prerequisites. The report excludes
host/account identities, addresses, executable/project paths, passwords, tokens,
cookies, keys and scientific data. It does not dump SSH configuration, environment
variables, runtime files, logs or notebook contents, and uploads nothing.

Review the file before sharing. Add a command shape using invented aliases/paths
and explain whether the problem concerns a client, selected server or notebook
kernel. Attach the report file rather than an unreviewed terminal transcript:
native SSH prompts can still identify the account/hops in your terminal.

Ordinary --json is **not** a public-report mode: status/discovery/doctor JSON may
include identities and private paths. See [JSON output](json-reference.md) and
[Troubleshooting](troubleshooting.md#reporting-a-problem).

## Inspect the current notebook kernel

JupyHop normally needs installing only on the browser/client computer. If you
choose to install it in a notebook's environment too, this optional API runs
inside that existing kernel without SSH:

```python
import json
from jupyhop.diagnostics import kernel_report

print(json.dumps(kernel_report(), indent=2))
```

It identifies the context as notebook-kernel and reports normalized Python/package
versions. Missing optional packages are null. It reads package metadata without
importing Jupyter or collecting in-memory scientific variables. It does not prove
that a frontend is connected or that a kernel can survive a reboot.

An installation in the remote kernel is optional. Without it, run this equivalent
stdlib cell in the notebook you are diagnosing:

```python
import json
import re
import sys
from importlib.metadata import PackageNotFoundError, version


def package_version(name):
    try:
        match = re.match(r"[0-9]+(?:\.[0-9]+){1,3}", version(name)[:64])
        return match[0] if match else None
    except (PackageNotFoundError, ValueError, OSError):
        return None


report = {
    "report_version": 1,
    "context": "notebook-kernel",
    "python": ".".join(str(part) for part in sys.version_info[:3]),
    "platform": sys.platform if sys.platform in {"linux", "darwin", "win32"} else "other",
    "packages": {
        name: package_version(name)
        for name in ("jupyhop", "ipykernel", "jupyter_client", "jupyter_server", "jupyterlab")
    },
    "coverage": "current-interpreter-package-metadata-only",
}
print(json.dumps(report, indent=2))
```

For your own private diagnosis, compare the kernel's sys.executable and working
directory with the intended environment/project. Those paths may be identifying;
review/redact them before adding them to an issue. Session UUIDs and kernel PIDs
are not authentication tokens, but reports do not need to collect them by default.
