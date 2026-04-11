from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

from ops.config import load_calendar_yaml_path


def load_calendar() -> dict[str, Any]:
    path = Path(load_calendar_yaml_path())
    if not path.exists():
        return {
            "banned_words": ["算命", "占卜"],
            "holidays": [],
            "cta_map": {},
        }
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def calendar_for_date(d: date) -> dict[str, Any]:
    data = load_calendar()
    md = f"{d.month:02d}-{d.day:02d}"
    banned = list(data.get("banned_words") or [])
    holiday_label = None
    weight = 1.0
    cta = None
    for h in data.get("holidays") or []:
        if h.get("date") == md:
            holiday_label = h.get("label")
            weight = float(h.get("weight", 1.0))
            cta = h.get("cta")
            break
    return {
        "banned_words": banned,
        "holiday_label": holiday_label,
        "holiday_weight": weight,
        "suggested_cta": cta,
        "cta_map": data.get("cta_map") or {},
    }
