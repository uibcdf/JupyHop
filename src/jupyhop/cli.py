"""Initial CLI: read-only SSH diagnostics. Jupyter workflows begin at M2."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jupyhop import __version__
from jupyhop.doctor import diagnose
from jupyhop.errors import JupyHopError
from jupyhop.ssh import SSHTransport


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jupyhop",
        description="SSH-native Jupyter foundations; currently read-only diagnostics.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser(
        "doctor", help="Check SSH and one remote Python/Jupyter environment (read-only)."
    )
    doctor.add_argument(
        "host", help="Existing OpenSSH alias; routing/User/keys come from SSH config."
    )
    doctor.add_argument(
        "--remote-python",
        default="python3",
        help="python3 or an absolute remote Python path; no environment activation.",
    )
    doctor.add_argument(
        "--ssh-config", type=Path, help="Pass a config file directly to OpenSSH (-F)."
    )
    doctor.add_argument(
        "--timeout",
        type=float,
        default=20,
        help="Total SSH probe deadline in seconds (1–300, default 20).",
    )
    doctor.add_argument(
        "--json",
        action="store_true",
        help="Emit allowlisted, nonsecret JSON; diagnostics stay on stderr.",
    )
    return parser


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


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        transport = SSHTransport(args.host, config=args.ssh_config, timeout=args.timeout)
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
            "jupyhop: diagnostic interrupted; remote sessions were not modified.", file=sys.stderr
        )
        return 130
    return 2
