# SSH and gateways

JupyHop uses OpenSSH and the access you already have. Put host addresses, Unix
users, keys and routing in your SSH configuration. JupyHop's optional TOML stores
application preferences such as remote Python paths, not SSH credentials.

## Direct access

Example `~/.ssh/config` entry; replace the example domain and account yourself:

```text
Host workstation
    HostName workstation.example.org
    User researcher
```

Verify the host fingerprint through a trusted channel and check ordinary
`ssh workstation` before using `jupyhop open workstation`. Keep SSH configuration
and included files owned by you, without group/other write access. Private
configuration commonly uses mode 0600.

If OpenSSH reports **Bad owner or permissions**, inspect the exact file named in
its error. For the default local ~/.ssh/config owned by your account, group or
other **write** permission is unsafe: 0664 is rejected, while 0644 normally
passes this file check. Mode 0600 is the conservative recommendation. A correctly
restricted 0700 directory does not replace the file's independent check.
An editable configuration could change the destination or commands SSH executes.
See the [OpenSSH file requirements](https://man.openbsd.org/ssh_config#FILES)
and [step-by-step correction](troubleshooting.md#bad-owner-or-permissions-on-ssh-configuration).
JupyHop does not change ownership or permissions for you.
Explicit -F/--ssh-config files can follow different OpenSSH permission checks;
the measured -F case accepted 0664. Use private permissions anyway, but let
OpenSSH decide rather than assuming every configuration path has the default
file's rejection policy. Unknown include/gateway errors remain qualified.

## ProxyJump

For a destination reachable through an authorized gateway:

```text
Host gateway
    HostName gateway.example.org
    User researcher

Host workstation
    HostName workstation.example.org
    User researcher
    ProxyJump gateway
```

Verify access and host trust for every hop, then use the final alias:

```console
ssh workstation
jupyhop open workstation
```

OpenSSH resolves the jump and configuration. The gateway needs ordinary SSH
forwarding permission, not JupyHop or Jupyter. A gateway can also be a destination
if that account and site's policy allow running Jupyter there.

The same alias can use a different route on another client. Configure that
client's OpenSSH appropriately; remote managed identities remain scoped to the
actual host and account. JupyHop does not establish a VPN or make an unreachable
private machine reachable without an existing route.

## Passwords, passphrases and keys

In a controlling terminal, OpenSSH handles native password/passphrase prompts.
Keys and agents work through ordinary OpenSSH configuration too. Each invocation
owns a private connection per route and reuses it for its probes and forwarding;
authentication happens once per live private connection/hop. Manage can ask
again after Ctrl-C ends an opened tunnel's foreground master. Python does not
read, retain or supply your SSH password.

Terminal authentication has a separate deadline:

```console
jupyhop doctor workstation --ssh-auth-timeout 180
```

`--ssh-auth-timeout` accepts 1–600 seconds (default 120). `--timeout` bounds the
separate SSH probe/startup operations (default 20 seconds) and supplies OpenSSH's
[ConnectTimeout](https://man.openbsd.org/ssh_config#ConnectTimeout), which covers
the initial connection/handshake. A longer authentication deadline does not
remove that handshake bound on a jump route. See
[timeout recovery](troubleshooting.md#ssh-times-out-during-a-start).
Ctrl-C cancels an attempt and cleans owned local resources; interrupted remote
writes still need reconciliation.

## Headless commands and other configurations

With no controlling terminal, or explicit `--batch`, authentication must work
noninteractively on every hop:

```console
jupyhop discover workstation --batch --json
```

Prepare authorized keys/agent access through your usual SSH workflow. The
`--password-stdin` option belongs only to a new Jupyter session password; it does
not feed an SSH prompt. Individual MFA setups have not been qualified separately.

An alternate configuration file can be selected explicitly:

```console
jupyhop doctor workstation --ssh-config /path/to/ssh_config
```

Use aliases whose destination/account remain stable for a transport-only SSH
connection. Per-command `Match` rules cannot switch the destination between RPCs
on that connection. Configured unrelated forwarding and arbitrary pre-existing
shared masters are not adopted. See [Compatibility](compatibility.md) and
[Security](security.md).

## Replace a fixed LocalForward workflow

You can keep the existing SSH alias, User, HostName, IdentityFile and ProxyJump
settings. Use `jupyhop discover workstation`, then `jupyhop open workstation`
instead of a separate `ssh -L ...` command. JupyHop allocates its own local port
and prints its own login URL each time.

Configured `LocalForward`/`RemoteForward`, `RemoteCommand` and arbitrary shared
control sockets are not reused by JupyHop. It clears configured forwards on its
own connection. Existing independent SSH tunnels remain under their original
owner; JupyHop does not close them. A custom SSH port belongs in the alias's
`Port` setting. There is no JupyHop option to attach to an arbitrary URL/port or
adopt an existing server for stop/archive.

If JupyHop runs inside an SSH shell on a gateway, its `127.0.0.1` login URL is on
that gateway. `--no-browser` does not make it reachable from a laptop. Install
and run JupyHop on the laptop/browser computer, using ProxyJump to reach the
destination. SSH forwarding policy must permit the connection through every
required hop.
