"""SSH diagnostics and read-only access to existing remote Jupyter servers."""

import argparse
import json
import signal
import sys
import webbrowser
from pathlib import Path
from typing import Any

from jupyhop import __version__
from jupyhop.config import Config, Host, load_config
from jupyhop.discovery import discover, select_server
from jupyhop.doctor import diagnose
from jupyhop.errors import JupyHopError, OwnershipError
from jupyhop.fleet import inventory, select_inventory
from jupyhop.lifecycle import lifecycle, require_lifecycle_ok, validate_managed_id
from jupyhop.managed import new_id, password_input, require_ready, start
from jupyhop.opening import open_connection
from jupyhop.ssh import SSHTransport


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jupyhop",
        description="Discover, launch and reconnect to remote Jupyter servers through OpenSSH.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser(
        "doctor", help="Check SSH and one remote Python/Jupyter environment (read-only)."
    )
    _connection_arguments(doctor, multiple=False)
    for name in ("discover", "list", "open"):
        command = commands.add_parser(
            name,
            help={
                "discover": "Find verified current-user Jupyter servers (partial, read-only).",
                "list": "Inventory explicit SSH aliases, or all configured hosts when omitted.",
                "open": "Open an existing server; keep its owned tunnel attached until Ctrl-C.",
            }[name],
        )
        _connection_arguments(
            command,
            multiple=True,
            host_nargs="*" if name == "list" else "?" if name == "open" else None,
        )
        command.add_argument(
            "--runtime-dir",
            action="append",
            default=[],
            help="Additional remote runtime directory (repeatable; absolute or ~/).",
        )
        if name == "open":
            command.add_argument(
                "session",
                nargs="?",
                help="Exact server ID from discover; required when ambiguous without a TTY.",
            )
            command.add_argument(
                "--no-browser",
                action="store_true",
                help="Print a token-free login URL and keep the tunnel attached.",
            )
    launch = commands.add_parser(
        "start", help="Launch a password-authenticated owned Jupyter server using private tmux."
    )
    _connection_arguments(launch, multiple=False)
    launch.add_argument(
        "--env",
        help="Named launch profile from the optional JupyHop config; not a Conda activation command.",
    )
    launch.add_argument(
        "--server-python",
        help="Remote Jupyter Python executable; overrides the selected profile, otherwise defaults to the helper.",
    )
    launch.add_argument(
        "--workdir",
        help="Remote working directory; relative paths resolve against remote home.",
    )
    launch.add_argument(
        "--name", help="Unique managed session display name (1–64 simple characters)."
    )
    launch.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read one password line from a protected stdin source instead of prompting. Never supply passwords in argv.",
    )
    launch.add_argument(
        "--no-open",
        action="store_true",
        help="Return the launch result without a local tunnel/browser.",
    )
    launch.add_argument(
        "--no-browser",
        action="store_true",
        help="Print the login URL and keep the tunnel attached.",
    )
    for name in ("status", "stop", "archive"):
        control = commands.add_parser(
            name,
            help={
                "status": "Observe managed sessions and reconcile interrupted launch readiness.",
                "stop": "Gracefully stop one verified managed session; terminates its kernels.",
                "archive": "Move an inactive managed record to private archive, preserving evidence and releasing its name.",
            }[name],
        )
        _connection_arguments(control, multiple=False)
        control.add_argument(
            "session",
            nargs="?" if name == "status" else None,
            help="Exact managed session UUID; names and unmanaged IDs are refused.",
        )
        if name != "status":
            control.add_argument(
                "--yes",
                action="store_true",
                help="Explicitly authorize this lifecycle action on the exact UUID without a terminal prompt.",
            )
    return parser


def _connection_arguments(
    parser: argparse.ArgumentParser, *, multiple: bool, host_nargs: str | None = None
) -> None:
    parser.add_argument(
        "host",
        nargs=host_nargs,
        help="Existing OpenSSH alias; routing/User/keys come from SSH config.",
    )
    if multiple:
        parser.add_argument(
            "--remote-python",
            action="append",
            help="Explicit remote Python executable (repeatable; default python3).",
        )
    else:
        parser.add_argument(
            "--remote-python",
            help="python3 or an absolute remote Python path; no activation.",
        )
    parser.add_argument(
        "--ssh-config", type=Path, help="Pass a config file directly to OpenSSH (-F)."
    )
    parser.add_argument(
        "--timeout",
        type=float,
        help="Deadline per SSH probe/startup in seconds (1–300, default 20).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional local JupyHop TOML file (default: XDG config/jupyhop/config.toml).",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit nonsecret JSON; diagnostics stay on stderr."
    )


def _display(report: dict[str, Any]) -> None:
    data = report["data"]
    identity = data["identity"]
    print(f"SSH OK: {report['host']} as {identity['user']} (uid {identity['uid']})")
    print(f"Python {data['python']['version']}: {data['python']['executable']}")
    for name in ("jupyter_server", "jupyter_core"):
        print(f"{name}: {data[name]['version'] or 'missing in selected interpreter'}")
    for entry in data["runtime_dirs"]:
        print(f"Runtime directory ({entry['status']}): {entry['path']}")
    managers = data["process_managers"]
    print(
        f"Process-manager probes: systemd --user {managers['systemd_user']}; tmux {'found' if managers['tmux'] else 'missing'}"
    )
    print("Coverage: selected interpreter only; no server discovery performed.")


def _coverage(report: dict[str, Any]) -> None:
    print(
        "Discovery is partial: only known runtime paths were searched; other environments or paths may exist.",
        file=sys.stderr,
    )
    for path in report["coverage"]["paths"]:
        if path["status"] != "ok":
            print(f"Runtime directory {path['status']}: {path['path']}", file=sys.stderr)
    for issue in report["coverage"]["issues"]:
        print(
            f"Discovery diagnostic: {issue}. Check --runtime-dir, --remote-python and --timeout.",
            file=sys.stderr,
        )


def _interrupted(signum: int, frame: Any) -> None:
    raise KeyboardInterrupt


def _fleet(args: argparse.Namespace, config: Config) -> int:
    hosts = args.host if args.command == "list" else None
    data = inventory(
        config,
        hosts,
        ssh_config=args.ssh_config,
        timeout=20 if args.timeout is None else args.timeout,
        pythons=args.remote_python,
        paths=args.runtime_dir,
    )
    for entry in data["hosts"]:
        if not entry["ok"]:
            print(f"{entry['host']}: {entry['error']['message']}", file=sys.stderr)
        else:
            print(
                f"{entry['host']}: discovery is partial; only known runtime paths were searched.",
                file=sys.stderr,
            )
    if args.command == "open":
        report, server = select_inventory(
            data, interactive=not args.json and sys.stdin.isatty() and sys.stdout.isatty()
        )
        args.host, args.session = report["host"], server["id"]
        args.remote_python, _ = config.discovery_options(
            args.host, args.remote_python, args.runtime_dir
        )
        return _open(
            args,
            SSHTransport(
                args.host,
                config=args.ssh_config,
                timeout=20 if args.timeout is None else args.timeout,
            ),
            report,
        )
    if args.json:
        print(json.dumps(data, ensure_ascii=True))
    else:
        for entry in data["hosts"]:
            if entry["ok"]:
                for server in entry["report"]["servers"]:
                    print(
                        f"{entry['host']}  {server['id']}  {server['origin']}  {server.get('name') or ''}  {server['state']}  port={server['port']}"
                    )
    if not any(entry["ok"] for entry in data["hosts"]):
        return 3
    return 14 if any(not entry["ok"] for entry in data["hosts"]) else 0


def _open(args: argparse.Namespace, transport: SSHTransport, report: dict[str, Any]) -> int:
    server = select_server(
        report,
        args.session,
        interactive=not args.json and sys.stdin.isatty() and sys.stdout.isatty(),
    )
    handlers = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGHUP)}
    try:
        for number in handlers:
            signal.signal(number, _interrupted)
        with open_connection(transport, report, server, args.remote_python) as (tunnel, url):
            if args.json:
                print(
                    json.dumps(
                        {
                            "host": transport.host,
                            "id": server["id"],
                            "origin": server["origin"],
                            "url": url,
                            "authentication": "jupyter-login",
                            "tunnel": "attached",
                        }
                    ),
                    flush=True,
                )
            else:
                print(url, flush=True)
            print(
                "Tunnel attached. Log in with your existing Jupyter password/token. Ctrl-C closes only this tunnel; the remote server is not stopped.",
                file=sys.stderr,
                flush=True,
            )
            if not args.no_browser:
                try:
                    opened = webbrowser.open(url, new=2)
                except (webbrowser.Error, OSError):
                    opened = False
                if not opened:
                    print(
                        "Browser unavailable. Open the printed login URL on this client, or use --no-browser; the tunnel remains attached.",
                        file=sys.stderr,
                        flush=True,
                    )
            tunnel.wait()
    finally:
        for number, handler in handlers.items():
            signal.signal(number, handler)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    launch_id = None
    try:
        config = load_config(args.config)
        if args.command == "list" or args.command == "open" and args.host is None:
            return _fleet(args, config)
        host = config.hosts.get(args.host, Host())
        args.timeout = 20 if args.timeout is None else args.timeout
        if args.command in {"discover", "open"}:
            args.remote_python, args.runtime_dir = config.discovery_options(
                args.host, args.remote_python, args.runtime_dir
            )
        else:
            args.remote_python = args.remote_python or host.remote_python
        if args.command in {"stop", "archive"}:
            validate_managed_id(args.session)
            if not args.yes:
                if not sys.stdin.isatty() or args.json:
                    raise OwnershipError(
                        (
                            "Stopping terminates kernels/computations. "
                            if args.command == "stop"
                            else "Archiving moves inactive recovery evidence and releases its name. "
                        )
                        + "Supply an exact UUID and --yes, or use a terminal for confirmation. No SSH command was sent."
                    )
                print(
                    (
                        f"Stop managed session {args.session}? This terminates its kernels and computations. "
                        if args.command == "stop"
                        else f"Archive inactive session {args.session}? Its evidence is retained; orphaned kernels are not stopped. "
                    )
                    + f"Type {args.command} to confirm: ",
                    end="",
                    file=sys.stderr,
                    flush=True,
                )
                if sys.stdin.readline().strip() != args.command:
                    raise OwnershipError("Lifecycle action cancelled; no SSH command was sent.")
        transport = SSHTransport(args.host, config=args.ssh_config, timeout=args.timeout)
        if args.command in {"status", "stop", "archive"}:
            report = lifecycle(transport, args.command, args.session, python=args.remote_python)
            if args.json:
                print(json.dumps(report, ensure_ascii=True))
            else:
                for server in report["servers"]:
                    print(
                        f"{server['id']}  managed  {server['name']}  {server['state']}  {server['reason']}"
                    )
                if report.get("archived") is not None:
                    print(f"Archived {report['archived']['id']} -> {report['archived']['path']}")
                elif not report["servers"]:
                    print("No managed session records found in this host/account registry.")
            require_lifecycle_ok(report)
            return 0
        if args.command == "start":
            profile = config.profile(args.host, args.env)
            password = password_input(args.password_stdin)
            launch_id = new_id()
            print(
                f"Starting managed session {launch_id}…",
                file=sys.stderr,
            )
            report = start(
                transport,
                server_python=args.server_python
                or (profile.server_python if profile else args.remote_python),
                helper_python=args.remote_python,
                workdir=args.workdir
                if args.workdir is not None
                else profile.workdir
                if profile
                else "~",
                name=args.name,
                password=password,
                session_id=launch_id,
            )
            del password
            if args.no_open or report["state"] != "ready":
                if args.json:
                    print(json.dumps(report, ensure_ascii=True))
                else:
                    print(f"{report['id']}  managed  {report['state']}")
                require_ready(report)
                return 0
            require_ready(report)
            args.session = launch_id
            pythons = [args.remote_python]
            args.remote_python = pythons
            return _open(
                args, transport, {"identity": report["identity"], "servers": [report["server"]]}
            )
        if args.command != "doctor":
            report = discover(transport, args.remote_python, args.runtime_dir)
            _coverage(report)
            if args.command == "open":
                return _open(args, transport, report)
            if args.json:
                print(json.dumps(report, ensure_ascii=True))
            else:
                for server in report["servers"]:
                    print(
                        f"{server['id']}  {server['origin']}  {server.get('name') or ''}  {server['state']}  port={server['port']}  {server['reason']}"
                    )
            ready = any(s["state"] == "ready" for s in report["servers"])
            if not ready:
                print(
                    "No verified server found in the searched paths. Try --runtime-dir or --remote-python; this partial search does not prove no servers are running.",
                    file=sys.stderr,
                )
            return 0 if ready else 6
        report = diagnose(transport, args.remote_python)
        if args.json:
            print(json.dumps(report, ensure_ascii=True))
        else:
            _display(report)
        if not report["ok"]:
            print(
                "Missing prerequisites: "
                + ", ".join(report["missing"])
                + ". Select an existing Jupyter environment with --remote-python /absolute/path/to/python. Nothing was installed remotely.",
                file=sys.stderr,
            )
            return 4
        return 0
    except ValueError as exc:
        parser.error(str(exc))
    except JupyHopError as exc:
        print(f"jupyhop: {exc}", file=sys.stderr)
        return exc.exit_code
    except KeyboardInterrupt:
        message = (
            "jupyhop: archive interrupted; retry archive with the same UUID to reconcile. No automatic deletion was attempted."
            if args.command == "archive"
            else "jupyhop: stop interrupted; remote outcome is unknown. Use status before retrying."
            if args.command == "stop"
            else f"jupyhop: interrupted; session request {launch_id} may remain running. Owned tunnel closed; use discover before retrying start."
            if launch_id
            else "jupyhop: interrupted; owned tunnel closed, remote sessions were not modified."
        )
        print(message, file=sys.stderr)
        return 130
    return 2
