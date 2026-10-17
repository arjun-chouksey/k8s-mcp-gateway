from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseSettings:
    url: str

    @classmethod
    def from_env(cls) -> DatabaseSettings:
        url = os.getenv("DATABASE_URL", "").strip()
        if not url:
            raise RuntimeError("Missing required environment variable: DATABASE_URL")
        if not url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise RuntimeError("DATABASE_URL must use PostgreSQL")
        return cls(url=url)


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        raise RuntimeError(f"{name} must be true or false")
    return normalized == "true"


@dataclass(frozen=True)
class AppSettings:
    database_url: str
    allowed_origin: str
    cookie_secure: bool
    api_key_pepper: str
    upstream_credential_key: str
    upstream_internal_allowlist: tuple[str, ...] = (
        "woocommerce-mcp.mcp.svc.cluster.local:8000",
        "currency-mcp.mcp.svc.cluster.local:8000",
        "policy-mcp.mcp.svc.cluster.local:8000",
    )
    session_ttl_seconds: int = 28_800
    invite_ttl_seconds: int = 86_400
    login_max_failures: int = 5
    login_window_seconds: int = 300
    upstream_refresh_seconds: int = 30

    @classmethod
    def from_env(cls) -> AppSettings:
        database_url = DatabaseSettings.from_env().url
        allowed_origin = os.getenv("ALLOWED_ORIGIN", "").strip().rstrip("/")
        if not allowed_origin.startswith(("http://", "https://")):
            raise RuntimeError("ALLOWED_ORIGIN must be an absolute HTTP(S) origin")
        session_ttl = int(os.getenv("SESSION_TTL_SECONDS", "28800"))
        invite_ttl = int(os.getenv("INVITE_TTL_SECONDS", "86400"))
        max_failures = int(os.getenv("LOGIN_MAX_FAILURES", "5"))
        window = int(os.getenv("LOGIN_WINDOW_SECONDS", "300"))
        refresh_seconds = int(os.getenv("UPSTREAM_REFRESH_SECONDS", "30"))
        api_key_pepper = os.getenv("API_KEY_PEPPER", "")
        if len(api_key_pepper) < 32:
            raise RuntimeError("API_KEY_PEPPER must be at least 32 characters")
        upstream_credential_key = os.getenv("UPSTREAM_CREDENTIAL_KEY", "")
        if not upstream_credential_key:
            raise RuntimeError("UPSTREAM_CREDENTIAL_KEY is required")
        allowlist = tuple(filter(None, (
            value.strip() for value in os.getenv(
                "UPSTREAM_INTERNAL_ALLOWLIST",
                "woocommerce-mcp.mcp.svc.cluster.local:8000,"
                "currency-mcp.mcp.svc.cluster.local:8000,"
                "policy-mcp.mcp.svc.cluster.local:8000",
            ).split(",")
        )))
        if min(session_ttl, invite_ttl, max_failures, window, refresh_seconds) <= 0:
            raise RuntimeError("session and login throttling settings must be positive")
        return cls(
            database_url=database_url,
            allowed_origin=allowed_origin,
            cookie_secure=_bool_env("COOKIE_SECURE", True),
            api_key_pepper=api_key_pepper,
            upstream_credential_key=upstream_credential_key,
            upstream_internal_allowlist=allowlist,
            session_ttl_seconds=session_ttl,
            invite_ttl_seconds=invite_ttl,
            login_max_failures=max_failures,
            login_window_seconds=window,
            upstream_refresh_seconds=refresh_seconds,
        )
