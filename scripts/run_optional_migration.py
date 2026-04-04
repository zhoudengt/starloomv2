#!/usr/bin/env python3
"""
Apply optional StarLoom schema (users birth_place columns) when MySQL is reachable.
Idempotent: safe to run multiple times. Same logic as app.database._ensure_users_birth_place_columns.

Usage (from repo root, with backend/.env configured):
  cd backend && python ../scripts/run_optional_migration.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))


async def main() -> None:
    from app.database import engine, ensure_users_birth_place_columns

    async with engine.begin() as conn:
        await ensure_users_birth_place_columns(conn)
    await engine.dispose()
    print("Optional migration OK (users birth_place columns present).")


if __name__ == "__main__":
    asyncio.run(main())
