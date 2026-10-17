from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable, Iterable
from urllib.parse import urlsplit, urlunsplit


Resolver = Callable[[str, int], Awaitable[Iterable[str]]]
BLOCKED_HOSTS = {"localhost", "metadata.google.internal", "metadata.azure.internal"}


async def system_resolver(host: str, port: int) -> set[str]:
    results = await asyncio.to_thread(
        socket.getaddrinfo, host, port, type=socket.SOCK_STREAM,
    )
    return {entry[4][0] for entry in results}


def parse_allowlist(values: tuple[str, ...]) -> set[tuple[str, int]]:
    allowed: set[tuple[str, int]] = set()
    for value in values:
        host, separator, raw_port = value.strip().lower().rpartition(":")
        if not separator or not host or not raw_port.isdigit():
            raise RuntimeError("UPSTREAM_INTERNAL_ALLOWLIST entries must use host:port")
        allowed.add((host.rstrip("."), int(raw_port)))
    return allowed


async def validate_upstream_url(
    value: str, allowlist: tuple[str, ...], resolver: Resolver = system_resolver,
) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("upstream URL must be absolute HTTP(S)")
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise ValueError("upstream URL cannot contain userinfo or a fragment")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as error:
        raise ValueError("upstream URL port is invalid") from error
    host = parsed.hostname.lower().rstrip(".")
    if (host, port) in parse_allowlist(allowlist):
        return urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path or "/", parsed.query, ""))
    if parsed.scheme != "https":
        raise ValueError("public upstream URLs must use HTTPS")
    if host in BLOCKED_HOSTS or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("upstream host is not allowed")
    try:
        literal = ipaddress.ip_address(host)
        addresses = {str(literal)}
    except ValueError:
        try:
            addresses = set(await asyncio.wait_for(resolver(host, port), timeout=3.0))
        except TimeoutError as error:
            raise ValueError("upstream host resolution timed out") from error
        except (OSError, socket.gaierror) as error:
            raise ValueError("upstream host could not be resolved") from error
    if not addresses:
        raise ValueError("upstream host did not resolve")
    try:
        if any(not ipaddress.ip_address(address).is_global for address in addresses):
            raise ValueError("upstream host resolves to a blocked network")
    except ValueError as error:
        if str(error) == "upstream host resolves to a blocked network":
            raise
        raise ValueError("upstream host resolution is invalid") from error
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path or "/", parsed.query, ""))
