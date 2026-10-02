"""Shared pilot bearer-key minting (HS256, EUROSETU_JWT_SECRET).

Single source of truth for the JWT shape verified by ``app/security.py``.
Used by:
- ``POST /api/admin/mint`` (in-app manual queue)
- ``scripts/mint_pilot_token.py`` (local CLI)
- ``workers/pilot-key-minter.js`` (Cloudflare Email Worker, WebCrypto port -
  keep claims identical; see workers/README.md for the parity test vector).

Claims: {"sub": requester email, "exp": now+days*86400, "iat": now,
          "tenant_id": tenant, "tenants": {tenant: roles}}
Header: {"alg": "HS256", "typ": "JWT"}
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

DEFAULT_TENANT = os.getenv("EUROSETU_DEFAULT_TENANT", "tenant-a")
DEFAULT_ROLES = tuple(
    r.strip()
    for r in os.getenv(
        "EUROSETU_DEFAULT_PILOT_ROLES", "pilot_viewer,pilot_contributor"
    ).split(",")
    if r.strip()
) or ("pilot_viewer", "pilot_contributor")
DEFAULT_DAYS = int(os.getenv("EUROSETU_DEFAULT_KEY_DAYS", "30"))


def _enc(obj: dict) -> str:
    return (
        base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode())
        .rstrip(b"=")
        .decode()
    )


def mint_pilot_key(
    secret: str,
    tenant: str,
    roles: list[str],
    days: int,
    sub: str,
    now: int | None = None,
) -> str:
    """Mint an HS256 pilot bearer token. Raises ValueError on bad input."""
    tenant = (tenant or "").strip()
    sub = (sub or "").strip()
    roles = [r.strip() for r in (roles or []) if r.strip()]
    if not secret:
        raise ValueError("EUROSETU_JWT_SECRET is not configured")
    if not tenant:
        raise ValueError("tenant is required")
    if not sub or "@" not in sub:
        raise ValueError("sub must be the requester email address")
    if not roles:
        raise ValueError("at least one role is required")
    if not (1 <= int(days) <= 365):
        raise ValueError("days must be between 1 and 365")
    now = int(now) if now is not None else int(time.time())
    header = _enc({"alg": "HS256", "typ": "JWT"})
    payload = _enc(
        {
            "sub": sub,
            "exp": now + int(days) * 86400,
            "iat": now,
            "tenant_id": tenant,
            "tenants": {tenant: roles},
        }
    )
    sig = (
        base64.urlsafe_b64encode(
            hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        )
        .rstrip(b"=")
        .decode()
    )
    return f"{header}.{payload}.{sig}"
