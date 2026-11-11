"""Check native Jupyter cookies in the private SSH helper and local client."""

import re
from email.utils import parsedate_to_datetime
from http.cookies import SimpleCookie
from urllib.parse import quote


def native_cookie(headers: list[str], port: int, base: str) -> tuple[str, str]:
    name = f"username-127-0-0-1-{port}"
    matches = [value for value in headers if value.partition("=")[0].strip() == name]
    if len(matches) != 1:
        raise ValueError
    header = matches[0]
    if len(header) > 4096 or any(not 32 <= ord(c) <= 126 for c in header):
        raise ValueError
    parts = header.split(";")
    attributes = {}
    for part in parts[1:]:
        key, sep, value = part.strip().partition("=")
        key = key.lower()
        if key in attributes or key not in {"path", "expires", "httponly", "samesite"}:
            raise ValueError
        attributes[key] = value if sep else None
    if (
        attributes.get("path") != base
        or "httponly" not in attributes
        or attributes["httponly"] is not None
        or (attributes.get("samesite") or "").lower() != "lax"
    ):
        raise ValueError
    if "expires" in attributes:
        expiry = attributes["expires"]
        if expiry is None or parsedate_to_datetime(expiry).tzinfo is None:
            raise ValueError
    parsed = SimpleCookie()
    parsed.load(header)
    cookie = parsed.get(name)
    if (
        set(parsed) != {name}
        or cookie is None
        or not re.fullmatch(r"[A-Za-z0-9|:+/=_-]+", cookie.value)
    ):
        raise ValueError
    return header, name + "=" + cookie.coded_value


def login_path(base: str) -> str:
    return base + "login?next=" + quote(base, safe="")
