# Reproducing 0.2.0 stabilization

Run from a reviewed full Git checkout, as a non-root development user, with the
existing dev/experiments dependencies, OpenSSH server/client and tmux. No real
account, address, password, private key or unredacted site evidence belongs in
this repository. See [the plan](../devguide/22-02-stabilization.md) and
[observed evidence](../devguide/23-02-stabilization-evidence.md).

## Installed clients

```console
python -m experiments.client_upgrade --preview-version 0.2.0
```

The trusted local baseline commit is
`21e0dc97161d83088ae6ad850027fa4d17ee4d3c` (0.1.0). Fetch that trusted history if
the checkout is shallow; CI uses fetch-depth=0. Both wheels build offline with
--no-isolation. A temporary copy of the current package receives the preview
version; this checkout/version and scientific environments remain untouched.
The dev extra includes setuptools>=77 because these offline builds cannot rely
on an isolated build environment or an interpreter bundling the backend.
Old/new venvs install offline without Jupyter, with separate keys/HOMEs/routes.
The old client launches the server; upgraded, simultaneous old and independent
new clients retain server/kernel/session/PID/memory/progress and original runner/
registry bytes. Only its UUID is stopped/archived. All loopback resources clean up.

Final acceptance uses the actual reviewed candidate rather than a preview:

```console
python -m experiments.client_upgrade --candidate-wheel dist/jupyhop-0.2.0-py3-none-any.whl
```

Optional --hold-seconds extends the disconnected toy workload, up to four hours.
Short default runs are regression acceptance, not hours-long endurance evidence.

## Native SSH authentication

```console
pytest --run-integration tests/integration/test_ssh_auth.py
```

Native encrypted fixture keys and a real controlling PTY exercise direct/jump
prompts, private RPC input, CLI discovery/open, echo restoration, cancellation,
SIGTERM, timeout, headless refusal and missing-control-socket failure. The
application never parses a password prompt or reads the SSH password; only the
test actor types a synthetic secret. Unix-account password acceptance is separate:
[optional disposable-account instructions](m5_accounts.md#optional-native-password-ci-acceptance).

## Explicit authorized site pilot

This operator script currently automates noninteractive OpenSSH routes; terminal
password workflows use the CLI and separate password acceptance above. Select
existing remote Python executables and a test account authorized for synthetic
work. It creates external manual servers and a managed toy session; existing
scientific servers/data are outside its lifecycle scope. It installs no packages,
changes no SSH configuration, and performs no reboot/logout/network-policy change.

```console
pilot_results="$(mktemp -d /tmp/jupyhop-site-results-XXXXXXXX)"
python -m experiments.site_pilot workstation \
    --server-python /absolute/remote/managed-env/bin/python \
    --manual-python /absolute/remote/manual-env/bin/python \
    --hold-seconds 7200 \
    --evidence-file "$pilot_results/pilot.json"
```

--manual-python may repeat for another existing environment; --ssh-config passes
an optional existing or reviewed private route config to native OpenSSH.
The evidence file must not exist and is created 0600. It contains private host/
resource identities, not passwords. New session passwords are generated only in
memory and cross encrypted stdin; manual settings retain only a private hash.
Manual fixtures use exclusive marked 0700 /tmp directories, including a private
runtime supplied as an explicit known discovery path. Native Jupyter metadata and
browser redirect files stay inside that owned root; normal user runtime files are
preserved byte-for-byte. Cleanup refuses
symlinks/unmatched markers and never signals an arbitrary PID. Managed stop/archive
requires its exact newly generated UUID. Unknown launch/cleanup retains evidence
and workdirs for explicit recovery; definitive preflight refusal cleans its own
manual resources. SIGINT/SIGTERM/SIGHUP unwind through guarded cleanup.

Fresh worker processes/login/forwards must observe the same server/kernel/session/
PID/memory and advancing bounded computation after the disconnected hold. This
alone is not proof of a second physical computer, a real last-logout policy,
physical suspend or a changed WAN route. Record those manual observations
separately, redact them before committing, and inspect the final cleanup receipt.
