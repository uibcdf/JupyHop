"""Revalidate on the exact forwarding connection, then expose a login URL."""

import http.client
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import quote

from jupyhop._discovery_probe import Unsupported, endpoint
from jupyhop.discovery import probe
from jupyhop.errors import DiscoveryError, PrerequisiteError, TunnelError
from jupyhop.ssh import SSHTransport
from jupyhop.tunnel import Tunnel


@contextmanager
def open_connection(
    transport: SSHTransport,
    report: dict[str, Any],
    server: dict[str, Any],
    pythons: list[str] | None = None,
) -> Iterator[tuple[Tunnel, str]]:
    with Tunnel(transport, server["port"]) as tunnel:
        found = False
        for python in pythons or ["python3"]:
            try:
                data = probe(tunnel, python, server["sources"][:16], transport.timeout)
            except PrerequisiteError:
                continue
            if data["identity"] != report["identity"]:
                raise DiscoveryError(
                    "The forwarding connection resolved to a different remote account/host. No browser was opened."
                )
            if any(
                s["id"] == server["id"]
                and s["state"] == "ready"
                and s.get("observed_id", s["id"]) == server.get("observed_id", server["id"])
                for s in data["servers"]
            ):
                found = True
                break
        if not found:
            raise DiscoveryError(
                "Server identity or listener changed before opening. Discover again; no remote process was modified."
            )
        try:
            if endpoint(tunnel.local_port, server["base_url"]) != server["version"]:
                raise Unsupported
        except (Unsupported, OSError, ValueError, AttributeError, http.client.HTTPException):
            raise TunnelError(
                "The forwarded Jupyter endpoint or authentication check failed. Check SSH forwarding policy and discover again; authentication was not bypassed."
            ) from None
        base = f"http://127.0.0.1:{tunnel.local_port}{server['base_url']}"
        yield tunnel, base + "login?next=" + quote(server["base_url"], safe="")
