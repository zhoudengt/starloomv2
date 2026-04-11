"""输出目录：backend/ops/out/YYYY-MM-DD/"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path


def ops_root() -> Path:
    return Path(__file__).resolve().parent


def out_root() -> Path:
    return ops_root() / "out"


def day_dir(d: date) -> Path:
    return out_root() / d.isoformat()


def default_calendar_yaml() -> str:
    return str(ops_root() / "config" / "calendar.yaml")
