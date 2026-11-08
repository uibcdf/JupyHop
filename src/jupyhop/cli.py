"""SSH diagnostics and read-only access to existing remote Jupyter servers."""

import argparse
import json
import signal
import sys
import webbrowser
from pathlib import Path
from typing import Any

from jupyhop import __version__
from jupyhop.discovery import discover, select_server
from jupyhop.doctor import diagnose
from jupyhop.errors import JupyHopError, OwnershipError
from jupyhop.opening import open_connection
from jupyhop.ssh import SSHTransport


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jupyhop",
        description="Discover and open existing Jupyter servers through OpenSSH.",
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
                "list": "Alias for discover on one SSH host.",
                "open": "Open an existing server; keep its owned tunnel attached until Ctrl-C.",
            }[name],
        )
        _connection_arguments(command, multiple=True)
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
    stop = commands.add_parser(
        "stop",
        help="Refuse lifecycle control of discovered servers (managed stop is not implemented).",
    )
    stop.add_argument("host")
    stop.add_argument("session")
    return parser


def _connection_arguments(parser: argparse.ArgumentParser, *, multiple: bool) -> None:
    parser.add_argument(
        "host", help="Existing OpenSSH alias; routing/User/keys come from SSH config."
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
            default="python3",
            help="python3 or an absolute remote Python path; no activation.",
        )
    parser.add_argument(
        "--ssh-config", type=Path, help="Pass a config file directly to OpenSSH (-F)."
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20,
        help="Deadline per SSH probe/startup in seconds (1–300, default 20).",
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
                            "origin": "unmanaged",
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
    try:
        if args.command == "stop":
            raise OwnershipError(
                "Discovered servers are unmanaged: JupyHop cannot stop, restart or adopt them. Managed lifecycle commands are not implemented. No SSH command was sent."
            )
        transport = SSHTransport(args.host, config=args.ssh_config, timeout=args.timeout)
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
                        f"{server['id']}  unmanaged  {server['state']}  port={server['port']}  {server['reason']}"
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
        print(
            "jupyhop: interrupted; owned tunnel closed, remote sessions were not modified.",
            file=sys.stderr,
        )
        return 130
    return 2
