"""Shared daily fortune JSON shape (public horoscope, not personalized)."""

from datetime import date
from typing import Any


def normalize_daily_payload(data: dict, sign_cn: str, today: date) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "overall_score": 70,
        "love_score": 70,
        "career_score": 70,
        "wealth_score": 70,
        "health_score": 70,
        "lucky_color": "金色",
        "lucky_number": 7,
        "summary": f"{sign_cn}今日运势参考。",
        "love": "",
        "career": "",
        "wealth": "",
        "health": "",
        "advice": "",
    }
    merged = {**defaults, **{k: v for k, v in data.items() if not str(k).startswith("_")}}
    return merged


def wrap_daily_response(sign: str, sign_cn: str, today: date, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "sign": sign.lower(),
        "sign_cn": sign_cn,
        "date": today.isoformat(),
        **data,
    }
