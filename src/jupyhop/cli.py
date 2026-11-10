"""SSH diagnostics and read-only access to existing remote Jupyter servers."""

import argparse
import json
import signal
import sys
import webbrowser
from collections import Counter
from pathlib import Path
from typing import Any

from jupyhop import __version__
from jupyhop.config import Config, Host, load_config
from jupyhop.connection import ConnectionPool
from jupyhop.controls import control, show_inventory
from jupyhop.diagnostics import support_report
from jupyhop.discovery import discover, select_server
from jupyhop.doctor import diagnose
from jupyhop.errors import JupyHopError, SelectionError
from jupyhop.fleet import inventory, select_inventory
from jupyhop.managed import new_id, password_input, require_ready, start
from jupyhop.opening import open_connection
from jupyhop.selection import choose, validate_name
from jupyhop.session_inventory import inspect_sessions
from jupyhop.ssh import SSHTransport, validate_alias


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
    doctor.add_argument(
        "--report",
        action="store_true",
        help="Emit a versioned shareable JSON support report with local/remote versions, excluding identities, paths and credentials; never upload it.",
    )
    for name in ("discover", "list", "open"):
        command = commands.add_parser(
            name,
            aliases=["resume"] if name == "open" else [],
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
        if name in {"discover", "list"}:
            command.add_argument(
                "--all",
                dest="all_candidates",
                action="store_true",
                help="Show individual unmanaged diagnostics, including stale metadata; JSON always retains the bounded sample.",
            )
        if name == "open":
            target = command.add_mutually_exclusive_group()
            target.add_argument(
                "session",
                nargs="?",
                help="Exact server ID from discover; required when ambiguous without a TTY.",
            )
            target.add_argument(
                "--name",
                dest="selector_name",
                help="Select one exact current managed session name.",
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
        help="Read the new Jupyter password from protected stdin; SSH passwords stay in native terminal prompts. Never supply passwords in argv.",
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
        _connection_arguments(control, multiple=False, host_nargs="?")
        target = control.add_mutually_exclusive_group()
        target.add_argument(
            "session",
            nargs="?",
            help="Exact managed UUID; omit for terminal selection (status shows inventory).",
        )
        target.add_argument(
            "--name",
            dest="selector_name",
            help="Select one exact current managed name; lifecycle selection requires a terminal.",
        )
        if name == "status":
            control.add_argument(
                "--history",
                action="store_true",
                help="Inspect private archive history; --json uses versioned inventory output.",
            )
            control.add_argument(
                "--history-offset",
                type=int,
                default=0,
                help="Bounded archive page offset (0–4096; pages contain at most 64 entries).",
            )
        if name == "stop":
            completion = control.add_mutually_exclusive_group()
            completion.add_argument(
                "--archive",
                dest="archive_after",
                action="store_true",
                help="Explicitly authorize archiving after confirmed stop (also for UUID --yes scripts).",
            )
            completion.add_argument(
                "--keep-record",
                action="store_true",
                help="Keep the stopped record; interactive stop otherwise offers stop and archive.",
            )
        if name != "status":
            control.add_argument(
                "--yes",
                action="store_true",
                help="Explicitly authorize this lifecycle action on the exact UUID without a terminal prompt.",
            )
    manage = commands.add_parser(
        "manage", help="Inspect sessions and choose open, stop or archive in a terminal."
    )
    _connection_arguments(manage, multiple=False, host_nargs="?")
    manage.add_argument(
        "--runtime-dir",
        action="append",
        default=[],
        help="Additional known remote runtime directory (repeatable).",
    )
    manage.add_argument(
        "--no-browser",
        action="store_true",
        help="Print a login URL while keeping the selected tunnel attached.",
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
        "--batch",
        action="store_true",
        help="Disable SSH authentication prompts; require keys/agent or another noninteractive method.",
    )
    parser.add_argument(
        "--ssh-auth-timeout",
        type=float,
        default=120,
        help="Deadline for native terminal SSH authentication in seconds (1–600, default 120).",
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
        if issue == "entry_limit" and any(
            value in report["coverage"]["issues"] for value in ("sample_limit", "scan_limit")
        ):
            continue
        advice = {
            "sample_limit": "The retained diagnostic sample is bounded; this is not a total server count. Verified endpoints are still considered within the scan bounds.",
            "scan_limit": "A runtime directory reached the 512-entry scan bound; search coverage is partial. Inspect known runtime paths.",
            "entry_limit": "A scan or retained sample reached a bound; a longer SSH timeout cannot enlarge those limits.",
            "time_limit": "The bounded remote probe reached its time budget. Inspect the selected known paths and environment.",
        }.get(issue, "Check --runtime-dir, --remote-python and --timeout.")
        print(
            f"Discovery diagnostic: {issue}. {advice}",
            file=sys.stderr,
        )


def _servers(report: dict[str, Any], *, all_candidates: bool, prefix: str = "") -> None:
    hidden: Counter[str] = Counter()
    for server in report["servers"]:
        if server["origin"] == "unmanaged" and server["state"] != "ready" and not all_candidates:
            hidden[server["state"]] += 1
            continue
        print(
            f"{prefix}{server['id']}  {server['origin']}  {server.get('name') or ''}  {server['state']}  port={server['port']}  {server['reason']}"
        )
    if hidden:
        counts = ", ".join(f"{state}={count}" for state, count in sorted(hidden.items()))
        print(
            f"{prefix}Unmanaged diagnostics retained in this partial sample: {counts}. Use --all for individual rows; these are not running-server counts.",
            file=sys.stderr,
        )


class _SignalInterrupt(KeyboardInterrupt):
    pass


def _interrupted(signum: int, frame: Any) -> None:
    raise _SignalInterrupt


def _fleet(args: argparse.Namespace, config: Config) -> int:
    hosts = args.host if args.command == "list" else None
    data = inventory(
        config,
        hosts,
        ssh_config=args.ssh_config,
        timeout=20 if args.timeout is None else args.timeout,
        pythons=args.remote_python,
        paths=args.runtime_dir,
        connections=args.connections,
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
            data,
            interactive=not args.json and sys.stdin.isatty() and sys.stdout.isatty(),
            name=args.selector_name,
        )
        args.host, args.session = report["host"], server["id"]
        args.selector_name = None
        args.remote_python, _ = config.discovery_options(
            args.host, args.remote_python, args.runtime_dir
        )
        return _open(
            args,
            SSHTransport(
                args.host,
                config=args.ssh_config,
                timeout=20 if args.timeout is None else args.timeout,
                connections=args.connections,
            ),
            report,
        )
    if args.json:
        print(json.dumps(data, ensure_ascii=True))
    else:
        for entry in data["hosts"]:
            if entry["ok"]:
                _servers(
                    entry["report"], all_candidates=args.all_candidates, prefix=entry["host"] + "  "
                )
    if not any(entry["ok"] for entry in data["hosts"]):
        return 3
    return 14 if any(not entry["ok"] for entry in data["hosts"]) else 0


def _open(args: argparse.Namespace, transport: SSHTransport, report: dict[str, Any]) -> int:
    server = select_server(
        report,
        args.session,
        interactive=not args.json and sys.stdin.isatty() and sys.stdout.isatty(),
        name=getattr(args, "selector_name", None),
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


def _choose_host(config: Config, *, interactive: bool) -> str:
    if not interactive:
        raise SelectionError(
            "Supply an explicit SSH host alias for this command; no SSH command was sent."
        )
    value = "<enter another alias>"
    if config.hosts:
        value = choose(
            [*config.hosts, value], str, interactive=True, prompt="Select an SSH host number: "
        )
    if value == "<enter another alias>":
        print("Existing SSH alias (Enter cancels): ", end="", file=sys.stderr, flush=True)
        value = sys.stdin.readline().strip()
        if not value:
            raise SelectionError("Host selection cancelled; no SSH command was sent.")
    return validate_alias(value)


def _manage(args: argparse.Namespace, transport: SSHTransport, config: Config) -> int:
    descriptions = {
        "open": "Open/resume an existing server",
        "stop": "Stop a managed server (offer archive)",
        "archive": "Archive inactive managed evidence",
        "history": "Inspect archived history",
        "refresh": "Refresh inventory",
        "exit": "Exit management",
    }
    history = False
    while True:
        observed = inspect_sessions(transport, python=args.remote_python)
        show_inventory(observed, history=history)
        history = False
        try:
            action = choose(
                list(descriptions),
                descriptions.__getitem__,
                interactive=True,
                prompt="Select an action number (Enter exits): ",
            )
        except SelectionError:
            return 0
        if action == "exit":
            return 0
        if action in {"history", "refresh"}:
            history = action == "history"
            continue
        try:
            if action == "open":
                pythons, paths = config.discovery_options(
                    args.host, [args.remote_python], args.runtime_dir
                )
                report = discover(transport, pythons, paths)
                _coverage(report)
                server = select_server(report, None, interactive=True)
                opening = argparse.Namespace(
                    **(
                        vars(args)
                        | {"session": server["id"], "selector_name": None, "remote_python": pythons}
                    )
                )
                try:
                    _open(opening, transport, report)
                except _SignalInterrupt:
                    raise
                except KeyboardInterrupt:
                    args.connections.discard(transport)
                    print(
                        "Tunnel closed; remote server remains running. Returning to management; SSH may ask you to authenticate again.",
                        file=sys.stderr,
                    )
            else:
                selected = argparse.Namespace(
                    **(
                        vars(args)
                        | {
                            "command": action,
                            "session": None,
                            "selector_name": None,
                            "yes": False,
                            "archive_after": False,
                            "keep_record": False,
                            "history": False,
                            "history_offset": 0,
                        }
                    )
                )
                try:
                    control(selected, transport)
                except KeyboardInterrupt:
                    args.lifecycle_phase = getattr(selected, "lifecycle_phase", None)
                    raise
        except JupyHopError as error:
            print(f"jupyhop: {error}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "resume":
        args.command = "open"
    launch_id = None
    connections = None
    handlers = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGHUP)}
    try:
        for number in handlers:
            signal.signal(number, _interrupted)
        config = load_config(args.config)
        if getattr(args, "selector_name", None) is not None:
            validate_name(args.selector_name)
        connections = ConnectionPool(batch=args.batch, auth_timeout=args.ssh_auth_timeout)
        args.connections = connections
        if args.command == "manage" and (args.json or not sys.stdin.isatty()):
            raise SelectionError(
                "Manage requires a terminal; use status --history --json or explicit UUID commands for scripts."
            )
        if args.command == "list" or args.command == "open" and args.host is None and config.hosts:
            return _fleet(args, config)
        if args.host is None:
            args.host = _choose_host(config, interactive=not args.json and sys.stdin.isatty())
        host = config.hosts.get(args.host, Host())
        args.timeout = 20 if args.timeout is None else args.timeout
        if args.command in {"discover", "open"}:
            args.remote_python, args.runtime_dir = config.discovery_options(
                args.host, args.remote_python, args.runtime_dir
            )
        else:
            args.remote_python = args.remote_python or host.remote_python
        transport = SSHTransport(
            args.host, config=args.ssh_config, timeout=args.timeout, connections=connections
        )
        if args.command in {"status", "stop", "archive"}:
            return control(args, transport)
        if args.command == "manage":
            return _manage(args, transport, config)
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
                _servers(report, all_candidates=args.all_candidates)
            ready = any(s["state"] == "ready" for s in report["servers"])
            if not ready:
                print(
                    "No verified server found in the searched paths. Try --runtime-dir or --remote-python; this partial search does not prove no servers are running.",
                    file=sys.stderr,
                )
            return 0 if ready else 6
        if args.report:
            report, code = support_report(transport, args.remote_python)
            print(json.dumps(report, ensure_ascii=True, indent=None if args.json else 2))
            return code
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
            if args.command == "archive" or getattr(args, "lifecycle_phase", None) == "archive"
            else "jupyhop: stop interrupted; remote outcome is unknown. Use status before retrying."
            if args.command == "stop" or getattr(args, "lifecycle_phase", None) == "stop"
            else f"jupyhop: interrupted; session request {launch_id} may remain running. Owned tunnel closed; use discover before retrying start."
            if launch_id
            else "jupyhop: interrupted; owned tunnel closed, remote sessions were not modified."
        )
        print(message, file=sys.stderr)
        return 130
    finally:
        try:
            if connections is not None:
                connections.close()
        finally:
            for number, handler in handlers.items():
                signal.signal(number, handler)
    return 2
