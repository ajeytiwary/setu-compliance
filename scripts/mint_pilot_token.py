#!/usr/bin/env python3
"""Mint a local-test pilot bearer token (HS256, EUROSETU_JWT_SECRET).

Usage:
  EUROSETU_JWT_SECRET=test-secret .venv/bin/python scripts/mint_pilot_token.py
  EUROSETU_JWT_SECRET=test-secret .venv/bin/python scripts/mint_pilot_token.py --tenant tenant-a --days 30 --roles pilot_viewer pilot_contributor verifier admin

The token goes in the Authorization header plus the tenant header:
  curl -H "Authorization: Bearer <token>" -H "x-eurosetu-tenant: tenant-a" http://127.0.0.1:8765/api/pilot/overview
  curl -H "Authorization: Bearer <token>" -H "x-eurosetu-tenant: tenant-a" http://127.0.0.1:8765/pilot  # (after public-shell fix; APIs stay gated)

LOCAL TESTING ONLY. Never use this secret in production.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.pilot_keys import mint_pilot_key


def mint(secret: str, tenant: str, roles: list[str], days: int, sub: str = "local-tester") -> str:
    # Thin wrapper over the shared minter so CLI, /api/admin/mint and the
    # Email Worker all produce the identical JWT shape.
    return mint_pilot_key(secret, tenant, roles, days, sub)


def main() -> int:
    ap = argparse.ArgumentParser(description="Mint a local-test pilot bearer token")
    ap.add_argument("--tenant", default="tenant-a")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--sub", default="local-tester")
    ap.add_argument("--secret", default=os.getenv("EUROSETU_JWT_SECRET", "test-secret"))
    ap.add_argument(
        "--roles",
        nargs="*",
        default=["pilot_viewer", "pilot_contributor", "verifier", "admin"],
    )
    args = ap.parse_args()
    token = mint(args.secret, args.tenant, list(args.roles), args.days, args.sub)
    exp = time.strftime("%Y-%m-%d", time.localtime(time.time() + args.days * 86400))
    print(token)
    print(f"# tenant={args.tenant} roles={','.join(args.roles)} expires={exp} (in {args.days}d)", file=sys.stderr)
    print(f"# secret used: {'EUROSETU_JWT_SECRET env' if os.getenv('EUROSETU_JWT_SECRET') else 'default test-secret (set EUROSETU_JWT_SECRET to override)'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
